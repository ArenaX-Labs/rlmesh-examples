"""Avoid Hazards: head for the goal, pushed away from hazards that come close."""

import sys

import numpy as np
import rlmesh
from rlmesh.numpy import Model

AVOID_RADIUS = 220.0


def unit(vector):
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 1e-6 else np.zeros_like(vector)


class AvoidHazards(Model):
    def predict(self, observation):
        push = np.zeros(2)
        for hazard in observation["hazards"]:  # (x, y) from the cube to each hazard
            distance = np.linalg.norm(hazard)
            if 1e-6 < distance < AVOID_RADIUS:
                push -= unit(hazard) * (AVOID_RADIUS - distance) / AVOID_RADIUS
        return unit(unit(observation["goal"]) + 1.25 * unit(push)).astype(np.float32)


if __name__ == "__main__":
    address = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:7447/env"
    print(rlmesh.run(AvoidHazards(), address, episodes=3))
