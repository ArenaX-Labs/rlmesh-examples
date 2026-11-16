"""Optional :8878 ensure helpers and Serving-address resolution for RLmeshSim demos."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _SCRIPTS_DIR.parent

UNREAL_ADDR_VAR = "RLMESH_UNREAL_ADDR"


def ensure_unreal_demo(demo_id: str) -> None:
    """Load ``demo_id`` via this project's optional control server, then Play."""
    scripts = str(_SCRIPTS_DIR)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)

    from demo_client import DemoControlError, ensure_demo

    demo_id = demo_id.strip()
    print(f"Ensuring Unreal demo={demo_id} …")
    try:
        status = ensure_demo(demo_id)
    except DemoControlError as exc:
        raise RuntimeError(str(exc)) from exc
    print(
        f"Unreal ready: demo={status.get('demo_id')} env_id={status.get('env_id')}"
    )


def ensure_demo_arena() -> None:
    """Load Demo Arena via the local control server, then Play."""
    ensure_unreal_demo("demo_arena")


def _dotenv_candidates() -> list[Path]:
    """Likely ``integrations/unreal/.env`` locations (rlmesh checkout)."""
    out: list[Path] = []
    env_root = os.environ.get("RLMESH_ROOT", "").strip()
    if env_root:
        out.append(Path(env_root) / "integrations" / "unreal" / ".env")
    plugin = _PROJECT_ROOT / "Plugins" / "RLMesh"
    if plugin.exists():
        # Junction/copy of integrations/unreal/RLMesh → sibling .env
        out.append(plugin.resolve().parent / ".env")
    out.append(_PROJECT_ROOT / ".env")
    return out


def _load_dotenv_addr() -> str:
    """Read ``RLMESH_UNREAL_ADDR`` from a nearby ``.env`` if present."""
    for path in _dotenv_candidates():
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() != UNREAL_ADDR_VAR:
                continue
            return value.strip().strip('"').strip("'")
    return ""


def resolve_address(cli_address: str = "") -> str:
    """``--address``, else ``RLMESH_UNREAL_ADDR``, else value from a local ``.env``."""
    address = (cli_address or "").strip()
    if address:
        return address
    address = os.environ.get(UNREAL_ADDR_VAR, "").strip()
    if address:
        return address
    address = _load_dotenv_addr()
    if address:
        os.environ.setdefault(UNREAL_ADDR_VAR, address)
    return address
