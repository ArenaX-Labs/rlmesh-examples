"""The pi coding agent as an RLMesh model: pi runs the agent loop, the env runs every tool call.

Each episode gets one ``pi --mode rpc`` process whose only tools are the env's (``pi_tools.js``).
When pi calls one, predict returns the call as the action; the env's result in the next
observation answers it. Provider and model come from ``$RLMESH_LLM``, else ``$PI_PROVIDER`` and ``$PI_MODEL``.
"""

from __future__ import annotations

import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import suppress
from pathlib import Path
from queue import Empty, Queue
from typing import Any

import rlmesh
from chat_env import Message, output_dir
from harness import STEP_BUDGET_S, _text, split_llm
from rlmesh.types import PredictContext
from trajectory import Trajectory

EXTENSION = Path(__file__).resolve().with_name("pi_tools.js")


def pi_llm() -> tuple[str, str]:
    """pi's provider and model: ``$RLMESH_LLM`` when RLMesh Managed names one, else
    ``$PI_PROVIDER`` and ``$PI_MODEL``."""
    if llm := os.environ.get("RLMESH_LLM"):
        return split_llm(llm)
    return os.environ.get("PI_PROVIDER", ""), os.environ.get("PI_MODEL", "")


def _empty() -> Message:
    return {"role": "assistant", "content": ""}


class _Pi:
    """One pi process in RPC mode, holding one episode's conversation."""

    def __init__(self, command: list[str], tools: list[dict[str, Any]], system: str) -> None:
        self.args = [*command, "--mode", "rpc", "--no-session", "--offline", "--no-builtin-tools"]
        self.args += ["--no-extensions", "--no-skills", "--no-prompt-templates", "--no-themes"]
        self.args += ["--no-context-files", "-e", str(EXTENSION)]
        for flag, value in zip(("--provider", "--model"), pi_llm(), strict=True):
            if value:
                self.args += [flag, value]
        # A fresh agent dir, cwd and HOME keep pi off ~/.pi, any .pi/ and ambient cloud credentials.
        self.home = tempfile.mkdtemp(prefix="pi-agent-")
        self.stderr = Path(self.home) / "stderr.log"
        env = {
            **os.environ,
            "HOME": self.home,
            "PI_CODING_AGENT_DIR": self.home,
            "PI_ENV_TOOLS": json.dumps(tools),
            "PI_ENV_SYSTEM": system,
        }
        try:
            with self.stderr.open("wb") as stderr:
                self.process = subprocess.Popen(
                    self.args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=stderr,
                    env=env,
                    cwd=self.home,
                )
        except BaseException:
            shutil.rmtree(self.home, ignore_errors=True)
            raise
        self.ids = itertools.count()
        self.events: Queue[dict[str, Any] | None] = Queue()
        self.pending: dict[str, str] = {}
        # What the trajectory records of the turn being answered; never sent to the env.
        self.reasoning: list[str] = []
        self.usages: list[dict[str, Any]] = []
        # After an abort, events of the abandoned turn can still arrive; skip to the next agent_start.
        self.stale = False
        threading.Thread(target=self._read, args=(self.process, self.events), daemon=True).start()
        # A retry starts after agent_end, which predict already took as the final reply; a compaction
        # would rewrite the history the env's observations assume.
        self._send({"type": "set_auto_retry", "enabled": False})
        self._send({"type": "set_auto_compaction", "enabled": False})

    @staticmethod
    def _read(process: subprocess.Popen[bytes], events: Queue[dict[str, Any] | None]) -> None:
        assert process.stdout
        for line in process.stdout:
            try:
                events.put(json.loads(line))
            except ValueError:
                pass
        events.put(None)

    # TODO: a wedged pi that stops reading stdin blocks this write past the step budget; bound it
    # (writer thread or non-blocking pipe) once a stalled pi is seen holding a predict.
    def _send(self, command: dict[str, Any]) -> None:
        assert self.process.stdin
        try:
            self.process.stdin.write(json.dumps(command).encode() + b"\n")
            self.process.stdin.flush()
        except BrokenPipeError:
            raise self._exited() from None

    def _exited(self) -> RuntimeError:
        code = self.process.wait()
        log = self.stderr.read_bytes()[-2000:].decode(errors="replace").strip()
        return RuntimeError(f"pi exited with code {code}: {log}")

    def _next(self, deadline: float) -> dict[str, Any] | None:
        try:
            event = self.events.get(timeout=max(0.0, deadline - time.monotonic()))
        except Empty:
            return None
        if event is None:
            raise self._exited()
        return event

    def _request(self, command: dict[str, Any], deadline: float) -> dict[str, Any] | None:
        id = f"{command['type']}-{next(self.ids)}"
        self._send({**command, "id": id})
        while event := self._next(deadline):
            if event["type"] == "response" and event.get("id") == id:
                return event
        return None

    def step(self, messages: list[Message], deadline: float) -> Message:
        for message in messages:
            if message["role"] == "tool" and message.get("tool_call_id") in self.pending:
                dialog = self.pending.pop(message["tool_call_id"])
                value = _text(message.get("content"))
                self._send({"type": "extension_ui_response", "id": dialog, "value": value})
        # TODO: images in observations are dropped; send them as pi images once a task needs it.
        prompt = "\n\n".join(_text(m.get("content")) for m in messages if m["role"] == "user")
        if prompt:
            # While pi waits on tool results, steer delivers the prompt before its next LLM call.
            self._send({"type": "prompt", "message": prompt, "streamingBehavior": "steer"})
        # Keep part of the budget to abort the turn if pi has not answered by then.
        abort_at = deadline - min(10.0, max(0.0, deadline - time.monotonic()) / 4)
        action = self._reply(abort_at)
        if action is None:
            # Abort waits for pi to go idle, which also cancels its pending tool calls.
            if not self._request({"type": "abort"}, deadline):
                self._kill()
                raise RuntimeError("pi did not stop its timed-out turn; killed it")
            self.pending.clear()
            self.stale = True
            return _empty()
        return action

    def _reply(self, deadline: float) -> Message | None:
        text, calls = "", []
        ended: set[str] = set()
        requested: dict[str, dict[str, Any]] = {}
        while event := self._next(deadline):
            kind = event["type"]
            if kind == "response" and not event["success"]:
                if event["command"] == "prompt":
                    raise RuntimeError(f"pi rejected the prompt: {event.get('error')}")
                print(f"pi: {event['command']}: {event.get('error')}", file=sys.stderr, flush=True)
            elif self.stale:
                self.stale = kind != "agent_start"
            elif kind == "message_end" and event["message"]["role"] == "assistant":
                content = event["message"]["content"]
                text = "".join(part["text"] for part in content if part["type"] == "text")
                self.reasoning += [p["thinking"] for p in content if p["type"] == "thinking"]
                if usage := event["message"].get("usage"):
                    self.usages.append(
                        {
                            "input_tokens": usage["input"],
                            "output_tokens": usage["output"],
                            "cache_read_input_tokens": usage["cacheRead"],
                            "cache_creation_input_tokens": usage["cacheWrite"],
                            "stop_reason": event["message"].get("stopReason"),
                        }
                    )
                calls = [part["id"] for part in content if part["type"] == "toolCall"]
            elif kind == "tool_execution_end":
                ended.add(event["toolCallId"])
            elif kind == "extension_ui_request" and event["method"] == "input":
                call = json.loads(event["title"])
                self.pending[call["id"]] = event["id"]
                requested[call["id"]] = call
            elif kind == "agent_end":
                return self._final(event["messages"], deadline)
            waiting = [id for id in calls if id in requested]
            if waiting and all(id in requested or id in ended for id in calls):
                return {
                    "role": "assistant",
                    "content": text,
                    "tool_calls": [
                        {
                            "id": id,
                            "type": "function",
                            "function": {
                                "name": requested[id]["name"],
                                "arguments": json.dumps(requested[id]["arguments"]),
                            },
                        }
                        for id in waiting
                    ],
                }
        return None

    def _final(self, messages: list[dict[str, Any]], deadline: float) -> Message | None:
        # agent_end comes before pi clears its streaming flag; a prompt in between would queue.
        while state := self._request({"type": "get_state"}, deadline):
            if not state["data"]["isStreaming"]:
                break
            time.sleep(0.01)
        else:
            return None
        last = next((m for m in reversed(messages) if m["role"] == "assistant"), None)
        if last is None:
            return _empty()
        if last.get("stopReason") == "error":
            raise RuntimeError(f"pi: {last.get('errorMessage')}")
        text = "".join(part["text"] for part in last["content"] if part["type"] == "text")
        return {"role": "assistant", "content": text}

    def _kill(self) -> None:
        self.process.kill()
        self.process.wait()

    def close(self) -> None:
        assert self.process.stdin
        with suppress(BrokenPipeError):
            self.process.stdin.close()
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._kill()
        shutil.rmtree(self.home, ignore_errors=True)


class PiHarness(rlmesh.Model):
    """Answer each observation with pi's next tool call or final reply.

    Args:
        pi_command: How to run pi (default ``$PI_COMMAND``, else ``pi``).
    """

    def __init__(self, pi_command: list[str] | None = None) -> None:
        command = pi_command or os.environ.get("PI_COMMAND", "pi").split()
        # pi starts in its own temp cwd, so a relative executable would not resolve there.
        self.pi_command = [os.path.abspath(shutil.which(command[0]) or command[0]), *command[1:]]
        self.trajectories = output_dir() / "trajectories"
        self.trajectories.mkdir(exist_ok=True)
        # TODO: an episode torn down without on_episode_end (served-path teardown fires no hook) keeps
        # its pi process until close(); reap idle processes once long-lived servers leak them.
        self.episodes: dict[str, _Pi] = {}
        super().__init__()

    def predict(self, observation: str, context: PredictContext) -> str:
        started = time.monotonic()
        try:
            obs = json.loads(observation)
        except ValueError:
            obs = None
        if not isinstance(obs, dict):
            # A probe samples random text; answer it without the LLM.
            return json.dumps(_empty())
        episode = context["episode_id"] or "episode"
        messages: list[Message] = obs["messages"]
        pi = self.episodes.get(episode)
        if pi is None:
            system = "\n\n".join(_text(m.get("content")) for m in messages if m["role"] == "system")
            pi = self.episodes[episode] = _Pi(self.pi_command, obs.get("tools") or [], system)
        state = context["state"]
        trajectory: Trajectory = state.get("trajectory") or state.setdefault(
            "trajectory",
            Trajectory(
                self.trajectories / f"{episode}.json",
                episode,
                context["episode_seed"],
                "pi",
                "/".join(part for part in pi_llm() if part),
            ),
        )
        trajectory.observe(messages, obs.get("tools") or [])
        pi.reasoning, pi.usages = [], []
        action = pi.step(messages, started + STEP_BUDGET_S)
        trajectory.reply(
            {**action, "reasoning": "\n\n".join(pi.reasoning)},
            pi.usages,
            rlmesh_step=context["predict_index"],
            latency_ms=round((time.monotonic() - started) * 1000, 1),
        )
        trajectory.save()
        return json.dumps(action)

    def on_episode_end(self, episode_id: str = "") -> None:
        pi = self.episodes.pop(episode_id or "episode", None)
        if pi:
            pi.close()

    def close(self) -> None:
        while self.episodes:
            self.episodes.popitem()[1].close()
