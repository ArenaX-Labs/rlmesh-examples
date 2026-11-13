#!/usr/bin/env python3
"""Gymnasium-facing client for RLmeshSim Demo Arena.

  python Scripts/demos/demo_arena/gym.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_DEMO_DIR = Path(__file__).resolve().parent
_DEMOS_DIR = _DEMO_DIR.parent
for _p in (_DEMOS_DIR, _DEMO_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from _rlmesh import ensure_demo_arena, ensure_rlmesh_on_path

ensure_rlmesh_on_path()

from gym_common import make_remote_env, smoke_remote_env


def make_env(address: str | None = None, *, ensure: bool = True, **remote_kwargs):
    if ensure:
        ensure_demo_arena()
    return make_remote_env(address, **remote_kwargs)


def main(argv: list[str] | None = None) -> int:
    del argv
    try:
        ensure_demo_arena()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return smoke_remote_env()


if __name__ == "__main__":
    raise SystemExit(main())
