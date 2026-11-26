"""Drive the served env with a hand-written policy.

uv run run.py                                     # the env served on 127.0.0.1:7447
uv run run.py --image rlmesh-examples/hello-env   # the env image, run as a sandbox
"""

import argparse

from rlmesh.numpy import Model, SandboxEnv


def predict(obs):
    pos, target = obs
    return 1 if target > pos else 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", default="127.0.0.1:7447")
    parser.add_argument("--image", help="start this env image as a sandbox instead")
    parser.add_argument("--episodes", type=int, default=5)
    args = parser.parse_args()

    model = Model(predict)
    if args.image:
        with SandboxEnv(f"image://{args.image}") as env:
            result = model.run(env, episodes=args.episodes)
    else:
        result = model.run(args.address, episodes=args.episodes)
    print(
        f"episodes={result.num_episodes} "
        f"mean_reward={result.mean_reward:.2f} steps={result.total_steps}"
    )


if __name__ == "__main__":
    main()
