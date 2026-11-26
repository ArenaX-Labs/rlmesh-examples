# UR10e pick and place

A UR10e with a Robotiq 2F-140 gripper picks up a cube and places it on a target in Isaac Sim 6.1.
The scripted policy runs in a separate Python process. RLMesh resizes the camera image, converts the
tool pose, and maps gripper commands between the policy and simulator conventions.

Start with [`hello-env`](../../hello-env/) for the serving loop or
[`franka-reach`](../franka-reach/) for batched Franka reach. This example serves one robot and uses
the asset and PINK inverse-kinematics controller from
[NVIDIA's pick-and-place tutorial](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/robot_setup_tutorials/tutorial_pickplace_example.html).

## Run

The simulator needs a Linux x86_64 host with an RTX GPU, a compatible NVIDIA driver, Docker, and the
NVIDIA container runtime. Allow 16 GB of container memory. Assets download from NVIDIA at startup,
so the container needs internet access. The Dockerfile sets NVIDIA's EULA and privacy-consent
variables; review those terms before use.

The container serves on every interface, so it needs a host identity: make one, pass it to the
container, and dial the keyed address it prints.

```bash
docker build -t rlmesh-examples/isaacsim-pick-place python/isaacsim/ur10e-pick-place
cd python/isaacsim/ur10e-pick-place
uv run rlmesh host-identity new --out env.identity --address 127.0.0.1:7447 --participant env
# prints address=127.0.0.1:7447#<key>/env
RLMESH_HOST_IDENTITY="$(cat env.identity)" docker run --rm --gpus all --memory=16g \
  -e RLMESH_HOST_IDENTITY -p 127.0.0.1:7447:7447 rlmesh-examples/isaacsim-pick-place
```

Wait for `RLMesh serving env` in the container logs. In a second terminal:

```bash
cd python/isaacsim/ur10e-pick-place
RLMESH_ENV_ADDRESS='127.0.0.1:7447#<key>/env' uv run run.py --episodes 3 --check --record recordings/demo
```

The client prints each phase and the final success rate. `--check` exits with an error unless all
requested episodes succeed. `--record` writes a result bundle with camera video and episode metrics;
open the MP4 under `recordings/demo/media` to replay the run. Omit `--record` when you only need the
result. Add `--view http` to watch the camera live at `http://localhost:8008` while the episodes
run, or `--view terminal` over SSH. The client needs `uv`, but no Isaac Sim installation or GPU.
Stop the container with Ctrl-C after the demo.

## Walk through the adapter

Open [`ur10e_pick_place.py`](ur10e_pick_place.py) at `UR10ePickPlace.tags`, then [`run.py`](run.py)
at `SPEC`. The environment tags its observation fields and action layout; the model spec declares
the policy's input and output layout. `Model(policy.predict, spec=SPEC)` resolves the conversion
when it connects. Matching uses roles, so the environment's `image` can become the model's `camera`
and the model's gripper-first action can drive the environment's gripper-last action.

| Data          | Simulator format                       | Policy format                                     |
| ------------- | -------------------------------------- | ------------------------------------------------- |
| Camera        | `image`: 224 x 224 HWC RGB, uint8      | `camera`: 3 x 128 x 128 CHW, float32 in [0, 1]    |
| Tool pose     | Separate position and WXYZ quaternion  | `state`: position followed by axis-angle rotation |
| Gripper state | `finger_joint` angle, 0 to 0.5 radians | Last `state` element, normalized to [-1, 1]       |
| Task          | `instruction`                          | `task`                                            |
| Action        | `[x, y, z, finger_joint]`              | `[gripper, x, y, z]`, gripper in [-1, 1]          |

For example, the policy's `[-1, 0.5, 0.2, 0.325]` becomes `[0.5, 0.2, 0.325, 0]`: move the tool to
that world position with the fingers open. A gripper command of `+1` becomes `0.5` radians. Both
sides use metres and the same world frame.

The policy uses the cube and target positions supplied by the simulator, under custom roles
`x/cube_pos` and `x/target_pos`. Each role occurs once, so this single-arm example needs no `part=`.
The `joint_pos` observation is tagged for other policies but is not requested by this spec. If a
policy does request joint vectors, `labels=` can reorder axes when the two sides name the same full
set of joints. A second arm would use the same roles with a distinct `part=` on both the environment
tags and the model spec.

The scripted policy reads the adapted tool position to advance through approach, grasp, lift,
transport, release, and retract. The camera is converted and recorded, but the scripted policy does
not use vision to locate the cube.

Follow the action into `PickPlaceEnv.step()`: the environment holds the gripper's downward
orientation and passes the Cartesian target to PINK inverse kinematics. PINK computes arm joint
targets; Isaac Sim applies those targets and the gripper command. RLMesh handles the data conversion
and transport, while the environment owns robot control and physics.

The packaged tutorial pairs a UR10 motion model with the UR10e asset. This demo observes the
simulated wrist flange and allows 5 cm of position error before advancing to the next motion. For
tighter motion, use a kinematic model calibrated to the assembled robot and its tool frame.

Success requires the cube to have risen above 10 cm, then settled within 3.5 cm of the destination
with the fingers open and the tool retracted. A sequence that misses the cube times out. Each
episode resets the arm and object, and its seed varies the pickup position by up to 2 cm on each
horizontal axis.

## Check without a GPU

From the repository root, `uv run pytest python/isaacsim/ur10e-pick-place` checks image channels and
normalization, rotation encoding, action ordering, and gripper scaling against the example's adapter
declarations, and that the policy waits for the tool to arrive, follows the pickup and release
sequence, and resets between episodes. Use the container run with `--check` to test grasping and
release in physics.

## Use another robot or policy

To use a UR5e, replace the USD asset and kinematic model, assemble the gripper, and verify the tool
transforms and reachable poses. The grasp offset and motion tolerance are defined beside `PHASES` in
`run.py`. NVIDIA documents the robot setup in its
[custom robot adaptation guide](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/robot_setup_tutorials/tutorial_manipulator_workflow.html#adapt-the-examples-for-an-imported-or-custom-robot).

To connect a different policy, keep the environment tags and declare the policy's observation and
action conventions in its `ModelSpec`. Update the tags if you change what the environment produces
or accepts. The current controller assumes an uncluttered scene and a fixed grasp orientation; it
does not plan collision-free paths or recover a dropped object. This example controls a simulated
robot only.

The factory exposes `image_size` (default 224, minimum 128) and `max_steps` (default 600). For
example, add `-e 'RLMESH_MAKE_KWARGS={"max_steps": 800}'` to `docker run` to increase the episode
budget. Physics runs at 60 Hz with four simulation ticks per control step.
