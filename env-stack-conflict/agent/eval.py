from rlmesh.numpy import RemoteEnv

from helpers import close_all, evaluate, report
from policy import make_policy

SEED = 0
POLICY_SEED = 56
MAX_STEPS = 500
RECORD = False
WATCH = False

envs = {
    "safety/mujoco2.3": RemoteEnv("tcp://127.0.0.1:5555"),
    "modern/mujoco3.3": RemoteEnv("tcp://127.0.0.1:5556"),
}

results = evaluate(
    make_policy(POLICY_SEED),
    envs,
    seed=SEED,
    max_steps=MAX_STEPS,
    record=RECORD,
    watch=WATCH,
)
report(results)
close_all(envs)
