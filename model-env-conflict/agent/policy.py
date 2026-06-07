from pathlib import Path

import numpy as np
from stable_baselines3 import SAC

MODERN_CHECKPOINT = (
    Path(__file__).resolve().parent / "models" / "sac-halfcheetah-v5-modern.zip"
)


def make_policy():
    if not MODERN_CHECKPOINT.exists():
        raise FileNotFoundError(
            f"{MODERN_CHECKPOINT} not found — run `uv run train.py` first"
        )
    model = SAC.load(MODERN_CHECKPOINT, device="cpu")

    def policy(observation):
        action, _ = model.predict(
            np.asarray(observation, dtype=np.float32), deterministic=True
        )
        return np.asarray(action, dtype=np.float32)

    return policy, MODERN_CHECKPOINT.name
