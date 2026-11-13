"""Shared primitives for swapping the active RLMesh environment in-editor.

All activate paths:
  1. End with a single env host actor (one EnvServer).
  2. Never save the level or assets.
"""

from __future__ import annotations

import math
import re
from typing import Iterable

import unreal

from . import registry

_PROTECTED_CLASS_SUBSTR = (
    "playerstart",
    "camera",
    "light",
    "sky",
    "fog",
    "landscape",
    "pawn",
    "character",
    "gamemode",
    "gamestate",
    "playercontroller",
    "worldsettings",
    "physicsvolume",
    "abstractnavdata",
    "particle",
    "emitter",
)


def log(msg: str) -> None:
    unreal.log(f"envs: {msg}")


def log_warning(msg: str) -> None:
    unreal.log_warning(f"envs: {msg}")


def log_error(msg: str) -> None:
    unreal.log_error(f"envs: {msg}")


def label_of(actor) -> str:
    try:
        return str(actor.get_actor_label())
    except Exception:
        return actor.get_name()


def is_valid(actor) -> bool:
    try:
        return bool(unreal.SystemLibrary.is_valid(actor))
    except Exception:
        return actor is not None


def is_class(actor, uclass) -> bool:
    cls = actor.get_class()
    return cls == uclass or unreal.MathLibrary.class_is_child_of(cls, uclass)


def editor_world():
    return unreal.EditorLevelLibrary.get_editor_world()


def all_actors(world=None):
    world = world or editor_world()
    return list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor))


def load_class(path: str):
    return unreal.load_class(None, path)


def _map_leaf(path_or_world: str) -> str:
    """Normalize a content/world path to its map asset name (no PIE prefix)."""
    leaf = path_or_world.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    leaf = leaf.split(".", 1)[0]
    return re.sub(r"^UEDPIE_\d+_", "", leaf)


def ensure_map(map_path: str, *, map_name: str | None = None) -> None:
    """Load ``map_path`` if the editor world is not already that map. Never saves."""
    world = editor_world()
    current = ""
    try:
        if world is not None:
            current = str(world.get_path_name())
    except Exception:
        pass

    want = map_name or map_path.rsplit("/", 1)[-1]
    if current and _map_leaf(current) == _map_leaf(want):
        log(f"map already loaded ({current})")
        return

    log(f"loading map {map_path}")
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    try:
        if les is not None and hasattr(les, "load_level"):
            les.load_level(map_path)
        else:
            unreal.EditorLevelLibrary.load_level(map_path)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"failed to load map {map_path}: {exc}") from exc


def remove_other_hosts(keep_class_path: str) -> int:
    """Destroy every registered env host except the one for ``keep_class_path``."""
    world = editor_world()
    removed = 0
    for path in registry.ENV_HOSTS.values():
        if path == keep_class_path:
            continue
        other = load_class(path)
        if other is None:
            continue
        for actor in list(unreal.GameplayStatics.get_all_actors_of_class(world, other)):
            log(f"removing inactive env host {label_of(actor)}")
            actor.destroy_actor()
            removed += 1
    return removed


def ensure_host(
    host_class_path: str,
    *,
    label: str = registry.AGENT_LABEL,
    default_location: unreal.Vector | None = None,
):
    """Return a single host actor of ``host_class_path`` (spawn if needed)."""
    world = editor_world()
    host_class = load_class(host_class_path)
    if host_class is None:
        raise RuntimeError(
            f"env host class missing: {host_class_path} (compile the game module)"
        )

    actors = all_actors(world)
    existing = [a for a in actors if is_class(a, host_class) and is_valid(a)]
    if existing:
        host = existing[0]
        for extra in existing[1:]:
            log(f"removing duplicate host {label_of(extra)}")
            extra.destroy_actor()
        loc = host.get_actor_location()
    else:
        agent_props = [
            a
            for a in actors
            if "agent" in label_of(a).lower()
            and is_valid(a)
            and not is_class(a, host_class)
        ]
        if agent_props:
            loc = agent_props[0].get_actor_location()
        elif default_location is not None:
            loc = default_location
        else:
            loc = unreal.Vector(0.0, 0.0, 100.0)
        host = unreal.EditorLevelLibrary.spawn_actor_from_class(
            host_class, loc, unreal.Rotator(0.0, 0.0, 0.0)
        )
        if host is None:
            raise RuntimeError(f"failed to spawn env host {host_class_path}")
        log(f"spawned host {host_class_path} at {loc}")

    host.set_actor_label(label)
    host.set_actor_location(host.get_actor_location(), False, False)
    return host


def apply_material(actor, material_path: str) -> None:
    mat = unreal.EditorAssetLibrary.load_asset(material_path)
    if mat is None or not is_valid(actor):
        log_warning(f"material {material_path} not applied to {label_of(actor)}")
        return
    try:
        if isinstance(actor, unreal.StaticMeshActor):
            actor.static_mesh_component.set_material(0, mat)
            return
        mesh = actor.get_component_by_class(unreal.StaticMeshComponent)
        if mesh is not None:
            mesh.set_material(0, mat)
    except Exception as exc:  # noqa: BLE001
        log_warning(f"set_material failed on {label_of(actor)}: {exc}")


def spawn_static_mesh(
    label: str,
    location: unreal.Vector,
    scale: unreal.Vector,
    mesh_path: str,
):
    spawned = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor, location, unreal.Rotator(0.0, 0.0, 0.0)
    )
    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
    spawned.static_mesh_component.set_static_mesh(mesh)
    spawned.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    spawned.static_mesh_component.set_world_scale3d(scale)
    spawned.set_actor_label(label)
    spawned.set_actor_location(location, False, False)
    return spawned


def load_bp_class(asset_path: str):
    if not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        return None
    return unreal.EditorAssetLibrary.load_blueprint_class(asset_path)


def is_bp_instance(actor, asset_path: str) -> bool:
    bp_class = load_bp_class(asset_path)
    if bp_class is None or actor is None:
        return False
    cls = actor.get_class()
    return cls == bp_class or unreal.MathLibrary.class_is_child_of(cls, bp_class)


def spawn_goal(location: unreal.Vector):
    bp_class = load_bp_class(registry.BP_GOAL)
    if bp_class is not None:
        spawned = unreal.EditorLevelLibrary.spawn_actor_from_class(
            bp_class, location, unreal.Rotator(0.0, 0.0, 0.0)
        )
        if spawned is not None:
            spawned.set_actor_label(registry.GOAL_LABEL)
            spawned.set_actor_location(location, False, False)
            return spawned
    return spawn_static_mesh(
        registry.GOAL_LABEL,
        location,
        unreal.Vector(0.6, 0.6, 0.6),
        registry.SPHERE_MESH,
    )


def separate_3d(agent_loc: unreal.Vector, loc: unreal.Vector, min_dist: float) -> unreal.Vector:
    dx = float(loc.x) - float(agent_loc.x)
    dy = float(loc.y) - float(agent_loc.y)
    dz = float(loc.z) - float(agent_loc.z)
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    if dist >= min_dist:
        return loc
    if dist < 1.0:
        return unreal.Vector(
            float(agent_loc.x) + min_dist,
            float(agent_loc.y) + min_dist * 0.5,
            float(agent_loc.z),
        )
    scale = min_dist / dist
    return unreal.Vector(
        float(agent_loc.x) + dx * scale,
        float(agent_loc.y) + dy * scale,
        float(agent_loc.z) + dz * scale,
    )


def separate_xy(agent_loc: unreal.Vector, loc: unreal.Vector, min_dist: float) -> unreal.Vector:
    dx = float(loc.x) - float(agent_loc.x)
    dy = float(loc.y) - float(agent_loc.y)
    dist = math.sqrt(dx * dx + dy * dy)
    if dist >= min_dist:
        return unreal.Vector(float(loc.x), float(loc.y), float(agent_loc.z))
    if dist < 1.0:
        return unreal.Vector(
            float(agent_loc.x) + min_dist,
            float(agent_loc.y) + min_dist * 0.5,
            float(agent_loc.z),
        )
    scale = min_dist / dist
    return unreal.Vector(
        float(agent_loc.x) + dx * scale,
        float(agent_loc.y) + dy * scale,
        float(agent_loc.z),
    )


def _is_protected_class(actor) -> bool:
    cls_name = actor.get_class().get_name().lower()
    return any(s in cls_name for s in _PROTECTED_CLASS_SUBSTR)


def clear_procedural_leftovers(
    *,
    host,
    keep: Iterable,
    host_class,
    named_keys: tuple[str, ...] = (
        "agent",
        "target",
        "goal",
        "box",
        "cube",
        "sphere",
        "rlmesh",
        "coin",
        "hazard",
    ),
) -> int:
    """Remove leftover demo props on the procedural map. Keeps floors / systems."""
    keep_set = {a for a in keep if a is not None}
    destroyed = 0
    for actor in all_actors():
        if actor in keep_set or not is_valid(actor):
            continue
        if _is_protected_class(actor):
            continue

        cls_name = actor.get_class().get_name().lower()
        label = label_of(actor).lower()
        is_extra_host = is_class(actor, host_class)
        is_sma = isinstance(actor, unreal.StaticMeshActor)
        is_brush = "brush" in cls_name
        is_named = any(k in label for k in named_keys)

        if is_sma and not is_named and not is_extra_host:
            try:
                scale = actor.static_mesh_component.get_world_scale3d()
                if max(abs(scale.x), abs(scale.y)) >= 5.0:
                    continue
            except Exception:
                pass

        drop = False
        if is_extra_host or is_named or is_brush:
            drop = True
        elif is_sma and not is_named:
            try:
                scale = actor.static_mesh_component.get_world_scale3d()
                if max(abs(scale.x), abs(scale.y), abs(scale.z)) <= 2.0:
                    drop = True
            except Exception:
                pass

        if drop:
            log(f"clearing leftover {label_of(actor)} ({actor.get_class().get_name()})")
            actor.destroy_actor()
            destroyed += 1

    for extra in unreal.GameplayStatics.get_all_actors_of_class(editor_world(), host_class):
        if extra != host:
            log(f"removing duplicate host {extra.get_name()}")
            extra.destroy_actor()
            destroyed += 1
    return destroyed
