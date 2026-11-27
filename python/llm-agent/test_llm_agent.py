from __future__ import annotations

import contextlib
import json
import re
import sys
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

HERE = Path(__file__).resolve().parent


def test_harness_solves_served_addition_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, serve: Any, port: int
) -> None:
    monkeypatch.setenv("RLMESH_OUTPUT_DIR", str(tmp_path))
    monkeypatch.syspath_prepend(str(HERE))
    from fake_llm import scripted
    from harness import LLMHarness

    harness = LLMHarness(model="fake", chat=scripted("", "5"))
    line = serve("chat_env.py", "--address", f"127.0.0.1:{port}/env", cwd=HERE, ready="serving ")
    result = harness.run(line.rsplit(" on ", 1)[1], seeds=[0])

    episode = result.episodes[0]
    assert episode.success is True
    assert episode.terminated and episode.steps == 1

    (path,) = (tmp_path / "trajectories").glob("*.json")
    trajectory = json.loads(path.read_text())
    user, agent = trajectory["steps"]
    assert user["source"] == "user" and "2 + 3" in user["message"]
    assert (agent["source"], agent["message"], agent["llm_call_count"]) == ("agent", "5", 1)
    assert agent["extra"]["rlmesh_step"] == 0
    (env_log,) = (tmp_path / "env").glob("*.jsonl")
    assert json.loads(env_log.read_text())["rewards"] == {"correct": 1.0}


class _Msg(SimpleNamespace):
    def model_dump(self, **_: Any) -> dict[str, Any]:
        return dict(vars(self))


class _FakeEnv:
    max_turns = 3

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.rubric = SimpleNamespace(score_rollout=self._score)

    def get_eval_dataset(self) -> list[dict[str, Any]]:
        return [{"example_id": 7}]

    async def _score(self, state: dict[str, Any]) -> None:
        state["reward"] = 1.0

    async def rollout(self, row: Any, client: Any, model: str) -> dict[str, Any]:
        if self.mode == "raise":
            raise ValueError("no dataset")
        state: dict[str, Any] = {}
        if self.mode == "error":
            state["error"] = ValueError("bad setup")
            return state
        call = {"id": "c1", "name": "lookup", "arguments": '{"q": "x"}'}
        prompt = [
            _Msg(role="system", content="rules"),
            _Msg(role="user", content="example"),
            _Msg(role="assistant", content="shot", tool_calls=[call]),
            _Msg(role="tool", tool_call_id="c1", content="found"),
            _Msg(role="user", content="go"),
        ]
        tool = SimpleNamespace(name="lookup", description="find", parameters={})
        reply = await client.get_response(
            prompt=prompt, model=model, tools=[tool], sampling_args={}, state=state
        )
        prompt += [
            _Msg(role="assistant", content=reply.message.content),
            _Msg(role="user", content="again"),
        ]
        await client.get_response(
            prompt=prompt, model=model, tools=None, sampling_args={}, state=state
        )
        return {**state, "metrics": {"correct_answer": 1.0}, "stop_condition": "done"}


def _stub_verifiers_v0(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    verifiers = ModuleType("verifiers")
    verifiers.__dict__.update(
        Client=type("Client", (), {"__init__": lambda self, config: None}),
        load_environment=_FakeEnv,
    )
    types = ModuleType("verifiers.types")
    types.__dict__.update(
        Response=SimpleNamespace,
        ResponseMessage=SimpleNamespace,
        ToolCall=SimpleNamespace,
    )
    monkeypatch.setitem(sys.modules, "verifiers", verifiers)
    monkeypatch.setitem(sys.modules, "verifiers.types", types)
    monkeypatch.delitem(sys.modules, "serve_v0", raising=False)
    request.addfinalizer(lambda: sys.modules.pop("serve_v0", None))


def test_v0_bridge_turns_reset_and_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    monkeypatch.setenv("RLMESH_OUTPUT_DIR", str(tmp_path))
    monkeypatch.syspath_prepend(str(HERE))
    _stub_verifiers_v0(monkeypatch, request)
    from serve_v0 import EnvironmentEnv

    env = EnvironmentEnv("fake")
    obs, info = env.reset(seed=0)
    assert json.loads(obs) == {
        "messages": [
            {"role": "system", "content": "rules"},
            {"role": "user", "content": "example"},
            {
                "role": "assistant",
                "content": "shot",
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "lookup", "arguments": '{"q": "x"}'},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "c1", "content": "found"},
            {"role": "user", "content": "go"},
        ],
        "tools": [
            {
                "type": "function",
                "function": {"name": "lookup", "description": "find", "parameters": {}},
            }
        ],
    }
    assert info == {"task_id": "7"}
    obs, _, done, _, _ = env.step(json.dumps({"role": "assistant", "content": "a"}))
    assert json.loads(obs) == {
        "messages": [{"role": "user", "content": "again"}],
        "tools": [],
    }
    assert not done

    abandoned = env.rollout
    obs, _ = env.reset(seed=0)
    assert abandoned is not None and abandoned.cancelled()
    assert json.loads(obs)["messages"][0]["role"] == "system"
    env.step(json.dumps({"role": "assistant", "content": "a"}))
    _, reward, done, truncated, info = env.step(json.dumps({"role": "assistant", "content": "b"}))
    assert (reward, done, truncated, info["is_success"]) == (1.0, True, False, True)

    env.reset(seed=0)
    env.close()
    assert env.loop.is_closed()

    failing = EnvironmentEnv("raise")
    with pytest.raises(ValueError, match="no dataset"):
        failing.reset(seed=0)
    failing.close()

    erroring = EnvironmentEnv("error")
    with pytest.raises(RuntimeError, match=re.escape(repr(ValueError("bad setup")))):
        erroring.reset(seed=0)
    erroring.close()


class _FakeV1Env:
    def __init__(self, config: Any) -> None:
        self.taskset = SimpleNamespace(
            load=lambda: [SimpleNamespace(data=SimpleNamespace(name="t7"))]
        )
        self.seen: list[Any] = []
        self.served = False
        self.calls = 2
        self.trace_errors: list[Any] = []
        self.episode_errors: list[Any] = []
        self.stop_condition = "user_completed"

    @contextlib.asynccontextmanager
    async def serving(self) -> Any:
        self.served = True
        yield
        self.served = False

    async def run_episode(self, task: Any, ctx: Any) -> Any:
        client = sys.modules["verifiers.v1.interception.server"].resolve_client(None)
        dialect = SimpleNamespace(
            upstream_path="/chat/completions",
            validate_response=lambda raw: raw,
            parse_response=lambda raw: SimpleNamespace(message=raw["choices"][0]["message"]),
        )
        tools = [{"type": "function", "function": {"name": "lookup"}}]
        messages = [
            {"role": "system", "content": "policy"},
            {"role": "user", "content": "my phone is broken"},
        ]
        for _ in range(self.calls):
            reply = await client.get_response(
                dialect,
                {"messages": messages, "tools": tools},
                None,
                session_id="s",
                turn=None,
                headers={},
            )
            self.seen.append(reply.message)
            messages = [
                *messages,
                reply.message,
                {"role": "tool", "tool_call_id": "c1", "content": "ok"},
            ]
        reward = SimpleNamespace(score=1.0)
        trace = SimpleNamespace(
            rewards={"tau2_reward": reward, "skipped": None},
            reward=1.0,
            metrics={"turns": 2.0},
            stop_condition=self.stop_condition,
            is_timeout=False,
            is_truncated=False,
            errors=self.trace_errors,
        )
        return SimpleNamespace(traces=[trace], errors=self.episode_errors, is_timeout=False)


class _UnservableV1Env(_FakeV1Env):
    @contextlib.asynccontextmanager
    async def serving(self) -> Any:
        raise OSError("port in use")
        yield


def _unbridged(config: Any) -> Any:
    raise AssertionError("no bridge")


def _stub_verifiers_v1(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    v1 = ModuleType("verifiers.v1")
    v1.__dict__.update(
        Client=object,
        taskset_config_type=lambda env_id: SimpleNamespace,
        env_config_type=lambda env_id: SimpleNamespace,
        load_environment=_FakeV1Env,
        ModelContext=SimpleNamespace,
        EvalClientConfig=SimpleNamespace,
        TasksetConfig=SimpleNamespace,
    )
    interception = ModuleType("verifiers.v1.interception")
    server = ModuleType("verifiers.v1.interception.server")
    server.__dict__["resolve_client"] = _unbridged
    verifiers = ModuleType("verifiers")
    verifiers.__dict__["v1"] = v1
    v1.__dict__["interception"] = interception
    interception.__dict__["server"] = server
    for module in (verifiers, v1, interception, server):
        monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.delitem(sys.modules, "serve_v1", raising=False)
    request.addfinalizer(lambda: sys.modules.pop("serve_v1", None))


def test_v1_env_bridge_turns_and_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    monkeypatch.setenv("RLMESH_OUTPUT_DIR", str(tmp_path))
    monkeypatch.syspath_prepend(str(HERE))
    _stub_verifiers_v1(monkeypatch, request)
    from serve_v1 import V1EnvEnv

    env = V1EnvEnv("tau2", "telecom")
    obs, info = env.reset(seed=0)
    assert json.loads(obs) == {
        "messages": [
            {"role": "system", "content": "policy"},
            {"role": "user", "content": "my phone is broken"},
        ],
        "tools": [{"type": "function", "function": {"name": "lookup"}}],
    }
    assert info == {"task_id": "t7"}
    call = {
        "id": "c1",
        "type": "function",
        "function": {"name": "lookup", "arguments": "{}"},
    }
    obs, _, done, _, _ = env.step(json.dumps({"content": None, "tool_calls": [call]}))
    assert env.env.seen[0] == {
        "content": None,
        "tool_calls": [call],
        "role": "assistant",
    }
    assert json.loads(obs)["messages"] == [{"role": "tool", "tool_call_id": "c1", "content": "ok"}]
    assert not done
    _, reward, done, truncated, info = env.step(
        json.dumps({"role": "assistant", "content": "fixed"})
    )
    assert (reward, done, truncated, info["is_success"]) == (1.0, True, False, True)
    assert info["rewards"] == {"tau2_reward": 1.0}
    assert info["stop_condition"] == "user_completed"

    env.env.episode_errors = [SimpleNamespace(type="EnvError", message="no seat")]
    env.env.trace_errors = [SimpleNamespace(type="HarnessError", message="exited 1")]
    env.env.calls = 0
    with pytest.raises(
        RuntimeError,
        match=r"first model call: \['EnvError: no seat', 'HarnessError: exited 1'\]",
    ):
        env.reset(seed=1)

    env.close()
    assert env.loop.is_closed() and not env.env.served


def test_v1_env_bridge_max_steps_truncates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    monkeypatch.setenv("RLMESH_OUTPUT_DIR", str(tmp_path))
    monkeypatch.syspath_prepend(str(HERE))
    _stub_verifiers_v1(monkeypatch, request)
    from serve_v1 import V1EnvEnv

    env = V1EnvEnv("tau2", max_steps=1)
    env.reset(seed=0)
    obs, reward, done, truncated, info = env.step(json.dumps({"content": "hi"}))
    assert (json.loads(obs)["messages"], reward, done, truncated) == (
        [],
        0.0,
        False,
        True,
    )
    assert (info["stop_condition"], info["is_success"]) == ("max_steps", False)
    assert env.episode is None and len(env.env.seen) == 1

    env.env.calls = 1
    env.env.stop_condition = "tau2_max_steps"
    env.reset(seed=0)
    _, _, done, truncated, info = env.step(json.dumps({"content": "hi"}))
    assert (done, truncated, info["stop_condition"]) == (False, True, "tau2_max_steps")
    env.close()


def _fail_first(load: Any, calls: list[Any]) -> Any:
    def flaky(config: Any) -> Any:
        calls.append(config)
        if len(calls) == 1:
            raise ValueError("hub down")
        return load(config)

    return flaky


def test_v0_env_reads_env_vars_and_retries_a_failed_first_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    monkeypatch.setenv("RLMESH_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("ENV_ID", "fake")
    monkeypatch.setenv("MAX_TURNS", "5")
    monkeypatch.syspath_prepend(str(HERE))
    _stub_verifiers_v0(monkeypatch, request)
    loads: list[str] = []
    monkeypatch.setattr(
        sys.modules["verifiers"],
        "load_environment",
        _fail_first(lambda _: _FakeEnv("ok"), loads),
    )
    from serve_v0 import EnvironmentEnv

    env = EnvironmentEnv()
    assert loads == []
    with pytest.raises(ValueError, match="hub down"):
        env.reset(seed=0)
    env.reset(seed=0)
    env.reset(seed=0)
    assert loads == ["fake", "fake"] and env.env.max_turns == 5
    env.close()


def test_v1_envs_read_env_vars_and_retry_a_failed_first_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    monkeypatch.setenv("RLMESH_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("TASKSET", "primeintellect/gpqa")
    monkeypatch.setenv("ENV_ID", "tau2")
    monkeypatch.setenv("DOMAIN", "airline")
    monkeypatch.setenv("MAX_STEPS", "3")
    monkeypatch.syspath_prepend(str(HERE))
    _stub_verifiers_v1(monkeypatch, request)
    tasksets: list[Any] = []
    configs: list[Any] = []
    data = SimpleNamespace(name="q0", prompt="2 + 2?", system_prompt=None)
    v1 = sys.modules["verifiers.v1"]
    monkeypatch.setattr(
        v1,
        "load_taskset",
        _fail_first(
            lambda _: SimpleNamespace(load=lambda: [SimpleNamespace(data=data)]),
            tasksets,
        ),
        raising=False,
    )
    monkeypatch.setattr(v1, "load_environment", _fail_first(_FakeV1Env, configs))
    from serve_v1 import TasksetEnv, V1EnvEnv

    for env, loads in ((TasksetEnv(), tasksets), (V1EnvEnv(), configs)):
        assert loads == []
        with pytest.raises(ValueError, match="hub down"):
            env.reset(seed=0)
        env.reset(seed=0)
        env.reset(seed=0)
        assert len(loads) == 2
        env.close()
    assert tasksets[-1].id == "primeintellect/gpqa"
    assert configs[-1].taskset.domain == "airline"
    with pytest.raises(ValueError, match="at least 1"):
        V1EnvEnv(max_steps=0)


def test_v1_env_serves_one_lane_per_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    monkeypatch.setenv("RLMESH_OUTPUT_DIR", str(tmp_path))
    monkeypatch.syspath_prepend(str(HERE))
    _stub_verifiers_v1(monkeypatch, request)
    from serve_v1 import V1EnvEnv

    server = sys.modules["verifiers.v1.interception.server"]
    v1 = sys.modules["verifiers.v1"]
    first, second = V1EnvEnv("tau2"), V1EnvEnv("tau2")
    monkeypatch.setattr(v1, "load_environment", _UnservableV1Env)
    with pytest.raises(OSError, match="port in use"):
        first.reset(seed=0)
    assert server.resolve_client is _unbridged
    monkeypatch.setattr(v1, "load_environment", _FakeV1Env)
    second.reset(seed=0)
    with pytest.raises(RuntimeError, match="RLMESH_NUM_ENVS=1"):
        first.reset(seed=0)
    second.close()
    assert server.resolve_client is _unbridged
    first.reset(seed=0)
    first.close()


def test_probe_random_text_is_answered_without_the_llm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RLMESH_OUTPUT_DIR", str(tmp_path))
    monkeypatch.syspath_prepend(str(HERE))
    from chat_env import AdditionTask
    from harness import LLMHarness

    env = AdditionTask()
    for action in ("\x00zq\ufffd", "[1, 2]", "42"):
        env.reset(seed=0)
        _, reward, done, _, info = env.step(action)
        assert (reward, done, info["is_success"]) == (0.0, True, False)

    def chat(messages: Any, tools: Any) -> tuple[dict[str, Any], None]:
        raise AssertionError("the LLM must not be called")

    harness = LLMHarness(chat=chat)
    context: Any = {
        "episode_id": "e",
        "episode_seed": 0,
        "predict_index": 0,
        "predict_seed": 0,
        "state": {},
    }
    assert json.loads(harness.predict("\x00zq", context)) == {
        "role": "assistant",
        "content": "",
    }
    assert json.loads(harness.predict("[1]", context))["content"] == ""


def test_predict_logs_redacted_images_but_sends_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RLMESH_OUTPUT_DIR", str(tmp_path))
    monkeypatch.syspath_prepend(str(HERE))
    from harness import LLMHarness

    sent: list[Any] = []

    def chat(messages: Any, tools: Any) -> tuple[dict[str, Any], None]:
        sent.append(json.loads(json.dumps(messages)))
        raise RuntimeError(f"bad request: {messages[0]['content'][0]}")

    harness = LLMHarness(model="fake", chat=chat, retries=0)
    url = "data:image/png;base64,QUJD"
    observation = json.dumps(
        {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "image_url", "image_url": {"url": url}}],
                }
            ],
            "tools": [],
        }
    )
    context: Any = {
        "episode_id": "ep",
        "episode_seed": None,
        "predict_index": 0,
        "predict_seed": None,
        "state": {},
    }
    with pytest.raises(RuntimeError):
        harness.predict(observation, context)

    assert sent[0][0]["content"][0]["image_url"]["url"] == url
    assert context["state"]["messages"][0]["content"][0]["image_url"]["url"] == url
    text = (tmp_path / "trajectories" / "ep.json").read_text()
    assert "QUJD" not in text
    user, agent = json.loads(text)["steps"]
    assert user["message"] == "[image image/png, 4 bytes]"
    assert "<redacted>" in agent["extra"]["error"]


def test_trajectory_pairs_tool_results_with_their_calls(tmp_path: Path) -> None:
    sys.path.insert(0, str(HERE))
    from trajectory import Trajectory

    trajectory = Trajectory(tmp_path / "t.json", "ep", 3, "agent", "m")
    trajectory.observe([{"role": "user", "content": "go"}], [])
    call = {"id": "c1", "function": {"name": "run_shell", "arguments": '{"command": "ls"}'}}
    usage = {"input_tokens": 10, "cache_read_input_tokens": 5, "output_tokens": 2}
    trajectory.reply(
        {"role": "assistant", "content": "", "reasoning": "look", "tool_calls": [call]},
        [usage, usage],
        rlmesh_step=0,
        latency_ms=1.0,
    )
    trajectory.observe(
        [
            {"role": "tool", "tool_call_id": "c1", "content": "a.txt"},
            {"role": "user", "content": "more"},
        ],
        [],
    )
    trajectory.save()

    document = json.loads((tmp_path / "t.json").read_text())
    _, agent, follow_up = document["steps"]
    assert agent["tool_calls"][0]["arguments"] == {"command": "ls"}
    assert agent["observation"]["results"] == [{"source_call_id": "c1", "content": "a.txt"}]
    assert agent["metrics"] == {"prompt_tokens": 30, "completion_tokens": 4, "cached_tokens": 10}
    assert (agent["reasoning_content"], agent["llm_call_count"]) == ("look", 2)
    assert (follow_up["source"], follow_up["step_id"]) == ("user", 3)
    assert document["final_metrics"]["total_prompt_tokens"] == 30


def test_anthropic_turns_replay_native_blocks_and_merge_tool_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(HERE))
    from harness import _anthropic_messages

    native = [
        {"type": "thinking", "thinking": "plan", "signature": "sig"},
        {"type": "tool_use", "id": "t1", "name": "look", "input": {}},
    ]
    call = {"id": "t2", "type": "function", "function": {"name": "move", "arguments": '{"x": 1}'}}
    system, turns = _anthropic_messages(
        [
            {"role": "system", "content": "rules"},
            {"role": "user", "content": "go"},
            {"role": "assistant", "content": "", "anthropic_content": native},
            {"role": "tool", "tool_call_id": "t1", "content": "dark"},
            {"role": "assistant", "content": "moving", "tool_calls": [call]},
            {"role": "tool", "tool_call_id": "t2", "content": "ok"},
            {"role": "tool", "tool_call_id": "t3", "content": "also"},
        ]
    )
    assert system == "rules"
    assert [turn["role"] for turn in turns] == ["user", "assistant", "user", "assistant", "user"]
    assert turns[1]["content"] == native
    assert turns[3]["content"][1] == {
        "type": "tool_use",
        "id": "t2",
        "name": "move",
        "input": {"x": 1},
    }
    assert [block["tool_use_id"] for block in turns[4]["content"]] == ["t2", "t3"]


def test_tictactoe_scores_both_seats(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RLMESH_OUTPUT_DIR", str(tmp_path))
    monkeypatch.syspath_prepend(str(HERE))
    from chat_env import TicTacToeTask

    def play(*moves: str, seed: int = 0) -> tuple[list[str], dict[str, Any]]:
        env = TicTacToeTask()
        obs, _ = env.reset(seed=seed)
        prompts = [json.loads(obs)["messages"][0]["content"]]
        for move in moves:
            obs, _, done, _, info = env.step(json.dumps({"role": "assistant", "content": move}))
            if done:
                return prompts, info
            prompts.append(json.loads(obs)["messages"][0]["content"])
        raise AssertionError("game did not end")

    prompts, info = play("1", "4", "2", "5", "3")
    assert [p.split("You are ")[1][0] for p in prompts] == ["X", "O", "X", "O", "X"]
    assert info["rewards"] == {"X": 1.0, "O": -1.0}
    assert (info["is_success"], info["reward"], info["winner"]) == (True, 1.0, "X")

    _, info = play("1", "1")
    assert info["rewards"] == {"X": 1.0, "O": -1.0} and info["winner"] == "X"
    _, info = play("seven")
    assert info["rewards"] == {"X": -1.0, "O": 1.0} and info["is_success"] is False

    prompts, info = play("seven", seed=1)
    assert prompts[0].split("You are ")[1][0] == "O"
    assert info["rewards"] == {"X": 1.0, "O": -1.0} and info["reward"] == 1.0

    _, info = play(json.dumps([{"type": "text", "text": "5"}]))
    assert info["winner"] == "O"

    _, info = play("1", "2", "3", "5", "4", "6", "8", "7", "9")
    assert info["rewards"] == {"X": 0.0, "O": 0.0} and info["winner"] == "draw"


def test_terminal_task_runs_tools_and_grades_with_hidden_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RLMESH_OUTPUT_DIR", str(tmp_path / "out"))
    monkeypatch.syspath_prepend(str(HERE))
    import terminal_env

    task, work, logs = tmp_path / "task", tmp_path / "work", tmp_path / "logs"
    (task / "tests").mkdir(parents=True)
    work.mkdir()
    (task / "name").write_text("terminal-bench/answer\n")
    (task / "instruction.md").write_text("Put 42 in answer.txt.")
    (task / "tests" / "test.sh").write_text(
        f"grep -qx 42 answer.txt && echo 1 > {logs}/reward.txt || echo 0 > {logs}/reward.txt\n"
    )
    monkeypatch.setattr(terminal_env, "TASK_DIR", task)
    monkeypatch.setattr(terminal_env, "TESTS_DIR", tmp_path / "tests")
    monkeypatch.setattr(terminal_env, "VERIFIER_DIR", logs)
    monkeypatch.chdir(work)

    def act(*calls: tuple[str, dict[str, Any]]) -> tuple[Any, ...]:
        tool_calls = [
            {"id": f"c{i}", "type": "function", "function": {"name": n, "arguments": json.dumps(a)}}
            for i, (n, a) in enumerate(calls)
        ]
        return env.step(json.dumps({"role": "assistant", "content": "", "tool_calls": tool_calls}))

    env = terminal_env.TerminalTask()
    assert not (task / "tests").exists() and terminal_env.TerminalTask().tests == env.tests
    obs, _ = env.reset(seed=0)
    first = json.loads(obs)
    assert "Put 42" in first["messages"][0]["content"]
    assert [t["function"]["name"] for t in first["tools"]] == ["run_shell", "write_file", "submit"]

    obs, _, done, _, _ = act(
        ("write_file", {"path": "answer.txt", "content": "42\n"}),
        ("run_shell", {"command": "cat answer.txt; env"}),
        ("run_shell", {"command": "sleep 5 & echo started"}),
    )
    results = json.loads(obs)["messages"]
    assert not done and [m["tool_call_id"] for m in results] == ["c0", "c1", "c2"]
    assert results[1]["content"].startswith("exit code 0\n42")
    assert "RLMESH_OUTPUT_DIR" not in results[1]["content"]
    assert results[2]["content"] == "exit code 0\nstarted\n"
    assert not (tmp_path / "tests").exists()

    # A step that submits keeps the verifier's share of the budget from its commands.
    monkeypatch.setattr(terminal_env, "STEP_BUDGET_S", 6.0)
    monkeypatch.setattr(terminal_env, "VERIFIER_BUDGET_S", 4.0)
    started = time.monotonic()
    obs, reward, done, truncated, info = act(("run_shell", {"command": "sleep 5"}), ("submit", {}))
    assert time.monotonic() - started < 4
    assert json.loads(obs)["messages"][0]["content"].startswith("timed out after 2s")
    assert (reward, done, truncated, info["is_success"]) == (1.0, True, False, True)
    assert info["task_id"] == "terminal-bench/answer" and info["turns"] == 2
    assert env.render().shape == (720, 1280, 3)


def test_render_draws_each_wordle_row_and_the_latest_turn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RLMESH_OUTPUT_DIR", str(tmp_path))
    monkeypatch.syspath_prepend(str(HERE))
    from chat_env import TicTacToeTask
    from render import _with_final_guess, board

    feedback = "\nC R A N E\nX G X X X\nYou have 5 guesses left."
    messages = [
        {"role": "user", "content": [{"type": "text", "text": feedback}]},
        {"role": "assistant", "content": "R O B O T\nG G G G G"},
        {"role": "user", "content": "\nT R I O S\nY G Y X X\n"},
    ]
    assert board(messages) == [("CRANE", "XGXXX"), ("TRIOS", "YGYXX")]
    won = [*messages, {"role": "assistant", "content": "<guess>[brass]</guess>"}]
    won.append({"role": "user", "content": "Congratulations! You guessed the word correctly!"})
    assert _with_final_guess(won, board(won), True)[-1] == ("BRASS", "GGGGG")
    assert _with_final_guess(won, board(won), None) == board(won)

    env = TicTacToeTask()
    env.reset(seed=0)
    env.step(json.dumps({"role": "assistant", "content": "5"}))
    assert [m["role"] for m in env.history] == ["user", "assistant", "user"]
    assert env.render().shape == (720, 1280, 3)
