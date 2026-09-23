import sys
from pathlib import Path

import gymnasium
import numpy
import stable_baselines3
from stable_baselines3 import SAC

MODERN_CHECKPOINT = (
    Path(__file__).resolve().parent.parent
    / "agent"
    / "models"
    / "sac-halfcheetah-v5-modern.zip"
)


def print_stack():
    print(f"python            {sys.version.split()[0]}")
    print(f"numpy             {numpy.__version__}")
    print(f"gymnasium         {gymnasium.__version__}")
    print(f"stable-baselines3 {stable_baselines3.__version__}")


def main():
    print_stack()
    if not MODERN_CHECKPOINT.exists():
        print(f"missing checkpoint: {MODERN_CHECKPOINT}")
        return 3
    try:
        SAC.load(MODERN_CHECKPOINT, device="cpu")
    except ModuleNotFoundError as exc:
        if exc.name != "numpy._core":
            raise
        print(f"could not load modern checkpoint: {type(exc).__name__}: {exc}")
        return 0
    print("modern checkpoint loaded under the old stack — Wall 2 no longer holds")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
