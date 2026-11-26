"""Run the model image against the env image, both as RLMesh sandboxes.

docker build -t my-env:latest env
docker build -t my-model:latest model
uv run run.py
"""

import argparse

import rlmesh


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-image", default="my-env:latest")
    parser.add_argument("--model-image", default="my-model:latest")
    parser.add_argument("--episodes", type=int, default=2)
    args = parser.parse_args()

    with (
        rlmesh.SandboxEnv(f"image://{args.env_image}") as env,
        rlmesh.SandboxModel(f"image://{args.model_image}") as model,
    ):
        result = model.run(env, episodes=args.episodes)
    print(f"episodes={result.num_episodes} steps={result.total_steps}")


if __name__ == "__main__":
    main()
