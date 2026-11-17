"""Registered RLMesh environments and the maps / host actors they use."""

from __future__ import annotations

from typing import Any

# Shared procedural map for the compact gyms (one EnvServer host at a time).
DEFAULT_MAP = "/Game/GameScene"
ARENA_MAP = "/Game/GameScene_Demo"

AGENT_LABEL = "Agent"
TARGET_LABEL = "Target"
GOAL_LABEL = "Goal"
BP_GOAL = "/Game/BP_Goal"

MAT_AGENT = "/Game/Blue"
MAT_GOAL = "/Game/Gold"
CUBE_MESH = "/Engine/BasicShapes/Cube.Cube"
SPHERE_MESH = "/Engine/BasicShapes/Sphere.Sphere"

# C++ demo host actors (each owns one URLMesh*Component / EnvServer).
ENV_HOSTS: dict[str, str] = {
    "reach_target_all_axis": "/Script/RLmeshSim.RLMeshReachTargetAllAxisDemoActor",
    "chase_point": "/Script/RLmeshSim.RLMeshChasePointDemoActor",
    "avoid_hazards": "/Script/RLmeshSim.RLMeshAvoidHazardsDemoActor",
    "collect_coins": "/Script/RLmeshSim.RLMeshCollectCoinsDemoActor",
    "demo_arena": "/Script/RLmeshSim.RLMeshDemoArenaDemoActor",
}

# env_id → metadata used by the control API and activate().
ENVIRONMENTS: dict[str, dict[str, Any]] = {
    "reach_target_all_axis": {
        "title": "Reach Target All Axis",
        "env_id": "Unreal-ReachTargetAllAxis-v0",
        "map": DEFAULT_MAP,
        "host_class": ENV_HOSTS["reach_target_all_axis"],
        "description": "3D Box[3] reach toward a fixed/random target (XYZ).",
        "mode": "procedural",  # clear leftover props; ensure Agent + Target
    },
    "chase_point": {
        "title": "Chase Point",
        "env_id": "Unreal-ChasePoint-v0",
        "map": DEFAULT_MAP,
        "host_class": ENV_HOSTS["chase_point"],
        "description": "2D chase; goal wanders then freezes.",
        "mode": "procedural",
    },
    "avoid_hazards": {
        "title": "Avoid Hazards",
        "env_id": "Unreal-AvoidHazards-v0",
        "map": DEFAULT_MAP,
        "host_class": ENV_HOSTS["avoid_hazards"],
        "description": "2D reach with red hazard cubes; Box[2+2N] obs.",
        "mode": "procedural",
    },
    "collect_coins": {
        "title": "Collect Coins",
        "env_id": "Unreal-CollectCoins-v0",
        "map": DEFAULT_MAP,
        "host_class": ENV_HOSTS["collect_coins"],
        "description": "2D collect N gold spheres; Box[3] obs (nearest + coins_left).",
        "mode": "procedural",
    },
    "demo_arena": {
        "title": "Demo Arena",
        "env_id": "Unreal-DemoArena-v0",
        "map": ARENA_MAP,
        "host_class": ENV_HOSTS["demo_arena"],
        "description": "Level-driven arena: coins + goal, obstacles fail, walls block.",
        "mode": "authored",  # load map; bind labels; never destroy props
        "expected_coins": 3,
        "expected_obstacles": 1,
    },
}


def list_environments(*, implemented_only: bool = True) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for env_key, meta in ENVIRONMENTS.items():
        ready = bool(meta.get("host_class"))
        if implemented_only and not ready:
            continue
        out.append(
            {
                "id": env_key,
                "title": str(meta["title"]),
                "env_id": str(meta["env_id"]),
                "implemented": str(ready).lower(),
                "description": str(meta["description"]),
            }
        )
    return out


def get_environment(env_key: str) -> dict[str, Any] | None:
    key = env_key.strip()
    meta = ENVIRONMENTS.get(key)
    if not meta:
        return None
    return {"id": key, **meta}
