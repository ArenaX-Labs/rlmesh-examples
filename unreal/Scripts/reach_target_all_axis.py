"""Reach Target All Axis: fly the cube straight at the target."""

import sys

import numpy as np
import rlmesh
from rlmesh.numpy import Model


class TowardTarget(Model):
    def predict(self, observation):
        offset = observation  # (x, y, z) from the cube to the target
        return (offset / max(np.linalg.norm(offset), 1e-6)).astype(np.float32)


if __name__ == "__main__":
    address = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:7447/env"
    print(rlmesh.run(TowardTarget(), address, episodes=3))
