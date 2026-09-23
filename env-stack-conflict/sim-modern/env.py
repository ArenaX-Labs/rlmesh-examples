import gymnasium as gym
import rlmesh


class HalfCheetahModern(rlmesh.EnvFactory):
    """HalfCheetah-v5 on Gymnasium 1.x / MuJoCo 3.x."""

    workflow_edition = "2026.06"

    def make(self) -> gym.Env:
        return gym.make("HalfCheetah-v5", render_mode="rgb_array")
