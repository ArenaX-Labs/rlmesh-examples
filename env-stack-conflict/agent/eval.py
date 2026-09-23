from rlmesh.numpy import RemoteEnv

from helpers import close_all, evaluate, report
from policy import make_policy

SEED = 0
POLICY_SEED = 56
MAX_STEPS = 500
RECORD = False
WATCH = False

envs = {
    "safety/mujoco2.3": RemoteEnv("127.0.0.1:50051"),
    "modern/mujoco3.3": RemoteEnv("127.0.0.1:50052"),
}

try:
    results = evaluate(
        make_policy(POLICY_SEED),
        envs,
        seed=SEED,
        max_steps=MAX_STEPS,
        record=RECORD,
        watch=WATCH,
    )
    report(results)
finally:
    close_all(envs)
