#!/usr/bin/env python3
"""Drive Chase Point with a tiny ``rlmesh.numpy.Model``.

  # From RLmeshSim root (venv with rlmesh installed):
  python Scripts/demos/chase_point/app.py --verbose --address "127.0.0.1:7447#<key>/env"
  python Scripts/demos/chase_point/app.py --no-ensure --address "…"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import rlmesh

_DEMO_DIR = Path(__file__).resolve().parent
_DEMOS_DIR = _DEMO_DIR.parent
for _p in (_DEMOS_DIR, _DEMO_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from _rlmesh import ensure_unreal_demo, resolve_address
from policy import gap_xy, toward_goal

DEMO_ID = "chase_point"


class TowardGoal(rlmesh.numpy.Model):
    spec = rlmesh.NO_ADAPTER

    def __init__(self, *, verbose: bool = False) -> None:
        super().__init__()
        self._verbose = verbose

    def load(self) -> None:
        pass

    def predict(self, observation):
        action = toward_goal(observation)
        if self._verbose:
            gap = gap_xy(observation)
            dist = float(np.linalg.norm(gap))
            print(
                f"  gap=({gap[0]:+.1f}, {gap[1]:+.1f}) dist={dist:.1f} "
                f"-> dir=({action[0]:+.2f}, {action[1]:+.2f})"
            )
        return action


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--address",
        default="",
        help="Serving address (else RLMESH_UNREAL_ADDR or integrations/unreal/.env)",
    )
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument(
        "--seeds",
        default="",
        help="Comma-separated episode seeds (overrides --episodes)",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--no-ensure",
        action="store_true",
        help="Skip control server; connect to already-Serving Chase Point",
    )
    args = parser.parse_args(argv)

    if not args.no_ensure:
        try:
            ensure_unreal_demo(DEMO_ID)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    address = resolve_address(args.address)
    if not address:
        print(
            "Set RLMESH_UNREAL_ADDR or integrations/unreal/.env, or pass\n"
            '  --address "127.0.0.1:7447#<key>/env"',
            file=sys.stderr,
        )
        return 2

    run_kwargs: dict = {"episodes": args.episodes}
    if args.seeds.strip():
        run_kwargs = {
            "seeds": [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
        }

    rlmesh.run(TowardGoal(verbose=args.verbose), address, **run_kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
