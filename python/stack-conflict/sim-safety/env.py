import rlmesh
import safety_gymnasium
from safety_gymnasium.wrappers import SafetyGymnasium2Gymnasium


class HalfCheetahSafety(rlmesh.EnvFactory):
    """SafetyHalfCheetahVelocity-v1 on Safety-Gymnasium 1.0 / MuJoCo 2.3, with info["cost"]."""

    def make(self):
        env = safety_gymnasium.make("SafetyHalfCheetahVelocity-v1", render_mode="rgb_array")
        return SafetyGymnasium2Gymnasium(env)
