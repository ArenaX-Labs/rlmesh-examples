from pathlib import Path

import pytest

HERE = Path(__file__).parent


def test_client_runs_episodes_against_the_served_factory(serve, run_script, port):
    address = f"127.0.0.1:{port}"
    serve_env = {"RLMESH_ADDRESS": address}
    serve(
        "-m",
        "rlmesh.serve",
        "--env",
        "hello_env:HelloEnv",
        cwd=HERE,
        env=serve_env,
        ready="RLMesh serving env",
    )
    out = run_script("run.py", "--address", address, "--episodes", "3", cwd=HERE)
    assert "episodes=3 " in out


@pytest.mark.docker
def test_client_runs_episodes_against_the_image(docker_build, run_script):
    image = docker_build(HERE)
    assert "episodes=2 " in run_script("run.py", "--image", image, "--episodes", "2", cwd=HERE)
