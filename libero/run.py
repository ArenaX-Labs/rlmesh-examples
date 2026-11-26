"""Drive the served LIBERO env with random actions and show what a model sees.

    uv run run.py                                  # the env served on 127.0.0.1:7447
    uv run run.py --image rlmesh-examples/libero   # the env image, run as a sandbox
    uv run run.py --image rlmesh-examples/libero \
        --make-kwargs '{"task_suite": "libero_spatial", "task_id": 0}'
"""

import argparse
import json

import numpy as np
import rlmesh
from rlmesh.numpy import Model, SandboxEnv

rng = np.random.default_rng(0)
shown = False


def predict(obs):
    global shown
    if not shown:
        for key, value in obs.items():
            print(f"{key:26s} {getattr(value, 'shape', value)!s}")
        shown = True
    return rng.uniform(-1.0, 1.0, size=7).astype(np.float32)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", default="127.0.0.1:7447")
    parser.add_argument("--image", help="start this env image as a sandbox instead")
    parser.add_argument("--make-kwargs", default="{}", help="JSON params for the image's make()")
    parser.add_argument("--episodes", type=int, default=2)
    parser.add_argument("--max-steps", type=int, default=50)
    args = parser.parse_args()

    # NO_ADAPTER: take the env's observation dict as-is instead of adapting it to a model spec.
    model = Model(predict, spec=rlmesh.NO_ADAPTER)
    run = {"episodes": args.episodes, "max_episode_steps": args.max_steps}
    if args.image:
        params = json.loads(args.make_kwargs)
        with SandboxEnv(f"image://{args.image}", connect_timeout_seconds=300, **params) as env:
            result = model.run(env, **run)
    else:
        result = model.run(args.address, **run)
    print(
        f"episodes={result.num_episodes} "
        f"success_rate={result.success_rate:.2f} steps={result.total_steps}"
    )


if __name__ == "__main__":
    main()
