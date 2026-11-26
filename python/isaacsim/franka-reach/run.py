"""Drive the served Franka reach env with a scripted policy: move straight at the target.

RLMESH_ENV_ADDRESS='127.0.0.1:7447#<key>/env' uv run run.py
"""

import argparse
import os

import numpy as np
import rlmesh
from rlmesh.numpy import Model

MAX_DELTA = 0.05


def predict(obs):
    return np.clip(obs["target_pos"] - obs["eef_pos"], -MAX_DELTA, MAX_DELTA).astype(np.float32)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    # The address carries the session key: read it from the environment, not the command line.
    parser.add_argument("--address", default=os.environ.get("RLMESH_ENV_ADDRESS"))
    parser.add_argument("--episodes", type=int, default=4)
    args = parser.parse_args()
    if not args.address:
        parser.error("set RLMESH_ENV_ADDRESS to the env's keyed address")

    result = Model(predict, spec=rlmesh.NO_ADAPTER).run(args.address, episodes=args.episodes)
    print(
        f"episodes={result.num_episodes} steps={result.total_steps} "
        f"success_rate={result.success_rate}"
    )
