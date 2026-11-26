import os
import selectors
import socket
import subprocess
import sys
import time
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

STARTUP_TIMEOUT = 60.0


@pytest.fixture
def port() -> int:
    """A loopback port free for both TCP and UDP, as a session host needs."""
    for _ in range(64):
        with socket.socket() as tcp, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            tcp.bind(("127.0.0.1", 0))
            port = int(tcp.getsockname()[1])
            try:
                udp.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("no free local port")


def _wait_for(process: subprocess.Popen[str], ready: str) -> str:
    assert process.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    output: list[str] = []
    deadline = time.monotonic() + STARTUP_TIMEOUT
    while (left := deadline - time.monotonic()) > 0 and selector.select(timeout=left):
        line = process.stdout.readline()
        if not line:
            raise AssertionError(f"server exited early ({process.wait()}):\n{''.join(output)}")
        output.append(line)
        if ready in line:
            return line.strip()
    raise AssertionError(f"server never printed {ready!r}:\n{''.join(output)}")


@pytest.fixture
def serve() -> Iterator[Callable[..., str]]:
    """Start a Python server process; return its first output line containing ``ready``."""
    processes: list[subprocess.Popen[str]] = []

    def start(*args: str, cwd: Path, ready: str, env: dict[str, str] | None = None) -> str:
        process = subprocess.Popen(
            [sys.executable, "-u", *args],
            cwd=cwd,
            env={**os.environ, **(env or {})},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        processes.append(process)
        return _wait_for(process, ready)

    yield start
    for process in processes:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


@pytest.fixture
def run_script() -> Callable[..., str]:
    """Run a Python script to completion; return its stdout."""

    def run(*args: str, cwd: Path, timeout: float = 120.0) -> str:
        result = subprocess.run(
            [sys.executable, *args], cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        assert result.returncode == 0, f"exit={result.returncode}\n{result.stdout}{result.stderr}"
        return result.stdout

    return run


@pytest.fixture
def docker_build() -> Iterator[Callable[..., str]]:
    """Build a Docker context under a throwaway tag, removed after the test."""
    tags: list[str] = []

    def build(context: Path, *args: str) -> str:
        tag = f"rlmesh-examples-test/{context.name}:{uuid.uuid4().hex[:8]}"
        result = subprocess.run(
            ["docker", "build", "-q", "-t", tag, *args, str(context)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        tags.append(tag)
        return tag

    yield build
    if tags:
        subprocess.run(["docker", "rmi", "-f", *tags], capture_output=True)
