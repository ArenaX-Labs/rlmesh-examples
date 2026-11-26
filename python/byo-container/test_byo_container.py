from pathlib import Path

import pytest

HERE = Path(__file__).parent


@pytest.mark.docker
def test_model_image_runs_against_env_image(docker_build, run_script):
    env, model = docker_build(HERE / "env"), docker_build(HERE / "model")
    out = run_script("run.py", "--env-image", env, "--model-image", model, cwd=HERE, timeout=600)
    assert "episodes=2 " in out
