import safety_gymnasium
from rlmesh import EnvServer
from wrappers import SafetyToGymnasiumWithCost

env = SafetyToGymnasiumWithCost(
    safety_gymnasium.make("SafetyHalfCheetahVelocity-v1", render_mode="rgb_array")
)
EnvServer(env, "tcp://127.0.0.1:5557").serve()
