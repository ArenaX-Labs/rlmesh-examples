"""Activate the authored Demo Arena environment (non-destructive)."""

from __future__ import annotations

from . import registry, swap


def activate() -> None:
    meta = registry.ENVIRONMENTS["demo_arena"]
    swap.ensure_map(meta["map"])
    removed = swap.remove_other_hosts(meta["host_class"])

    host = swap.ensure_host(meta["host_class"])
    actors = swap.all_actors()

    goals = [
        a
        for a in actors
        if swap.label_of(a).lower().startswith("goal") and swap.is_valid(a)
    ]
    coins = [
        a
        for a in actors
        if swap.label_of(a).lower().startswith("coin") and swap.is_valid(a)
    ]
    obstacles = [
        a
        for a in actors
        if (
            swap.label_of(a).lower().startswith("obstacle")
            or swap.label_of(a).lower().startswith("hazard")
        )
        and swap.is_valid(a)
    ]

    if goals:
        try:
            host.set_editor_property("goal_actor", goals[0])
            swap.log(f"demo_arena GoalActor -> {swap.label_of(goals[0])}")
        except Exception as exc:  # noqa: BLE001
            swap.log_warning(f"demo_arena could not set goal_actor: {exc}")
    else:
        swap.log_error("demo_arena: no actor labeled Goal*")

    expect_c = int(meta.get("expected_coins", 0))
    expect_o = int(meta.get("expected_obstacles", 0))
    if len(coins) < expect_c:
        swap.log_warning(
            f"demo_arena: found {len(coins)} Coin* actor(s), expected {expect_c}"
        )
    if len(obstacles) < expect_o:
        swap.log_warning(
            f"demo_arena: found {len(obstacles)} Obstacle*/Hazard* actor(s), "
            f"expected {expect_o}"
        )

    swap.log(
        f"demo_arena active: agent={swap.label_of(host)} "
        f"coins={len(coins)} obstacles={len(obstacles)} "
        f"removed_hosts={removed} (props untouched; level not saved)"
    )
