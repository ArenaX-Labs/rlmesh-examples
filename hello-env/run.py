"""Drive the served env with a hand-written policy.

    uv run run.py                      # against 127.0.0.1:50051
    uv run run.py --address HOST:PORT --episodes 10
"""

import argparse

from rlmesh.numpy import Model


def predict(obs):
    pos, target = obs
    return 1 if target > pos else 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", default="127.0.0.1:50051")
    parser.add_argument("--episodes", type=int, default=5)
    args = parser.parse_args()

    result = Model(predict).run(args.address, episodes=args.episodes)
    print(
        f"episodes={result.num_episodes} "
        f"mean_reward={result.mean_reward:.2f} steps={result.total_steps}"
    )


if __name__ == "__main__":
    main()
