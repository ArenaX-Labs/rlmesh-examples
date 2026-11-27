from __future__ import annotations

import json
import os
import re
import shlex
import signal
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.util import find_spec
from pathlib import Path
from queue import Empty, Queue
from types import ModuleType
from typing import Any

import pytest

HERE = Path(__file__).resolve().parent
PI_PACKAGE = "@mariozechner/pi-coding-agent"
PI_VERSION = "0.73.1"
PI_MODULES = HERE / ".venv-pi/node_modules"
PI = PI_MODULES / ".bin/pi"

Reply = str | list[dict[str, Any]] | Callable[[], str]


class _FakeLLM(ThreadingHTTPServer):
    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _LLMHandler)
        self.url = f"http://127.0.0.1:{self.server_port}"
        self.requests: list[tuple[str, dict[str, str], dict[str, Any]]] = []
        self.replies: Queue[Reply] = Queue()

    def script(self, *replies: Reply) -> None:
        for reply in replies:
            self.replies.put(reply)


class _LLMHandler(BaseHTTPRequestHandler):
    server: _FakeLLM

    def log_message(self, *_: Any) -> None:
        pass

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        headers = {key.lower(): value for key, value in self.headers.items()}
        self.server.requests.append((self.path, headers, body))
        try:
            reply = self.server.replies.get_nowait()
        except Empty:
            self.send_error(400, "No scripted reply")
            return
        if callable(reply):
            reply = reply()

        if self.path.endswith("/chat/completions"):
            payload = _openai_stream(body["model"], reply)
        elif self.path == "/v1/messages" and isinstance(reply, str):
            payload = _anthropic_stream(body["model"], reply)
        else:
            self.send_error(400, "Unexpected provider request")
            return

        with suppress(BrokenPipeError, ConnectionResetError):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)


def _openai_stream(model: str, reply: str | list[dict[str, Any]]) -> bytes:
    delta = (
        {"content": reply}
        if isinstance(reply, str)
        else {"tool_calls": [{"index": i, **call} for i, call in enumerate(reply)]}
    )
    stop = "stop" if isinstance(reply, str) else "tool_calls"
    chunks = [
        {"index": 0, "delta": {"role": "assistant", **delta}, "finish_reason": None},
        {"index": 0, "delta": {}, "finish_reason": stop},
    ]
    events = (
        {
            "id": "chatcmpl-test",
            "object": "chat.completion.chunk",
            "created": 1,
            "model": model,
            "choices": [choice],
        }
        for choice in chunks
    )
    return (
        "".join(f"data: {json.dumps(event)}\n\n" for event in events) + "data: [DONE]\n\n"
    ).encode()


def _anthropic_stream(model: str, reply: str) -> bytes:
    message = {
        "id": "msg-test",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [],
        "usage": {"input_tokens": 1, "output_tokens": 0},
    }
    events = [
        {"type": "message_start", "message": message},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": reply}},
        {"type": "content_block_stop", "index": 0},
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn"},
            "usage": {"output_tokens": 2},
        },
        {"type": "message_stop"},
    ]
    return "".join(
        f"event: {event['type']}\ndata: {json.dumps(event)}\n\n" for event in events
    ).encode()


@pytest.fixture
def fake_llm() -> Iterator[_FakeLLM]:
    with _FakeLLM() as server:
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
        thread.start()
        try:
            yield server
        finally:
            server.shutdown()
            thread.join()


def _pids(path: Path) -> list[int]:
    return [int(line) for line in path.read_text().splitlines()] if path.exists() else []


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@pytest.fixture
def pi_runtime(
    fake_llm: _FakeLLM, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Path]:
    install = f"Run npm install --prefix .venv-pi --save-exact {PI_PACKAGE}@{PI_VERSION}"
    assert PI.is_file(), install
    package = json.loads((PI_MODULES / PI_PACKAGE / "package.json").read_text())
    assert (package["name"], package["version"]) == (PI_PACKAGE, PI_VERSION), install
    monkeypatch.syspath_prepend(str(HERE))
    monkeypatch.setenv("RLMESH_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(tmp_path / "agent"))
    monkeypatch.setenv("PI_COMMAND", str(PI))
    monkeypatch.setenv("PI_PROVIDER", "openai")
    monkeypatch.setenv("PI_MODEL", "fixture-model")
    monkeypatch.setenv("OPENAI_BASE_URL", f"{fake_llm.url}/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-openai-key")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    # Pi uses the model's explicit base URL for Anthropic. Redirect only its transport here.
    pid_log = tmp_path / "pi-pids"
    preload = tmp_path / "pi-test.mjs"
    preload.write_text(f"""\
import {{ appendFileSync }} from 'node:fs';
appendFileSync({json.dumps(str(pid_log))}, String(process.pid) + '\\n');
const origin = {json.dumps(fake_llm.url)};
const fetch = globalThis.fetch;
globalThis.fetch = (input, init) => {{
  const url = new URL(input instanceof Request ? input.url : input);
  if (url.hostname === 'api.anthropic.com') {{
    const local = new URL(url.pathname + url.search, origin);
    return fetch(input instanceof Request ? new Request(local, input) : local, init);
  }}
  if (url.origin !== origin) throw new Error(`Unexpected provider endpoint: ${{url.origin}}`);
  return fetch(input, init);
}};
""")
    monkeypatch.setenv("NODE_OPTIONS", f'--import="{preload}"')
    yield pid_log
    for pid in _pids(pid_log):
        with suppress(ProcessLookupError):
            os.kill(pid, signal.SIGKILL)


def _implementation() -> ModuleType:
    assert find_spec("pi_harness") is not None, "pi_harness.py must provide PiHarness"
    import pi_harness

    return pi_harness


@contextmanager
def _episode(harness: Any, episode_id: str) -> Iterator[Callable[..., dict[str, Any]]]:
    from terminal_env import TOOLS

    state: dict[str, Any] = {}
    index = 0

    def predict(*messages: dict[str, Any]) -> dict[str, Any]:
        nonlocal index
        context = {
            "episode_id": episode_id,
            "episode_seed": 0,
            "predict_index": index,
            "predict_seed": 0,
            "state": state,
        }
        index += 1
        return json.loads(
            harness.predict(json.dumps({"messages": messages, "tools": TOOLS}), context)
        )

    try:
        yield predict
    finally:
        harness.on_episode_end(episode_id)


def _user(content: str) -> dict[str, str]:
    return {"role": "user", "content": content}


def _call(name: str, **arguments: Any) -> dict[str, Any]:
    return {
        "id": f"call_{name}",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def _text(content: Any) -> str:
    return "".join(part["text"] for part in content) if isinstance(content, list) else content


def _user_prompts(request: dict[str, Any]) -> list[str]:
    return [_text(msg["content"]) for msg in request["messages"] if msg["role"] == "user"]


@pytest.mark.parametrize("multiple", [False, True], ids=["single", "multiple"])
def test_pi_round_trips_environment_tool_calls(
    pi_runtime: Path, fake_llm: _FakeLLM, multiple: bool
) -> None:
    harness = _implementation().PiHarness()
    from terminal_env import TOOLS

    calls = [_call("run_shell", command="echo hi")]
    prompts = ["Use the tools to say hi."]
    if multiple:
        calls.append(_call("write_file", path="hi.txt", content="from the environment"))
        prompts.append("Use both tools in the same turn.")
    env_results = {call["function"]["name"]: f"env result {i}\n" for i, call in enumerate(calls)}
    fake_llm.script(calls, "Finished.")

    seen = {}
    ids = set()
    with _episode(harness, "tools") as predict:
        action = predict(*map(_user, prompts))
        for _ in calls:
            assert action["role"] == "assistant"
            batch = action.get("tool_calls", [])
            if not batch:
                break
            results = []
            for call in batch:
                assert call["type"] == "function" and call["id"] and call["id"] not in ids
                ids.add(call["id"])
                function = call["function"]
                name = function["name"]
                assert name not in seen and name in env_results
                seen[name] = json.loads(function["arguments"])
                results.append(
                    {"role": "tool", "tool_call_id": call["id"], "content": env_results[name]}
                )
            action = predict(*results)
        assert action == {"role": "assistant", "content": "Finished."}
        assert len(_pids(pi_runtime)) == 1

    assert seen == {
        call["function"]["name"]: json.loads(call["function"]["arguments"]) for call in calls
    }
    (_, _, first), (_, _, followup) = fake_llm.requests
    sent = "\n".join(_user_prompts(first))
    assert all(prompt in sent for prompt in prompts)
    assert {tool["function"]["name"] for tool in first["tools"]} == {
        tool["function"]["name"] for tool in TOOLS
    }
    declared = {tool["function"]["name"]: tool["function"]["parameters"] for tool in first["tools"]}
    for tool in TOOLS:
        function = tool["function"]
        for key, value in function["parameters"].items():
            assert declared[function["name"]][key] == value
    request_ids = {
        call["function"]["name"]: call["id"]
        for msg in followup["messages"]
        for call in msg.get("tool_calls", [])
    }
    assert {
        msg["tool_call_id"]: _text(msg["content"])
        for msg in followup["messages"]
        if msg["role"] == "tool"
    } == {request_ids[name]: result for name, result in env_results.items()}


def test_pi_does_not_run_builtin_bash(pi_runtime: Path, fake_llm: _FakeLLM, tmp_path: Path) -> None:
    harness = _implementation().PiHarness()
    marker = tmp_path / "bash-ran"
    fake_llm.script([_call("bash", command=f"touch {shlex.quote(str(marker))}")], "Done.")

    with _episode(harness, "builtin") as predict:
        action = predict(_user("Continue this task."))
        assert fake_llm.requests
        if calls := action.get("tool_calls"):
            predict(
                *(
                    {"role": "tool", "tool_call_id": call["id"], "content": "Unavailable"}
                    for call in calls
                )
            )
    assert not marker.exists()


def test_pi_accepts_later_user_prompts_and_appends_actions(
    pi_runtime: Path, fake_llm: _FakeLLM, tmp_path: Path
) -> None:
    harness = _implementation().PiHarness()
    fake_llm.script("Starting.", "Continuing.")
    path = tmp_path / "transcripts/continue.jsonl"
    prompts = ["Start here.", "Keep going with the tools, or call submit when done."]
    actions = []

    with _episode(harness, "continue") as predict:
        for prompt in prompts:
            actions.append(predict(_user(prompt)))
            records = [json.loads(line) for line in path.read_text().splitlines()]
            assert [
                record.get("response", record.get("action", record)) for record in records
            ] == actions

    assert [action["content"] for action in actions] == ["Starting.", "Continuing."]
    assert [_user_prompts(body) for _, _, body in fake_llm.requests] == [prompts[:1], prompts]


def test_pi_reaps_episode_process_and_starts_with_fresh_history(
    pi_runtime: Path, fake_llm: _FakeLLM
) -> None:
    harness = _implementation().PiHarness()
    fake_llm.script([_call("run_shell", command="echo hi")], "Fresh start.")

    with _episode(harness, "first") as predict:
        assert predict(_user("First episode only."))["tool_calls"]
        (first_pid,) = _pids(pi_runtime)
        assert _alive(first_pid)
    assert not _alive(first_pid)

    with _episode(harness, "second") as predict:
        assert predict(_user("Second episode only."))["content"] == "Fresh start."
        _, second_pid = _pids(pi_runtime)
        assert second_pid != first_pid and _alive(second_pid)
    assert not _alive(second_pid)
    _, (_, _, request) = fake_llm.requests
    assert [msg["role"] for msg in request["messages"] if msg["role"] != "system"] == ["user"]
    assert _user_prompts(request) == ["Second episode only."]


def test_pi_step_timeout_returns_empty_action_and_recovers(
    pi_runtime: Path, fake_llm: _FakeLLM, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _implementation()
    import harness as llm_harness

    monkeypatch.setattr(llm_harness, "STEP_BUDGET_S", 3.0)
    monkeypatch.setattr(module, "STEP_BUDGET_S", 3.0, raising=False)
    harness = module.PiHarness()
    release = threading.Event()

    def stall() -> str:
        release.wait(timeout=6)
        return "Stale reply."

    fake_llm.script("Ready.", stall, "Recovered.")
    with _episode(harness, "timeout") as predict:
        assert predict(_user("Start normally."))["content"] == "Ready."
        started = time.monotonic()
        try:
            assert predict(_user("Wait for the provider.")) == {"role": "assistant", "content": ""}
            assert time.monotonic() - started < 5
            assert _user_prompts(fake_llm.requests[-1][2])[-1] == "Wait for the provider."
        finally:
            release.set()
        assert predict(_user("Try again.")) == {"role": "assistant", "content": "Recovered."}
        assert _user_prompts(fake_llm.requests[-1][2])[-1] == "Try again."


@pytest.mark.parametrize(
    ("provider", "model", "path", "header", "credential"),
    [
        (
            "openai",
            "another-model",
            "/v1/chat/completions",
            "authorization",
            "Bearer fixture-openai-key",
        ),
        ("anthropic", "claude-sonnet-4-6", "/v1/messages", "x-api-key", "fixture-anthropic-key"),
    ],
)
def test_pi_selects_provider_and_model_from_environment(
    pi_runtime: Path,
    fake_llm: _FakeLLM,
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    model: str,
    path: str,
    header: str,
    credential: str,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fixture-anthropic-key")
    monkeypatch.setenv("PI_PROVIDER", provider)
    monkeypatch.setenv("PI_MODEL", model)
    monkeypatch.setenv("PI_COMMAND", "unused-when-command-is-explicit")
    harness = _implementation().PiHarness(pi_command=[str(PI)])
    fake_llm.script("Correct provider.")

    with _episode(harness, "provider") as predict:
        assert predict(_user("Reply here."))["content"] == "Correct provider."
    ((request_path, headers, body),) = fake_llm.requests
    assert (request_path, headers[header], body["model"]) == (path, credential, model)


def test_pi_dockerfile_pins_agent_and_sdk_and_serves_harness() -> None:
    path = HERE / "docker/pi-harness.Dockerfile"
    assert path.is_file(), "docker/pi-harness.Dockerfile is missing"
    dockerfile = "\n".join(
        line for line in path.read_text().splitlines() if not line.lstrip().startswith("#")
    )
    defaults = dict(re.findall(r"(?m)^ARG\s+(\w+)=[\"']?([^\s\"']+)", dockerfile))
    resolved = re.sub(r"\$\{?(\w+)\}?", lambda m: defaults.get(m[1], m[0]), dockerfile)
    assert re.search(rf"{re.escape(PI_PACKAGE)}@{re.escape(PI_VERSION)}(?=[\s\"']|$)", resolved)
    assert "rlmesh==0.2.0a2" in resolved
    entrypoint = re.search(r"(?m)^ENTRYPOINT\s+(\[.*\])\s*$", dockerfile)
    assert entrypoint and json.loads(entrypoint[1]) == [
        "python",
        "-m",
        "rlmesh.serve",
        "pi_harness:PiHarness",
    ]


def _system_prompt(request: dict[str, Any]) -> str:
    return "\n".join(
        _text(msg["content"])
        for msg in request["messages"]
        if msg["role"] in ("system", "developer")
    )


def test_pi_sends_env_system_message_as_text_without_model_pod_paths(
    pi_runtime: Path, fake_llm: _FakeLLM, tmp_path: Path
) -> None:
    secret = tmp_path / "model-pod-secret.txt"
    secret.write_text("model pod secret contents")
    harness = _implementation().PiHarness()
    fake_llm.script("Done.")

    with _episode(harness, "system") as predict:
        predict({"role": "system", "content": str(secret)}, _user("Go."))
    ((_, _, request),) = fake_llm.requests
    system = _system_prompt(request)
    assert str(secret) in system
    assert "model pod secret contents" not in system
    for leak in ("Current working directory", str(HERE), str(tmp_path / "agent"), PI_PACKAGE):
        assert leak not in system


def test_pi_ignores_user_agent_dirs_and_uses_injected_key(
    pi_runtime: Path, fake_llm: _FakeLLM, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    planted = {
        "auth.json": json.dumps({"anthropic": {"type": "api_key", "key": "planted-key"}}),
        "settings.json": json.dumps({"defaultModel": "planted-model"}),
        "models.json": json.dumps({"providers": {}}),
        "SYSTEM.md": "PLANTED SYSTEM PROMPT",
    }
    dirs = [home / ".pi/agent", tmp_path / "agent"]
    for directory in dirs:
        directory.mkdir(parents=True)
        for name, content in planted.items():
            (directory / name).write_text(content)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fixture-anthropic-key")
    monkeypatch.setenv("PI_PROVIDER", "anthropic")
    monkeypatch.setenv("PI_MODEL", "claude-sonnet-4-6")
    harness = _implementation().PiHarness()
    fake_llm.script("Injected.")

    with _episode(harness, "isolated") as predict:
        assert predict(_user("Go."))["content"] == "Injected."
    ((_, headers, body),) = fake_llm.requests
    assert headers["x-api-key"] == "fixture-anthropic-key"
    assert "PLANTED" not in json.dumps(body)
    for directory in dirs:
        assert {path.name: path.read_text() for path in directory.iterdir()} == planted


def test_pi_timeout_without_abort_ack_kills_pi_and_raises(
    pi_runtime: Path, fake_llm: _FakeLLM, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _implementation()
    monkeypatch.setattr(module, "STEP_BUDGET_S", 3.0)
    request = module._Pi._request

    def ignore_abort(self: Any, command: dict[str, Any], deadline: float) -> Any:
        if command["type"] == "abort":
            time.sleep(max(0.0, deadline - time.monotonic()))
            return None
        return request(self, command, deadline)

    monkeypatch.setattr(module._Pi, "_request", ignore_abort)
    harness = module.PiHarness()
    release = threading.Event()

    def stall() -> str:
        release.wait(timeout=6)
        return "Stale reply."

    fake_llm.script(stall)
    with _episode(harness, "no-ack") as predict:
        started = time.monotonic()
        try:
            with pytest.raises(RuntimeError):
                predict(_user("Wait."))
            assert time.monotonic() - started < 3.5
        finally:
            release.set()
        (pid,) = _pids(pi_runtime)
        assert not _alive(pid)


def test_pi_runs_from_relative_command_without_compaction_or_user_home(
    pi_runtime: Path, fake_llm: _FakeLLM, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    (home / ".aws").mkdir(parents=True)
    (home / ".aws/credentials").write_text("[default]\naws_access_key_id = planted\n")
    seen = tmp_path / "pi-home"
    dump = tmp_path / "pi-home.mjs"
    dump.write_text(
        f"import {{ writeFileSync }} from 'node:fs';\n"
        f"writeFileSync({json.dumps(str(seen))}, process.env.HOME);\n"
    )
    monkeypatch.setenv("NODE_OPTIONS", f'{os.environ["NODE_OPTIONS"]} --import="{dump}"')
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(HERE)
    monkeypatch.setenv("PI_COMMAND", os.path.relpath(PI, HERE))
    harness = _implementation().PiHarness()
    fake_llm.script("Done.")

    with _episode(harness, "isolated-home") as predict:
        assert predict(_user("Go."))["content"] == "Done."
        pi = harness.episodes["isolated-home"]
        state = pi._request({"type": "get_state"}, time.monotonic() + 5)
        assert state["data"]["autoCompactionEnabled"] is False
        assert seen.read_text() == pi.home != str(home)
    assert not Path(pi.home).exists()


def test_pi_exit_raises_with_its_stderr(pi_runtime: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PI_PROVIDER")
    monkeypatch.setenv("PI_MODEL", "no-such-model")
    harness = _implementation().PiHarness()

    with _episode(harness, "unknown-model") as predict:
        for _ in range(2):  # the second predict writes to pi's closed stdin
            with pytest.raises(RuntimeError, match='"no-such-model" not found'):
                predict(_user("Go."))


@pytest.mark.parametrize("failure", ["no-api-key", "provider-error"])
def test_pi_raises_promptly_when_pi_rejects_the_prompt(
    pi_runtime: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    if failure == "no-api-key":
        monkeypatch.setenv("PI_PROVIDER", "anthropic")
        monkeypatch.setenv("PI_MODEL", "claude-sonnet-4-6")
    harness = _implementation().PiHarness()
    started = time.monotonic()
    with _episode(harness, failure) as predict, pytest.raises(RuntimeError) as error:
        predict(_user("Go."))
    assert time.monotonic() - started < 10
    assert ("API key" if failure == "no-api-key" else "400") in str(error.value)


def test_pi_close_ends_every_live_process(pi_runtime: Path, fake_llm: _FakeLLM) -> None:
    harness = _implementation().PiHarness()
    fake_llm.script("One.", "Two.")
    with _episode(harness, "one") as first, _episode(harness, "two") as second:
        first(_user("Go."))
        second(_user("Go."))
        pids = _pids(pi_runtime)
        assert len(pids) == 2 and all(map(_alive, pids))
        harness.close()
        assert not any(map(_alive, pids))
