import gymnasium as gym
from helpers import close_all, evaluate, report
from policy import make_policy
from rlmesh.numpy import RemoteEnv

SEED = 0
MAX_STEPS = 100
RECORD = True

policy, source = make_policy()

envs = {
    "modern-halfcheetah-v5": gym.make(
        "HalfCheetah-v5", render_mode="rgb_array" if RECORD else None
    ),
    "safety-halfcheetah-velocity": RemoteEnv("tcp://127.0.0.1:5557"),
}

results = evaluate(policy, envs, seed=SEED, max_steps=MAX_STEPS, record=RECORD)
report(results, source=source)
close_all(envs)
