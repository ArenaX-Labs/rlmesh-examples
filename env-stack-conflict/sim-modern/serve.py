import gymnasium as gym
from rlmesh import EnvServer

env = gym.make("HalfCheetah-v5", render_mode="rgb_array")
EnvServer(env, "tcp://127.0.0.1:5556").serve()
