"""Drive the served bring_ball env with a model that emits chunks of eight actions.

uv run run.py                      # the env served on 127.0.0.1:7447
"""

import argparse

import numpy as np
from rlmesh.numpy import Model

CHUNK = 8
STATE_DIM = 44
ACTION_DIM = 5


class ChunkPolicy(Model):
    """A stand-in for a VLA action head: one forward pass returns CHUNK actions."""

    native_chunk = CHUNK

    def load(self):
        rng = np.random.default_rng(0)
        self.weights = rng.standard_normal((STATE_DIM, CHUNK * ACTION_DIM)) * 0.1
        self.calls = 0

    def predict_chunk(self, observation):
        self.calls += 1
        chunk = np.tanh(observation["state"] @ self.weights)
        return chunk.reshape(CHUNK, ACTION_DIM).astype(np.float32)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", default="127.0.0.1:7447")
    parser.add_argument("--episodes", type=int, default=1)
    args = parser.parse_args()

    model = ChunkPolicy()
    result = model.run(args.address, episodes=args.episodes, execution_horizon=CHUNK)
    print(f"episodes={result.num_episodes} steps={result.total_steps} model_calls={model.calls}")


if __name__ == "__main__":
    main()
