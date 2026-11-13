"""Locate rlmesh Unreal demo helpers (gym_common / paths / dotenv)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _SCRIPTS_DIR.parent


def rlmesh_demo_common() -> Path:
    """Return ``integrations/unreal/demos/common`` from an rlmesh checkout."""
    env = os.environ.get("RLMESH_ROOT", "").strip()
    if env:
        common = Path(env) / "integrations" / "unreal" / "demos" / "common"
        if common.is_dir():
            return common

    plugin = _PROJECT_ROOT / "Plugins" / "RLMesh"
    if plugin.exists():
        # Junction/copy of integrations/unreal/RLMesh → sibling demos/common.
        common = plugin.resolve().parent / "demos" / "common"
        if common.is_dir():
            return common

    raise RuntimeError(
        "Cannot find rlmesh demos/common. Set RLMESH_ROOT to the rlmesh checkout, "
        "or junction Plugins/RLMesh from integrations/unreal/RLMesh."
    )


def ensure_rlmesh_on_path() -> Path:
    """Insert demos/common on sys.path; return that directory."""
    common = rlmesh_demo_common()
    if str(common) not in sys.path:
        sys.path.insert(0, str(common))
    scripts = str(_SCRIPTS_DIR)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    return common


def ensure_demo_arena() -> None:
    """Dev-only: load Demo Arena via local control server, then Play."""
    ensure_rlmesh_on_path()
    from demo_client import DemoControlError, ensure_demo

    print("Ensuring Unreal demo=demo_arena …")
    try:
        status = ensure_demo("demo_arena")
    except DemoControlError as exc:
        raise RuntimeError(str(exc)) from exc
    print(
        f"Unreal ready: demo={status.get('demo_id')} env_id={status.get('env_id')}"
    )
