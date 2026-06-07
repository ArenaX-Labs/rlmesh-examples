import numpy as np

OBS_DIM = 17
ACTION_DIM = 6


def make_policy(seed=0, scale=0.3):
    rng = np.random.default_rng(seed)
    weights = rng.standard_normal((OBS_DIM, ACTION_DIM)).astype(np.float32) * scale

    def policy(obs):
        return np.tanh(np.asarray(obs, dtype=np.float32) @ weights).astype(np.float32)

    return policy
