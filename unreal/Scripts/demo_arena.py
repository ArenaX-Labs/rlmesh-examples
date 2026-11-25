"""Demo Arena: collect every coin, then the goal, sliding along walls in the way."""

import math
import sys

import numpy as np
import rlmesh
from rlmesh.numpy import Model

CLEAR = 100.0  # wall clearance that counts as open; more than one step
AVOID_RADIUS = 160.0


def unit(vector):
    norm = np.linalg.norm(vector)
    return np.asarray(vector, dtype=np.float64) / norm if norm > 1e-6 else np.zeros(2)


def clearance(direction, walls):
    """Wall distance along ``direction``, interpolated between the two nearest rays."""
    turn = math.atan2(direction[1], direction[0]) % (2 * math.pi)
    slot = turn / (2 * math.pi) * len(walls)
    low, t = int(slot), slot - int(slot)
    return (1 - t) * walls[low % len(walls)] + t * walls[(low + 1) % len(walls)]


def nearest_target(goal, coins):
    """The nearest coin left, or the goal once every coin is collected."""
    left = [coin for coin in coins if np.linalg.norm(coin) > 1e-6]
    if left:
        return min(left, key=np.linalg.norm)
    return goal


class ArenaRunner(Model):
    workflow_edition = "2026.10"

    def __init__(self):
        super().__init__()
        self.on_episode_end()

    def on_episode_end(self):
        self.hug = None
        self.hug_steps = 0
        self.open_steps = 0
        self.last_distance = None

    def tangent(self, normal, pull, walls, obstacles):
        """The way along a wall with more room and fewer obstacles."""

        def score(direction):
            risk = 0.0
            for obstacle in obstacles:
                distance = np.linalg.norm(obstacle)
                toward = float(np.dot(direction, unit(obstacle)))
                if 1e-6 < distance < AVOID_RADIUS and toward > 0.3:
                    risk += toward * (AVOID_RADIUS - distance) / AVOID_RADIUS * 120.0
            return (
                clearance(direction, walls)
                + 80.0 * float(np.dot(direction, pull))
                - risk
            )

        left = np.array([-normal[1], normal[0]])
        return left if score(left) >= score(-left) else -left

    def predict(self, observation):
        walls = observation["walls"].astype(np.float64)
        obstacles = observation["obstacles"]
        target = nearest_target(observation["goal"], observation["coins"])
        distance = float(np.linalg.norm(target))
        if distance < 1e-6:
            return np.zeros(2, dtype=np.float32)
        if (
            self.last_distance is not None
            and abs(distance - self.last_distance) > 400.0
        ):
            self.hug = None  # a new target: the wall being followed no longer matters
            self.hug_steps = 0
            self.open_steps = 0
        self.last_distance = distance
        pull = unit(target)
        angles = np.arange(len(walls)) * 2 * math.pi / len(walls)
        rays = np.stack([np.cos(angles), np.sin(angles)], axis=1)
        ahead = clearance(pull, walls)

        if distance < 140.0 and ahead >= 50.0:
            self.hug = None
            return pull.astype(np.float32)

        push = np.zeros(2)
        if distance >= 120.0:
            limit = min(AVOID_RADIUS, max(distance * 0.4, 80.0))
            for obstacle in obstacles:
                gap = np.linalg.norm(obstacle)
                if 1e-6 < gap < limit:
                    push -= unit(obstacle) * (limit - gap) / limit

        if ahead >= CLEAR:
            self.open_steps += 1
            if self.open_steps >= 6:
                self.hug = None
            choice = pull + 0.45 * unit(push)
            choice = unit(choice if np.dot(unit(choice), pull) >= 0.3 else pull)
        else:
            self.open_steps = 0
            blocking = [
                i
                for i in range(len(walls))
                if walls[i] < CLEAR and np.dot(rays[i], pull) >= 0.15
            ]
            normal = rays[
                min(blocking, key=lambda i: walls[i])
                if blocking
                else int(np.argmin(walls))
            ]
            tangent = self.tangent(normal, pull, walls, obstacles)
            if (
                distance < 200.0
                or ahead < 45.0
                or self.hug is None
                or self.hug_steps >= 50
            ):
                self.hug, self.hug_steps = tangent, 0
            elif np.dot(self.hug, tangent) < 0.0:
                if clearance(self.hug, walls) < CLEAR * 0.55:
                    self.hug, self.hug_steps = tangent, 0
            else:
                self.hug = unit(0.7 * self.hug + 0.3 * tangent)
            self.hug_steps += 1
            choice = unit(self.hug - 0.45 * normal + 0.2 * unit(push))

        for ray, wall in zip(rays, walls, strict=True):
            into = float(np.dot(choice, ray))
            if wall < 65.0 and into > 0.0:
                choice = choice - into * ray
        if np.linalg.norm(choice) < 0.15:
            normal = rays[int(np.argmin(walls))]
            choice = -normal + self.tangent(normal, pull, walls, obstacles)

        for obstacle in obstacles:
            gap = np.linalg.norm(obstacle)
            toward = float(np.dot(unit(choice), unit(obstacle)))
            if 1e-6 < gap <= AVOID_RADIUS and toward > 0.35:
                choice = (
                    choice
                    - unit(obstacle)
                    * (1.0 + toward)
                    * (AVOID_RADIUS - gap)
                    / AVOID_RADIUS
                )
        if np.linalg.norm(choice) < 0.15:
            choice = pull
        return unit(choice).astype(np.float32)


if __name__ == "__main__":
    address = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:7447/env"
    print(rlmesh.run(ArenaRunner(), address, episodes=3))
