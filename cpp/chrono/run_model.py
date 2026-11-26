"""Drive the native C++ Project Chrono env from a Python model.

The env (``chrono_reach_env``) is Chrono's 6-DOF industrial robot served
through the RLMesh C ABI. This model never sees the env's own layout: it
declares the inputs it wants once (``MODEL_SPEC``), and RLMesh resolves an
adapter against the tags the C++ env published -- resizing the camera, packing
the proprio vector, and mapping its action back onto the env's.

    uv run run_model.py 127.0.0.1:7447
    uv run run_model.py 127.0.0.1:7447 --policy random
    uv run run_model.py 127.0.0.1:7447 --view http:9000
    uv run run_model.py --image chrono-reach:dev
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from typing import Any

import numpy as np
import rlmesh
import rlmesh.adapters as adapt
from rlmesh.numpy import Model, RemoteEnv, SandboxEnv

# The checkpoint's input format: a 224x224 camera, one proprio vector, the goal
# and the instruction under its own keys, and a normalized 3-D tool delta out.
MODEL_SPEC = adapt.ModelSpec(
    input={
        "image": adapt.Image(adapt.IMAGE_PRIMARY, size=224),
        "proprio": adapt.Concat(adapt.EEF_POS, adapt.JOINT_POS),
        "goal": adapt.Concat("x/target_pos"),
        "task": adapt.Text(adapt.INSTRUCTION),
    },
    output=adapt.Action(adapt.Actuator(adapt.ACTION_DELTA_POS, dim=3)),
)

# The gap (metres) at which the scripted policy's action saturates.
STEP_METRES = 0.03


def make_policy(kind: str, seed: int, pace: float) -> Callable[[dict[str, Any]], np.ndarray]:
    rng = np.random.default_rng(seed)

    def predict(payload: dict[str, Any]) -> np.ndarray:
        assert payload["image"].shape == (224, 224, 3)
        if pace:
            time.sleep(pace)  # slow the loop down enough to watch
        if kind == "random":
            return rng.uniform(-1.0, 1.0, size=3).astype(np.float32)
        # Scripted: head straight for the goal (the proprio vector starts with
        # the tool position), easing off as the gap closes.
        eef = np.asarray(payload["proprio"][:3], dtype=np.float32)
        goal = np.asarray(payload["goal"], dtype=np.float32)
        return np.clip((goal - eef) / STEP_METRES, -1.0, 1.0).astype(np.float32)

    return predict


class KeepResult(rlmesh.RunHooks):
    result = rlmesh.RunResult()

    def on_run_end(self, result: rlmesh.RunResult) -> None:
        self.result = result


def run(model: Model, target: Any, seeds: list[int], view: str | None) -> rlmesh.RunResult:
    if not view:
        return model.run(target, seeds=seeds)
    # The viewer watches a binding: step each episode by hand.
    kept = KeepResult()
    with model.bind(target, view=view, hooks=kept) as binding:
        for seed in seeds:
            binding.reset(seed=seed)
            while not binding.done:
                binding.step()
        if sys.stdin.isatty():
            input("\nrun finished; press Enter to close the viewer ")
    return kept.result


def describe(contract: Any, where: str) -> None:
    print(f"connected to {contract.id} at {where}")
    print(f"  {contract.metadata.get('simulator')} / {contract.metadata.get('robot')}")
    print("\nresolved adapter (env tags x model spec):")
    print(adapt.resolve_from_contract(contract, MODEL_SPEC).explain())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("address", nargs="?", default="127.0.0.1:7447")
    parser.add_argument("--image", help="start this env image as a sandbox instead")
    parser.add_argument("--episodes", type=int, default=4)
    parser.add_argument("--policy", choices=["scripted", "random"], default="scripted")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--view",
        default=None,
        help='live viewer: "terminal" or "http:9000" (open http://localhost:9000)',
    )
    parser.add_argument(
        "--pace",
        type=float,
        default=None,
        help="seconds to pause per step (default: 0.08 with --view, else 0)",
    )
    args = parser.parse_args()

    pace = args.pace if args.pace is not None else (0.08 if args.view else 0.0)
    model = Model(make_policy(args.policy, args.seed, pace), spec=MODEL_SPEC)
    seeds = [args.seed + i for i in range(args.episodes)]
    if args.image:
        with SandboxEnv(f"image://{args.image}") as env:
            describe(env.env_contract, args.image)
            print(f"\nrunning {args.episodes} episodes, {args.policy} policy ...")
            result = run(model, env, seeds, args.view)
    else:
        # An open RemoteEnv holds the env: close it before the model runs.
        with RemoteEnv(args.address) as env:
            describe(env.env_contract, args.address)
        print(f"\nrunning {args.episodes} episodes, {args.policy} policy ...")
        result = run(model, args.address, seeds, args.view)

    for episode in result.episodes:
        print(
            f"  episode {episode.index}: seed={episode.seed} steps={episode.steps} "
            f"reward={episode.reward:.2f} success={episode.success}"
        )
    print(
        f"\nepisodes={result.num_episodes} steps={result.total_steps} "
        f"mean_reward={result.mean_reward:.2f} success_rate={result.success_rate}"
    )


if __name__ == "__main__":
    main()
