"""Collect Coins: always head for the nearest coin left."""

import sys

import numpy as np
import rlmesh
from rlmesh.numpy import Model


class NearestCoin(Model):
    def predict(self, observation):
        offset = observation["nearest_coin"]
        return (offset / max(np.linalg.norm(offset), 1e-6)).astype(np.float32)


if __name__ == "__main__":
    address = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:7447/env"
    print(rlmesh.run(NearestCoin(), address, episodes=3))
