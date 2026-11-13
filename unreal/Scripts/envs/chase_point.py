"""Activate the Chase Point environment on the procedural map."""

from __future__ import annotations

import unreal

from . import registry, swap

MIN_DIST = 800.0


def activate() -> None:
    meta = registry.ENVIRONMENTS["chase_point"]
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
    goal_candidates = [
        a
        for a in actors
        if any(k in swap.label_of(a).lower() for k in ("goal", "target"))
        and not swap.is_class(a, host_class)
        and a not in agent_props
        and a != host
    ]

    if goal_candidates:
        goal = goal_candidates[0]
        raw = goal.get_actor_location()
        goal_loc = swap.separate_xy(agent_loc, raw, MIN_DIST)
        if not swap.is_bp_instance(goal, registry.BP_GOAL):
            old = goal
            goal = swap.spawn_goal(goal_loc)
            swap.log(f"replaced Goal {old.get_name()} with {registry.BP_GOAL}")
            old.destroy_actor()
        else:
            goal.set_actor_label(registry.GOAL_LABEL)
            goal.set_actor_location(goal_loc, False, False)
    else:
        goal_loc = unreal.Vector(
            float(agent_loc.x) + MIN_DIST,
            float(agent_loc.y) + MIN_DIST * 0.5,
            float(agent_loc.z),
        )
        goal = swap.spawn_goal(goal_loc)

    host.set_editor_property("goal_actor", goal)
    destroyed = swap.clear_procedural_leftovers(
        host=host,
        keep=(host, goal),
        host_class=host_class,
    )
    swap.apply_material(host, registry.MAT_AGENT)
    swap.apply_material(goal, registry.MAT_GOAL)
    swap.log(
        f"chase_point active: agent={swap.label_of(host)} goal={swap.label_of(goal)} "
        f"cleared={destroyed}"
    )
