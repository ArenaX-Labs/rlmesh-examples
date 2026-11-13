"""In-editor environment swap helpers for this sample project.

Activate one registered env at a time (single EnvServer). Never saves the level.

  from envs import activate, list_environments
  activate("reach_target")
  activate("demo_arena")
"""

from __future__ import annotations

from typing import Any

from . import (
    avoid_hazards,
    chase_point,
    collect_coins,
    demo_arena,
    reach_target,
)
from .registry import ENVIRONMENTS, get_environment, list_environments

_ACTIVATORS = {
    "reach_target": reach_target.activate,
    "chase_point": chase_point.activate,
    "avoid_hazards": avoid_hazards.activate,
    "collect_coins": collect_coins.activate,
    "demo_arena": demo_arena.activate,
}


def activate(env_key: str) -> dict[str, Any]:
    """Swap the editor to ``env_key`` and return its catalog metadata."""
    key = env_key.strip()
    meta = get_environment(key)
    if meta is None:
        known = ", ".join(sorted(ENVIRONMENTS))
        raise KeyError(f"unknown environment {env_key!r}; known: {known}")
    activator = _ACTIVATORS.get(key)
    if activator is None:
        raise RuntimeError(f"environment {key!r} has no activator")
    activator()
    return meta


__all__ = [
    "ENVIRONMENTS",
    "activate",
    "get_environment",
    "list_environments",
]
