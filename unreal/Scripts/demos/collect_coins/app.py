#!/usr/bin/env python3
"""Drive Collect Coins with a tiny ``rlmesh.numpy.Model``.

  python Scripts/demos/collect_coins/app.py --verbose --address "127.0.0.1:7447#<key>/env"
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
from policy import parse_obs, toward_nearest_coin

DEMO_ID = "collect_coins"


class TowardNearestCoin(rlmesh.numpy.Model):
    spec = rlmesh.NO_ADAPTER

    def __init__(self, *, verbose: bool = False) -> None:
        super().__init__()
        self._verbose = verbose

    def load(self) -> None:
        pass

    def predict(self, observation):
        action = toward_nearest_coin(observation)
        if self._verbose:
            gap, coins_left = parse_obs(observation)
            dist = float(np.linalg.norm(gap))
            print(
                f"  nearest={dist:.1f} coins_left_norm={coins_left:.2f} "
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
    parser.add_argument("--seeds", default="")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--no-ensure",
        action="store_true",
        help="Skip control server; connect to already-Serving Collect Coins",
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

    rlmesh.run(TowardNearestCoin(verbose=args.verbose), address, **run_kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
