"""A Terminal-Bench task as a chat env: the agent acts through shell tools, hidden tests score it.

The image is the task's own image with this server added under ``/opt/rlmesh``
(``docker/env-terminal.Dockerfile``). Tool calls run in the task container. The
tests ship in the image, but the server reads them into memory and deletes them
before the agent's first command; once it submits they run as Harbor would:
written to ``/tests``, ``bash /tests/test.sh``, reward read from
``/logs/verifier/reward.txt``.
"""

from __future__ import annotations

import ctypes
import functools
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from chat_env import ChatTaskEnv, Message, Turn

TASK_DIR = Path(os.environ.get("TB_TASK_DIR", "/opt/rlmesh/task"))
TESTS_DIR = Path("/tests")
VERIFIER_DIR = Path("/logs/verifier")
# The runner abandons an env step after 300 s; every step's commands, and the grading, stay under it.
STEP_BUDGET_S = 270.0
# A step that ends the episode keeps this much of its budget for the tests.
VERIFIER_BUDGET_S = 150.0
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
        self.tests = hidden_tests(TASK_DIR / "tests")
        self.verifier_log: str | None = None
        # The agent's shell sees the image's environment, not this server's.
        self.shell_env = {
            k: v for k, v in os.environ.items() if not k.startswith(("RLMESH_", "TB_"))
        }

    def start(self, index: int) -> Turn:
        self.task_id = self.env_id
        self.turns = 0
        self.verifier_log = None
        prompt = (
            f"{self.instruction.strip()}\n\n"
            f"You are working in a Linux container; the working directory is {self.workdir}. "
            "Use run_shell and write_file to do the task, check your work, then call submit."
        )
        return Turn([{"role": "user", "content": prompt}], tools=TOOLS)

    def respond(self, reply: Message) -> Turn:
        self.turns += 1
        calls = reply.get("tool_calls") or []
        names = [call.get("function", {}).get("name") for call in calls]
        submitted = "submit" in names
        ends = submitted or self.turns >= self.max_turns
        started = time.monotonic()
        deadline = started + STEP_BUDGET_S - (VERIFIER_BUDGET_S if ends else 0.0)
        results: list[Message] = []
        for call, name in zip(calls, names):
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
            except ValueError:
                args = {}
            if name == "submit":
                output = "Submitted."
            elif name == "run_shell":
                output = self._run(args, deadline)
            elif name == "write_file":
                output = self._write(args)
            else:
                output = f"unknown tool {name!r}"
            results.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": output})
        if ends:
            budget = started + STEP_BUDGET_S - time.monotonic()
            return self._grade(results, truncated=not submitted, timeout=budget)
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
        code, out = self._shell(["bash", "-c", command], timeout)
        if code is None:
            return f"timed out after {timeout:.0f}s\n{out}"
        return f"exit code {code}\n{out}"

    def _shell(self, argv: list[str], timeout: float) -> tuple[int | None, str]:
        """Run ``argv`` and return its exit code (``None`` on timeout) and clipped output.

        Output goes to a file, not a pipe, so a process the command leaves in the
        background (a server) cannot hold the call open; it keeps running. On
        timeout the command's whole session is killed.
        """
        with tempfile.TemporaryFile() as out:
            process = subprocess.Popen(
                argv,
                cwd=self.workdir,
                env=self.shell_env,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                code: int | None = process.wait(timeout)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                code = None
            return code, _clipped(out)

    def _write(self, args: dict[str, Any]) -> str:
        path = self.workdir / str(args.get("path", ""))
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(args.get("content", "")))
        except OSError as exc:
            return f"error: {exc}"
        return f"wrote {path}"

    def _grade(self, results: list[Message], truncated: bool, timeout: float) -> Turn:
        shutil.rmtree(TESTS_DIR, ignore_errors=True)
        for relative, (data, mode) in self.tests.items():
            path = TESTS_DIR / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            path.chmod(mode)
        logs = VERIFIER_DIR
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "reward.txt").unlink(missing_ok=True)
        started = time.monotonic()
        code, log = self._shell(["bash", str(TESTS_DIR / "test.sh")], timeout)
        if code is None:
            log = f"verifier timed out after {timeout:.0f}s\n{log}"
        self.verifier_log = log
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

    def render(self) -> Any:
        """The task, the model's latest reply and the shell session as an RGB frame."""
        from render import terminal_frame  # The harness imports this module without Pillow.

        return terminal_frame(
            self.history,
            self.env_id,
            self.instruction,
            str(self.workdir),
            (self.turns, self.max_turns),
            self.success,
            self.verifier_log,
        )


@functools.cache
def hidden_tests(root: Path) -> dict[str, tuple[bytes, int]]:
    """Read the tests under ``root`` into memory, then delete them, once per process.

    The agent's shell runs as root in this container, so nothing on disk is out
    of its reach; this process is made non-dumpable too, which keeps its memory
    from a root without ``CAP_SYS_PTRACE`` (the platform grants none).
    """
    files = [path for path in sorted(root.rglob("*")) if path.is_file()]
    if not files:
        raise FileNotFoundError(f"no tests under {root}")
    tests = {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mode & 0o777) for p in files}
    shutil.rmtree(root)
    if sys.platform == "linux":
        ctypes.CDLL(None).prctl(4, 0, 0, 0, 0)  # PR_SET_DUMPABLE, 0
    return tests


def _clipped(file: Any) -> str:
    """The text in ``file``, its middle cut when longer than ``MAX_OUTPUT_CHARS`` bytes."""
    size = file.seek(0, os.SEEK_END)
    file.seek(0)
    if size <= MAX_OUTPUT_CHARS:
        return file.read().decode(errors="replace")
    half = MAX_OUTPUT_CHARS // 2
    head = file.read(half)
    file.seek(size - half)
    tail = file.read()
    cut = size - 2 * half
    return f"{head.decode(errors='replace')}\n... [{cut} bytes cut] ...\n{tail.decode(errors='replace')}"
