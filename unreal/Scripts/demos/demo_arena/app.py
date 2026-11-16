#!/usr/bin/env python3
"""Drive Demo Arena with a tiny ``rlmesh.numpy.Model``.

Requires this project's demo control server and authored GameScene_Demo
(unless ``--no-ensure`` and Play yourself).

  python Scripts/demos/demo_arena/app.py --verbose --address "127.0.0.1:7447#<key>/env"
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
from policy import nearest_target_gap, parse_obs, reset_arena_policy_state, toward_goal_arena


class TowardGoalArena(rlmesh.numpy.Model):
    spec = rlmesh.NO_ADAPTER

    def __init__(self, *, verbose: bool = False) -> None:
        super().__init__()
        self._verbose = verbose

    def load(self) -> None:
        pass

    def predict(self, observation):
        action = toward_goal_arena(observation)
        if self._verbose:
            goal, coins, obstacles, walls = parse_obs(observation)
            _tgt, tdist = nearest_target_gap(goal, coins)
            coins_left = sum(1 for c in coins if float(np.linalg.norm(c)) > 1e-6)
            goal_left = 1 if float(np.linalg.norm(goal)) > 1e-6 else 0
            nearest_obs = min(
                (float(np.linalg.norm(o)) for o in obstacles),
                default=float("inf"),
            )
            nearest_wall = float(np.min(walls)) if walls.size else float("inf")
            print(
                f"  target={tdist:.1f} coins_left={coins_left} goal_left={goal_left} "
                f"obstacle={nearest_obs:.1f} wall={nearest_wall:.1f} "
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
        help="Skip demo control; connect to already-Serving Demo Arena",
    )
    args = parser.parse_args(argv)

    if not args.no_ensure:
        try:
            ensure_unreal_demo("demo_arena")
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

    reset_arena_policy_state()

    run_kwargs: dict = {"episodes": args.episodes}
    if args.seeds.strip():
        run_kwargs = {
            "seeds": [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
        }

    rlmesh.run(TowardGoalArena(verbose=args.verbose), address, **run_kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
