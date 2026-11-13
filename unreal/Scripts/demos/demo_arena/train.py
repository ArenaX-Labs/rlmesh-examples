#!/usr/bin/env python3
"""Train SB3 PPO on live RLmeshSim Demo Arena.

  pip install -r <rlmesh>/integrations/unreal/demos/common/requirements-gym-suite.txt
  python Scripts/demos/demo_arena/train.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_DEMO_DIR = Path(__file__).resolve().parent
_DEMOS_DIR = _DEMO_DIR.parent
for _p in (_DEMOS_DIR, _DEMO_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from _rlmesh import ensure_demo_arena, ensure_rlmesh_on_path

ensure_rlmesh_on_path()

from gym_common import (
    DEFAULT_TRAIN_TIMESTEPS,
    default_model_path,
    load_suite_dotenv,
    resolve_address,
    train_ppo,
)

ARTIFACTS_DIR = _DEMO_DIR / "artifacts"


def main(argv: list[str] | None = None) -> int:
    load_suite_dotenv()
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--address", default="")
    parser.add_argument("--timesteps", type=int, default=DEFAULT_TRAIN_TIMESTEPS)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--no-ensure", action="store_true")
    args = parser.parse_args(argv)

    if not args.no_ensure:
        try:
            ensure_demo_arena()
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    try:
        path = train_ppo(
            address=resolve_address(args.address) or None,
            total_timesteps=args.timesteps,
            model_path=args.out or default_model_path(ARTIFACTS_DIR),
            artifacts_dir=ARTIFACTS_DIR,
            seed=args.seed,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: train failed: {exc}", file=sys.stderr)
        return 1
    print(f"demo_arena train finished successfully ({path}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
