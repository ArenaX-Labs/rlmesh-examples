import json


def report(results, *, source=None, path="results.json"):
    print("\n=== one pretrained SAC policy, two stacks it cannot share a venv with ===")
    if source:
        print(f"policy: {source}")
    for name, r in results.items():
        print(
            f"{name:28s} steps={r['steps']:4d} "
            f"return={r['return']:9.1f} cost={r['cost']:6.1f}"
        )

    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nwrote {path}")
