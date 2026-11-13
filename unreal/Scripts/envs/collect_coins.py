"""Activate the Collect Coins environment on the procedural map."""

from __future__ import annotations

from . import registry, swap


def activate() -> None:
    meta = registry.ENVIRONMENTS["collect_coins"]
    swap.ensure_map(meta["map"])
    swap.remove_other_hosts(meta["host_class"])

    host = swap.ensure_host(meta["host_class"])
    host_class = swap.load_class(meta["host_class"])
    destroyed = swap.clear_procedural_leftovers(
        host=host,
        keep=(host,),
        host_class=host_class,
    )
    swap.apply_material(host, registry.MAT_AGENT)
    loc = host.get_actor_location()
    swap.log(
        f"collect_coins active: agent={swap.label_of(host)} "
        f"at ({loc.x:.0f},{loc.y:.0f},{loc.z:.0f}) cleared={destroyed} "
        f"(coins spawn at Play)"
    )
