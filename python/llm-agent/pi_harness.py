"""The pi coding agent as an RLMesh model: pi runs the agent loop, the env runs every tool call.

Each episode gets one ``pi --mode rpc`` process whose only tools are the env's (``pi_tools.js``).
When pi calls one, predict returns the call as the action; the env's result in the next
observation answers it. Provider and model come from ``$PI_PROVIDER`` and ``$PI_MODEL``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from queue import Empty, Queue
from typing import Any

import rlmesh
from chat_env import Message, append_jsonl, output_dir
from harness import STEP_BUDGET_S, _text, redact_images
from rlmesh.types import PredictContext

EXTENSION = Path(__file__).with_name("pi_tools.js")


def _empty() -> Message:
    return {"role": "assistant", "content": ""}


class _Pi:
    """One pi process in RPC mode, holding one episode's conversation."""

    def __init__(self, command: list[str], tools: list[dict[str, Any]], system: str) -> None:
        args = [*command, "--mode", "rpc", "--no-session", "--offline", "--no-builtin-tools"]
        args += ["--no-extensions", "--no-skills", "--no-prompt-templates", "--no-themes"]
        args += ["--no-context-files", "-e", str(EXTENSION)]
        for flag, var in (("--provider", "PI_PROVIDER"), ("--model", "PI_MODEL")):
            if os.environ.get(var):
                args += [flag, os.environ[var]]
        if system:
            args += ["--append-system-prompt", system]
        env = {**os.environ, "PI_ENV_TOOLS": json.dumps(tools)}
        self.process = subprocess.Popen(
            args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env
        )
        self.events: Queue[dict[str, Any] | None] = Queue()
        self.pending: dict[str, str] = {}
        threading.Thread(target=self._read, daemon=True).start()
        # A retry starts after agent_end, which predict already took as the final reply.
        self._send({"type": "set_auto_retry", "enabled": False})

    def _read(self) -> None:
        assert self.process.stdout
        for line in self.process.stdout:
            try:
                self.events.put(json.loads(line))
            except ValueError:
                pass
        self.events.put(None)

    def _send(self, command: dict[str, Any]) -> None:
        assert self.process.stdin
        self.process.stdin.write(json.dumps(command).encode() + b"\n")
        self.process.stdin.flush()

    def _next(self, deadline: float) -> dict[str, Any] | None:
        try:
            event = self.events.get(timeout=max(0.0, deadline - time.monotonic()))
        except Empty:
            return None
        if event is None:
            raise RuntimeError(f"pi exited with code {self.process.wait()}")
        return event

    def _request(self, command: dict[str, Any], deadline: float) -> dict[str, Any] | None:
        self._send({**command, "id": command["type"]})
        while event := self._next(deadline):
            if event["type"] == "response" and event.get("id") == command["type"]:
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
        action = self._reply(deadline)
        if action is None:
            # Abort waits for pi to go idle, which also cancels its pending tool calls.
            self._request({"type": "abort"}, time.monotonic() + 10)
            self.pending.clear()
            return _empty()
        return action

    def _reply(self, deadline: float) -> Message | None:
        text, calls = "", []
        ended: set[str] = set()
        requested: dict[str, dict[str, Any]] = {}
        while event := self._next(deadline):
            kind = event["type"]
            if kind == "message_end" and event["message"]["role"] == "assistant":
                content = event["message"]["content"]
                text = "".join(part["text"] for part in content if part["type"] == "text")
                calls = [part["id"] for part in content if part["type"] == "toolCall"]
            elif kind == "tool_execution_end":
                ended.add(event["toolCallId"])
            elif kind == "extension_ui_request" and event["method"] == "input":
                call = json.loads(event["title"])
                self.pending[call["id"]] = event["id"]
                requested[call["id"]] = call
            elif kind == "agent_end":
                return self._final(event["messages"], deadline)
            elif kind == "response" and not event["success"]:
                print(f"pi: {event['command']}: {event.get('error')}", file=sys.stderr, flush=True)
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
        if last.get("errorMessage"):
            print(f"pi: {last['errorMessage']}", file=sys.stderr, flush=True)
        text = "".join(part["text"] for part in last["content"] if part["type"] == "text")
        return {"role": "assistant", "content": text}

    def close(self) -> None:
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()


class PiHarness(rlmesh.Model):
    """Answer each observation with pi's next tool call or final reply.

    Args:
        pi_command: How to run pi (default ``$PI_COMMAND``, else ``pi``).
    """

    def __init__(self, pi_command: list[str] | None = None) -> None:
        self.pi_command = pi_command or os.environ.get("PI_COMMAND", "pi").split()
        self.transcripts = output_dir() / "transcripts"
        self.transcripts.mkdir(exist_ok=True)
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
        action = pi.step(messages, started + STEP_BUDGET_S)
        append_jsonl(
            self.transcripts / f"{episode}.jsonl",
            {
                "step": context["predict_index"],
                "seed": context["episode_seed"],
                "request": {
                    "model": os.environ.get("PI_MODEL"),
                    "messages": redact_images(messages),
                },
                "response": action,
                "latency_ms": round((time.monotonic() - started) * 1000, 1),
                "ts": time.time(),
            },
        )
        return json.dumps(action)

    def on_episode_end(self, episode_id: str = "") -> None:
        pi = self.episodes.pop(episode_id or "episode", None)
        if pi:
            pi.close()
