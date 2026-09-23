"""Scripted pick and place through a resolved RLMesh adapter, without Isaac imports."""

import argparse

import numpy as np
import rlmesh
import rlmesh.adapters as adapt
from rlmesh.numpy import Model

SPEC = adapt.ModelSpec(
    input={
        "camera": adapt.Image(
            adapt.IMAGE_PRIMARY,
            height=128,
            width=128,
            layout="chw",
            dtype="float32",
            normalize=True,
        ),
        "state": adapt.Concat(
            adapt.State(adapt.EEF_POS, frame="world"),
            adapt.State(adapt.EEF_ROT, encoding="axis_angle", frame="world"),
            adapt.State(adapt.GRIPPER_POS, range=(-1.0, 1.0)),
        ),
        "object": adapt.State("x/cube_pos", frame="world"),
        "goal": adapt.State("x/target_pos", frame="world"),
        "task": adapt.Text(adapt.INSTRUCTION),
    },
    # Deliberately different from the env: gripper first, in [-1, 1].
    output=adapt.Action(
        adapt.Actuator(adapt.ACTION_GRIPPER, dim=1, range=(-1.0, 1.0)),
        adapt.Actuator(adapt.ACTION_EEF_POS, dim=3, frame="world"),
    ),
)

PHASES = (
    "approach",
    "descend",
    "grasp",
    "lift",
    "transport",
    "lower",
    "release",
    "retract",
)
# Distances are metres from the cube centre to the tool flange. GRASP_OFFSET was
# measured for this asset under the tutorial's UR10 motion model; a kinematic
# model calibrated to the UR10e and its tool frame would change it.
GRASP_OFFSET = 0.185
CLEARANCE_OFFSET = 0.30
POSITION_TOLERANCE = 0.05  # Matches the tutorial's approximate UR10 motion model.


class PickPlacePolicy:
    def __init__(self):
        self.reset()

    def reset(self):
        self.phase = 0
        self.steps = 0
        self.pickup = None

    def predict(self, obs):
        if self.pickup is None:
            self.pickup = np.array(obs["object"], copy=True)
            print(
                f"camera={obs['camera'].shape}/{obs['camera'].dtype} "
                f"state={obs['state'].shape}"
            )
            print(f"task={obs['task']}")
        phase = self.phase
        if self.steps == 0:
            print(f"  {PHASES[phase]}", flush=True)
        position = self.pickup.copy() if phase < 4 else np.array(obs["goal"], copy=True)
        position[2] += CLEARANCE_OFFSET if phase in (0, 3, 4, 7) else GRASP_OFFSET
        grip = 1.0 if 2 <= phase <= 5 else -1.0
        action = np.array([grip, *position], np.float32)
        self.steps += 1
        near = np.linalg.norm(obs["state"][:3] - position) < POSITION_TOLERANCE
        # At 15 Hz, allow a second for the fingers to close or open.
        ready = self.steps >= 15 if phase in (2, 6) else self.steps >= 8 and near
        if ready and phase < 7:
            self.phase += 1
            self.steps = 0
        return action


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", default="127.0.0.1:50051")
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--record", help="Save metrics and camera video to a directory or .zip"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit unsuccessfully unless every episode succeeds",
    )
    parser.add_argument(
        "--view",
        choices=["terminal", "http", "both"],
        help="Watch the camera live: 'http' serves a page on localhost:8008",
    )
    args = parser.parse_args()
    if args.episodes < 1:
        parser.error("--episodes must be at least 1")

    policy = PickPlacePolicy()
    model = Model(policy.predict, spec=SPEC, on_episode_end=policy.reset)
    with rlmesh.Recorder(fps=15) as recorder:
        hooks = (
            recorder.capture(
                model="scripted-pick-place",
                env="ur10e-pick-place",
                cameras=[adapt.IMAGE_PRIMARY],
            )
            if args.record
            else None
        )
        with model.session(args.address, view=args.view) as session:
            result = session.run(
                seeds=list(range(args.seed, args.seed + args.episodes)), hooks=hooks
            )
        print(
            f"episodes={result.num_episodes} steps={result.total_steps} "
            f"success_rate={result.success_rate}"
        )
        if args.record:
            print(f"Recording: {recorder.export(args.record)}")
    if args.check and (
        result.num_episodes != args.episodes or result.success_rate != 1.0
    ):
        raise SystemExit(
            "Pick-and-place check failed: not all requested episodes succeeded"
        )


if __name__ == "__main__":
    main()
