import safety_gymnasium
from rlmesh import EnvServer
from safety_gymnasium.wrappers import SafetyGymnasium2Gymnasium

safety_env = safety_gymnasium.make(
    "SafetyHalfCheetahVelocity-v1", render_mode="rgb_array"
)
env = SafetyGymnasium2Gymnasium(safety_env)
EnvServer(env, "tcp://127.0.0.1:5555").serve()
