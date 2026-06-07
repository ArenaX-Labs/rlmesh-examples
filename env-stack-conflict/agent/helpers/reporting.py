import json


def report(results, path="results.json"):
    print("\n=== one policy, two simulator stacks ===")
    for name, r in results.items():
        print(
            f"{name:18s} obs={r['obs_shape']} steps={r['steps']} "
            f"return={r['return']:.1f} cost={r['cost']:.1f}"
        )

    scores = {
        name: {"return": r["return"], "cost": r["cost"], "steps": r["steps"]}
        for name, r in results.items()
    }
    with open(path, "w") as f:
        json.dump(scores, f, indent=2)
    print(f"\nwrote {path}")
