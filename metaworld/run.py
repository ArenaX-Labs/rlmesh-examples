"""Drive the served Meta-World env with random actions and show what a model sees.

    uv run run.py                      # against 127.0.0.1:50051
    uv run run.py --episodes 3 --max-steps 50
"""

import argparse

import numpy as np
import rlmesh
from rlmesh.numpy import Model

rng = np.random.default_rng(0)
shown = False


def predict(obs):
    global shown
    if not shown:
        print(f"image={obs['image'].shape} state={obs['state'].shape} task={obs['task']!r}")
        shown = True
    return rng.uniform(-1.0, 1.0, size=4).astype(np.float32)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", default="127.0.0.1:50051")
    parser.add_argument("--episodes", type=int, default=2)
    parser.add_argument("--max-steps", type=int, default=100)
    args = parser.parse_args()

    # NO_ADAPTER: take the env's observation dict as-is instead of adapting it to a model spec.
    model = Model(predict, spec=rlmesh.NO_ADAPTER)
    result = model.run(args.address, episodes=args.episodes, max_episode_steps=args.max_steps)
    print(
        f"episodes={result.num_episodes} "
        f"mean_reward={result.mean_reward:.2f} steps={result.total_steps}"
    )


if __name__ == "__main__":
    main()
