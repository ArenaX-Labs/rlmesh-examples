"""CPU check of the real environment tags and client spec: uv run python -m unittest."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import rlmesh.adapters as adapt
from run import SPEC, PickPlacePolicy, main
from ur10e_pick_place import ACTION_SPACE, UR10ePickPlace, observation_space


class AdapterTest(unittest.TestCase):
    def test_observation_conversion_and_action_mapping(self):
        adapter = adapt.resolve(
            UR10ePickPlace.tags, observation_space(224), ACTION_SPACE, SPEC
        )
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
        self.assertEqual(payload["camera"].shape, (3, 128, 128))
        self.assertEqual(payload["camera"].dtype, np.float32)
        for channel, expected in zip(
            payload["camera"], [0.0, 128 / 255, 1.0], strict=True
        ):
            np.testing.assert_allclose(channel, expected)
        np.testing.assert_allclose(
            payload["state"], [0.5, 0, 0.325, 0, 0, np.pi / 2, 0], atol=1e-6
        )
        np.testing.assert_array_equal(payload["object"], obs["cube_pos"])
        np.testing.assert_array_equal(payload["goal"], obs["target_pos"])
        self.assertEqual(payload["task"], "Move the cube")
        for grip, angle in [(-2, 0.0), (-1, 0.0), (0, 0.25), (1, 0.5), (2, 0.5)]:
            np.testing.assert_allclose(
                adapter.transform_action(np.array([grip, 0.5, 0.2, 0.325], np.float32)),
                [0.5, 0.2, 0.325, angle],
            )
        np.testing.assert_array_equal(obs["image"], image)

    def test_policy_restarts_and_does_not_advance_before_arrival(self):
        policy = PickPlacePolicy()
        obs = {
            "camera": np.zeros((3, 128, 128), np.float32),
            "task": "Move the cube",
            "object": np.array([0.5, 0, 0.025]),
            "goal": np.array([0.5, 0.4, 0.025]),
            "state": np.zeros(7),
        }
        for _ in range(20):
            policy.predict(obs)
        self.assertEqual(policy.phase, 0)
        obs["state"][:3] = [0.5, 0, 0.325]
        policy.predict(obs)
        self.assertEqual(policy.phase, 1)
        policy.reset()
        self.assertEqual(policy.phase, 0)
        self.assertIsNone(policy.pickup)

    def test_policy_lifts_transports_and_releases_before_reset(self):
        policy = PickPlacePolicy()
        obs = {
            "camera": np.zeros((3, 128, 128), np.float32),
            "task": "Move the cube",
            "object": np.array([0.5, 0, 0.025]),
            "goal": np.array([0.5, 0.4, 0.025]),
            "state": np.zeros(7),
        }
        actions = []
        for _ in range(120):
            action = policy.predict(obs)
            actions.append(action)
            # Follow the command, and let the object move once the gripper closes.
            # The policy must keep its original pickup reference during the lift.
            obs["state"][:3] = action[1:]
            if action[0] == 1.0:
                obs["object"][2] = 0.2

        np.testing.assert_allclose(actions[0], [-1, 0.5, 0, 0.325])
        self.assertTrue(any(np.allclose(a, [1, 0.5, 0, 0.325]) for a in actions))
        self.assertTrue(any(np.allclose(a, [1, 0.5, 0.4, 0.325]) for a in actions))
        self.assertTrue(any(np.allclose(a, [-1, 0.5, 0.4, 0.21]) for a in actions))
        np.testing.assert_allclose(actions[-1], [-1, 0.5, 0.4, 0.325])

        policy.reset()
        obs["object"] = np.array([0.48, 0.01, 0.025])
        np.testing.assert_allclose(policy.predict(obs), [-1, 0.48, 0.01, 0.325])

    def test_check_rejects_failed_or_incomplete_runs(self):
        with (
            patch("sys.argv", ["run.py", "--episodes", "3", "--check"]),
            patch("run.Model") as model,
            patch("run.rlmesh.Recorder"),
        ):
            session = model.return_value.session.return_value.__enter__.return_value
            for count, success_rate in [(3, 0.0), (1, 1.0), (0, None)]:
                with self.subTest(episodes=count, success_rate=success_rate):
                    session.run.return_value = SimpleNamespace(
                        num_episodes=count, total_steps=10, success_rate=success_rate
                    )
                    with self.assertRaisesRegex(SystemExit, "check failed"):
                        main()
            session.run.return_value = SimpleNamespace(
                num_episodes=3, total_steps=260, success_rate=1.0
            )
            main()


if __name__ == "__main__":
    unittest.main()
