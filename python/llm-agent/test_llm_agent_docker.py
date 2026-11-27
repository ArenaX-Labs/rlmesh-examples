from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.docker

HERE = Path(__file__).resolve().parent

FAKE_HARNESS = """\
from fake_llm import scripted
from harness import LLMHarness


class FakeHarness(LLMHarness):
    def __init__(self) -> None:
        super().__init__(model="fake", chat=scripted("", "5"))
"""

IMAGES = """\
ARG HARNESS
FROM ${HARNESS} AS model
COPY fake_harness.py .
ENV RLMESH_SERVE_TARGET=fake_harness:FakeHarness

FROM ${HARNESS} AS env
ENV RLMESH_OUTPUT_DIR=/rlmesh/output/env
ENTRYPOINT ["python", "-m", "rlmesh.serve", "--env", "chat_env:AdditionTask"]
"""


def test_harness_image_solves_addition_env_image(
    docker_build: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    harness = docker_build(HERE, "-f", str(HERE / "docker/harness.Dockerfile"))
    context = tmp_path / "context"
    context.mkdir()
    (context / "fake_harness.py").write_text(FAKE_HARNESS)
    (context / "Dockerfile").write_text(IMAGES)
    tags = {
        target: docker_build(context, "--target", target, "--build-arg", f"HARNESS={harness}")
        for target in ("model", "env")
    }

    monkeypatch.syspath_prepend(str(HERE))
    import run_docker

    output = tmp_path / "output"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_docker.py",
            "--env-image",
            tags["env"],
            "--harness-image",
            tags["model"],
            "--output",
            str(output),
        ],
    )
    run_docker.main()

    assert "seed=0 steps=1 reward=1.000 success=True" in capsys.readouterr().out
    assert len(list((output / "trajectories").glob("*.json"))) == 1
    assert len(list((output / "env").glob("*.jsonl"))) == 1
