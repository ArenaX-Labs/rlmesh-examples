"""Evaluate one SAC checkpoint on its training stack and on a Safety-Gymnasium env it cannot share.

uv run eval.py                                                # safety env on 127.0.0.1:7447
uv run eval.py --image rlmesh-examples/stack-conflict-safety  # the env image, as a sandbox
"""

import argparse
from pathlib import Path

import gymnasium as gym
import numpy as np
from rlmesh.numpy import RemoteEnv, SandboxEnv
from stable_baselines3 import SAC

CHECKPOINT = Path(__file__).parent / "models" / "sac-halfcheetah-v5-modern.zip"


def rollout(env, model, *, seed, max_steps):
    obs, _ = env.reset(seed=seed)
    total = cost = 0.0
    for step in range(1, max_steps + 1):
        action, _ = model.predict(np.asarray(obs, dtype=np.float32), deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action.astype(np.float32))
        total += float(reward)
        cost += float(info.get("cost", 0.0))
        if terminated or truncated:
            break
    return f"steps={step:4d} return={total:8.1f} cost={cost:6.1f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", default="127.0.0.1:7447")
    parser.add_argument("--image", help="start this env image as a sandbox instead")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=100)
    args = parser.parse_args()

    model = SAC.load(CHECKPOINT, device="cpu")
    run = {"seed": args.seed, "max_steps": args.max_steps}
    with gym.make("HalfCheetah-v5") as env:
        print(f"modern-halfcheetah-v5        {rollout(env, model, **run)}")
    remote = SandboxEnv(f"image://{args.image}") if args.image else RemoteEnv(args.address)
    with remote as env:
        print(f"safety-halfcheetah-velocity  {rollout(env, model, **run)}")


if __name__ == "__main__":
    main()
