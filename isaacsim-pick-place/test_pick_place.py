import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest
import rlmesh.adapters as adapt

sys.path.insert(0, str(Path(__file__).parent))
from run import SPEC, PickPlacePolicy, main  # noqa: E402
from ur10e_pick_place import ACTION_SPACE, UR10ePickPlace, observation_space  # noqa: E402


def policy_obs():
    return {
        "camera": np.zeros((3, 128, 128), np.float32),
        "task": "Move the cube",
        "object": np.array([0.5, 0, 0.025]),
        "goal": np.array([0.5, 0.4, 0.025]),
        "state": np.zeros(7),
    }


def test_adapter_converts_observations_and_actions():
    adapter = adapt.resolve(UR10ePickPlace.tags, observation_space(224), ACTION_SPACE, SPEC)
    image = np.empty((224, 224, 3), np.uint8)
    image[:] = [0, 128, 255]
    obs = {
        "image": image.copy(),
        "joint_pos": np.zeros(6, np.float32),
        "eef_pos": np.array([0.5, 0.0, 0.325], np.float32),
        "eef_quat": np.array([np.sqrt(0.5), 0, 0, np.sqrt(0.5)], np.float32),
        "gripper": np.array([0.25], np.float32),
        "cube_pos": np.array([0.5, 0.0, 0.025], np.float32),
        "target_pos": np.array([0.5, 0.4, 0.025], np.float32),
        "instruction": "Move the cube",
    }
    payload = adapter.transform_obs(obs)
    assert payload["camera"].shape == (3, 128, 128) and payload["camera"].dtype == np.float32
    for channel, expected in zip(payload["camera"], [0.0, 128 / 255, 1.0], strict=True):
        np.testing.assert_allclose(channel, expected)
    np.testing.assert_allclose(payload["state"], [0.5, 0, 0.325, 0, 0, np.pi / 2, 0], atol=1e-6)
    np.testing.assert_array_equal(payload["object"], obs["cube_pos"])
    np.testing.assert_array_equal(payload["goal"], obs["target_pos"])
    assert payload["task"] == "Move the cube"
    for grip, angle in [(-2, 0.0), (-1, 0.0), (0, 0.25), (1, 0.5), (2, 0.5)]:
        np.testing.assert_allclose(
            adapter.transform_action(np.array([grip, 0.5, 0.2, 0.325], np.float32)),
            [0.5, 0.2, 0.325, angle],
        )
    np.testing.assert_array_equal(obs["image"], image)


def test_policy_waits_for_arrival_and_restarts_on_reset():
    policy, obs = PickPlacePolicy(), policy_obs()
    for _ in range(20):
        policy.predict(obs)
    assert policy.phase == 0
    obs["state"][:3] = [0.5, 0, 0.325]
    policy.predict(obs)
    assert policy.phase == 1
    policy.reset()
    assert policy.phase == 0 and policy.pickup is None


def test_policy_lifts_transports_and_releases():
    policy, obs = PickPlacePolicy(), policy_obs()
    actions = []
    for _ in range(120):
        action = policy.predict(obs)
        actions.append(action)
        obs["state"][:3] = action[1:]
        if action[0] == 1.0:
            obs["object"][2] = 0.2

    np.testing.assert_allclose(actions[0], [-1, 0.5, 0, 0.325])
    for expected in ([1, 0.5, 0, 0.325], [1, 0.5, 0.4, 0.325], [-1, 0.5, 0.4, 0.21]):
        assert any(np.allclose(a, expected) for a in actions), expected
    np.testing.assert_allclose(actions[-1], [-1, 0.5, 0.4, 0.325])

    policy.reset()
    obs["object"] = np.array([0.48, 0.01, 0.025])
    np.testing.assert_allclose(policy.predict(obs), [-1, 0.48, 0.01, 0.325])


@pytest.mark.parametrize("episodes, success_rate", [(3, 0.0), (1, 1.0), (0, None)])
def test_check_rejects_failed_or_incomplete_runs(monkeypatch, episodes, success_rate):
    monkeypatch.setenv("RLMESH_ENV_ADDRESS", "127.0.0.1:7447#k/env")
    monkeypatch.setattr(sys, "argv", ["run.py", "--episodes", "3", "--check"])
    result = SimpleNamespace(num_episodes=episodes, total_steps=10, success_rate=success_rate)
    with patch("run.Model") as model, patch("run.rlmesh.Recorder"):
        model.return_value.run.return_value = result
        with pytest.raises(SystemExit, match="check failed"):
            main()
