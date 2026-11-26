from pathlib import Path


def test_dry_run_resolves_every_model_env_pairing(run_script):
    out = run_script("run.py", cwd=Path(__file__).parent)
    assert out.count("=== ") == 12 and out.count("env action:") == 12
