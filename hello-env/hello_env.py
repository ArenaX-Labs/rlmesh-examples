"""A 1-D walk to a target, served through an RLMesh factory."""

import gymnasium as gym
import numpy as np
import rlmesh


class LineWalk(gym.Env):
    """Step left (0) or right (1) until you reach the target cell."""

    def __init__(self, size: int) -> None:
        if size < 1:
            raise ValueError("size must be at least 1")
        self.size = size
        self.observation_space = gym.spaces.Box(0.0, 1.0, shape=(2,), dtype=np.float32)
        self.action_space = gym.spaces.Discrete(2)

    def _obs(self) -> np.ndarray:
        return np.array([self.pos, self.target], dtype=np.float32) / self.size

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.pos, self.target = self.np_random.choice(self.size + 1, size=2, replace=False)
        return self._obs(), {}

    def step(self, action):
        self.pos = int(np.clip(self.pos + (1 if action == 1 else -1), 0, self.size))
        done = self.pos == self.target
        return self._obs(), 1.0 if done else -0.01, done, False, {"is_success": done}


class HelloEnv(rlmesh.EnvFactory):
    params = rlmesh.ParamSpec(
        rlmesh.Param(
            "size", type="int", description="Distance between the endpoints (at least 1)."
        ),
    )

    @classmethod
    def enumerate_variants(cls):
        yield rlmesh.Variant("short", {"size": 5}, name="Short line")
        yield rlmesh.Variant("long", {"size": 50}, name="Long line")

    def make(self, *, size: int = 10) -> gym.Env:
        return gym.wrappers.TimeLimit(LineWalk(size), max_episode_steps=4 * size)
