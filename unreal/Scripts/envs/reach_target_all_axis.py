"""Activate the Reach Target All Axis environment on the procedural map."""

from __future__ import annotations

import unreal

from . import registry, swap

MIN_DIST = 800.0


def activate() -> None:
    meta = registry.ENVIRONMENTS["reach_target_all_axis"]
    swap.ensure_map(meta["map"])
    swap.remove_other_hosts(meta["host_class"])

    host = swap.ensure_host(meta["host_class"])
    agent_loc = host.get_actor_location()
    host_class = swap.load_class(meta["host_class"])

    actors = swap.all_actors()
    agent_props = [
        a
        for a in actors
        if "agent" in swap.label_of(a).lower()
        and not swap.is_class(a, host_class)
        and a != host
    ]
    target_candidates = [
        a
        for a in actors
        if "target" in swap.label_of(a).lower()
        and not swap.is_class(a, host_class)
        and a not in agent_props
        and a != host
    ]

    if target_candidates:
        target = target_candidates[0]
        raw = target.get_actor_location()
        target_loc = swap.separate_3d(agent_loc, raw, MIN_DIST)
        if not isinstance(target, unreal.StaticMeshActor):
            old = target
            target = swap.spawn_static_mesh(
                registry.TARGET_LABEL,
                target_loc,
                unreal.Vector(1.0, 1.0, 1.0),
                registry.CUBE_MESH,
            )
            swap.log(f"replaced non-mesh Target {old.get_name()}")
            old.destroy_actor()
        else:
            target.set_actor_label(registry.TARGET_LABEL)
            target.set_actor_location(target_loc, False, False)
            try:
                target.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
            except Exception:
                pass
    else:
        target_loc = unreal.Vector(
            float(agent_loc.x) + MIN_DIST,
            float(agent_loc.y) + MIN_DIST * 0.5,
            float(agent_loc.z),
        )
        target = swap.spawn_static_mesh(
            registry.TARGET_LABEL,
            target_loc,
            unreal.Vector(1.0, 1.0, 1.0),
            registry.CUBE_MESH,
        )

    host.set_editor_property("target_actor", target)
    destroyed = swap.clear_procedural_leftovers(
        host=host,
        keep=(host, target),
        host_class=host_class,
        named_keys=("agent", "target", "box", "cube", "rlmesh"),
    )
    swap.apply_material(host, registry.MAT_AGENT)
    swap.apply_material(target, registry.MAT_GOAL)
    swap.log(
        f"reach_target_all_axis active: agent={swap.label_of(host)} "
        f"target={swap.label_of(target)} cleared={destroyed}"
    )
