"""A Terminal-Bench task as a chat env: the agent acts through shell tools, hidden tests score it.

The image is the task's own image with this server added under ``/opt/rlmesh``
(``docker/env-terminal.Dockerfile``). Tool calls run in the task container; the
tests stay outside the agent's view until it submits, then run as Harbor would:
copied to ``/tests``, ``bash /tests/test.sh``, reward read from
``/logs/verifier/reward.txt``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from chat_env import ChatTaskEnv, Message, Turn

TASK_DIR = Path(os.environ.get("TB_TASK_DIR", "/opt/rlmesh/task"))
TESTS_DIR = Path("/tests")
VERIFIER_DIR = Path("/logs/verifier")
# The runner abandons an env step after 300 s; every step's commands, and the grading, stay under it.
STEP_BUDGET_S = 270.0
MAX_OUTPUT_CHARS = 12_000

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": (
                "Run a bash command in the task container and return its exit code and output. "
                "Each call starts a fresh shell in the task's working directory: files persist "
                "between calls, but cd and exported variables do not."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout_sec": {"type": "integer", "description": "default 120, max 240"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file (absolute, or relative to the working directory).",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit",
            "description": "Finish: the hidden tests run on the container as you leave it.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


class TerminalTask(ChatTaskEnv):
    """One Terminal-Bench task; every seed is the same task (Harbor tasks have no variants)."""

    def __init__(self) -> None:
        super().__init__()
        self.workdir = Path.cwd()
        self.env_id = TASK_DIR.joinpath("name").read_text().strip()
        self.instruction = TASK_DIR.joinpath("instruction.md").read_text()
        self.max_turns = int(os.environ.get("MAX_TURNS", "40"))
        self.turns = 0
        # The agent's shell sees the image's environment, not this server's.
        self.shell_env = {k: v for k, v in os.environ.items() if not k.startswith(("RLMESH_", "TB_"))}

    def start(self, index: int) -> Turn:
        self.task_id = self.env_id
        self.turns = 0
        prompt = (
            f"{self.instruction.strip()}\n\n"
            f"You are working in a Linux container; the working directory is {self.workdir}. "
            "Use run_shell and write_file to do the task, check your work, then call submit."
        )
        return Turn([{"role": "user", "content": prompt}], tools=TOOLS)

    def respond(self, reply: Message) -> Turn:
        self.turns += 1
        calls = reply.get("tool_calls") or []
        deadline = time.monotonic() + STEP_BUDGET_S
        results: list[Message] = []
        submitted = False
        for call in calls:
            name = call.get("function", {}).get("name")
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
            except ValueError:
                args = {}
            if name == "submit":
                submitted = True
                output = "Submitted."
            elif name == "run_shell":
                output = self._run(args, deadline)
            elif name == "write_file":
                output = self._write(args)
            else:
                output = f"unknown tool {name!r}"
            results.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": output})
        if submitted or self.turns >= self.max_turns:
            return self._grade(results, truncated=not submitted)
        if not calls:
            results.append(
                {"role": "user", "content": "Keep going with the tools, or call submit when done."}
            )
        return Turn(results, tools=TOOLS)

    def _run(self, args: dict[str, Any], deadline: float) -> str:
        command = str(args.get("command", ""))
        timeout = min(float(args.get("timeout_sec") or 120), 240.0, deadline - time.monotonic())
        if timeout <= 1:
            return "skipped: this step's time budget is spent; run it in your next message"
        try:
            done = subprocess.run(
                ["bash", "-c", command],
                cwd=self.workdir,
                env=self.shell_env,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            out = _text(exc.stdout) + _text(exc.stderr)
            return _clip(f"timed out after {timeout:.0f}s\n{out}")
        return _clip(f"exit code {done.returncode}\n{done.stdout}{done.stderr}")

    def _write(self, args: dict[str, Any]) -> str:
        path = self.workdir / str(args.get("path", ""))
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(args.get("content", "")))
        except OSError as exc:
            return f"error: {exc}"
        return f"wrote {path}"

    def _grade(self, results: list[Message], truncated: bool) -> Turn:
        shutil.rmtree(TESTS_DIR, ignore_errors=True)
        shutil.copytree(TASK_DIR / "tests", TESTS_DIR)
        logs = VERIFIER_DIR
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "reward.txt").unlink(missing_ok=True)
        started = time.monotonic()
        try:
            done = subprocess.run(
                ["bash", str(TESTS_DIR / "test.sh")],
                cwd=self.workdir,
                env=self.shell_env,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=STEP_BUDGET_S,
            )
            log = done.stdout + done.stderr
        except subprocess.TimeoutExpired as exc:
            log = f"verifier timed out\n{_text(exc.stdout)}{_text(exc.stderr)}"
        try:
            reward = float((logs / "reward.txt").read_text().strip())
        except (OSError, ValueError):
            reward = 0.0
        note = f"Tests ran: reward {reward:g}."
        return Turn(
            [*results, {"role": "user", "content": note}],
            rewards={"tests_pass": reward},
            reward=reward,
            truncated=truncated,
            info={
                "turns": self.turns,
                "verifier_s": round(time.monotonic() - started, 1),
                "verifier_tail": log[-4000:],
            },
        )


def _text(value: str | bytes | None) -> str:
    return value.decode(errors="replace") if isinstance(value, bytes) else value or ""


def _clip(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    half = MAX_OUTPUT_CHARS // 2
    return f"{text[:half]}\n... [{len(text) - MAX_OUTPUT_CHARS} chars cut] ...\n{text[-half:]}"
