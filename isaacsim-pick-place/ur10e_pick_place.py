"""One UR10e + Robotiq 2F-140, with PINK IK behind an RLMesh environment.

Uses the asset and motion configuration from NVIDIA's Isaac Sim 6.1 Tutorial 9:
https://docs.isaacsim.omniverse.nvidia.com/6.1.0/robot_setup_tutorials/tutorial_pickplace_example.html
"""

import os
import sys
import traceback

import numpy as np
import rlmesh
import rlmesh.adapters as adapt
import rlmesh.spaces as spaces

ROBOT_USD = (
    "/Isaac/Samples/Rigging/Manipulator/configure_manipulator/ur10e/ur/ur_gripper.usd"
)
ARM_NAMES = (
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint",
)
ARM_HOME = np.array([-np.pi, -np.pi / 2, -np.pi / 2, -np.pi / 2, np.pi / 2, 0.0])
PHYSICS_DT = 1.0 / 60.0
CONTROL_SUBSTEPS = 4
GRIPPER_CLOSED = 0.5  # finger_joint radians; 0 is open
INSTRUCTION = "Pick up the red cube and place it on the green target."


def observation_space(image_size: int):
    return spaces.Dict(
        {
            "image": spaces.Box(0, 255, (image_size, image_size, 3), "uint8"),
            "joint_pos": spaces.Box("-inf", "inf", (6,), "float32"),
            "eef_pos": spaces.Box("-inf", "inf", (3,), "float32"),
            "eef_quat": spaces.Box(-1, 1, (4,), "float32"),
            "gripper": spaces.Box("-inf", "inf", (1,), "float32"),
            "cube_pos": spaces.Box("-inf", "inf", (3,), "float32"),
            "target_pos": spaces.Box("-inf", "inf", (3,), "float32"),
            "instruction": spaces.Text(max_length=128),
        }
    )


# Per-component workspace bounds are enforced in step(). Positions are metres in
# the world frame; the gripper value is the finger joint angle in radians.
ACTION_SPACE = spaces.Box("-inf", "inf", (4,), "float32")


class PickPlaceEnv:
    def __init__(self, app, image_size: int, max_steps: int):
        self.app = app
        self.max_steps = max_steps
        self.observation_space = observation_space(image_size)
        self.action_space = ACTION_SPACE
        self._build_stage(image_size)

    def _build_stage(self, image_size: int):
        import isaacsim.core.experimental.utils.stage as stage_utils
        import omni.timeline
        from isaacsim.core.experimental.materials import PreviewSurfaceMaterial
        from isaacsim.core.experimental.objects import Cube, DomeLight, GroundPlane
        from isaacsim.core.experimental.prims import Articulation, GeomPrim, RigidPrim
        from isaacsim.core.simulation_manager import SimulationManager
        from isaacsim.core.utils.viewports import set_camera_view
        from isaacsim.robot_motion.pink import (
            PinkIKController,
            load_pink_supported_robot,
        )
        from isaacsim.sensors.experimental.rtx import CameraSensor, RtxCamera
        from isaacsim.storage.native import get_assets_root_path

        stage_utils.create_new_stage()
        SimulationManager.setup_simulation(dt=PHYSICS_DT, device="cpu")
        stage_utils.add_reference_to_stage(
            get_assets_root_path() + ROBOT_USD, path="/World/robot"
        )
        GroundPlane("/World/ground")
        DomeLight("/World/light").set_intensities(1000)
        red = PreviewSurfaceMaterial("/Looks/red")
        red.set_input_values("diffuseColor", [0.8, 0.05, 0.03])
        cube = Cube("/World/cube", positions=[[0.5, 0.0, 0.025]], sizes=0.05)
        cube.apply_visual_materials(red)
        GeomPrim(cube.paths, apply_collision_apis=True)
        self.cube = RigidPrim(cube.paths)
        self.cube.set_masses(0.05)
        green = PreviewSurfaceMaterial("/Looks/green")
        green.set_input_values("diffuseColor", [0.05, 0.7, 0.1])
        self.marker = Cube("/World/target", sizes=1.0, scales=[0.10, 0.10, 0.002])
        self.marker.apply_visual_materials(green)

        self.robot = Articulation("/World/robot")
        self.arm_indices = [self.robot.dof_names.index(name) for name in ARM_NAMES]
        self.finger_index = self.robot.dof_names.index("finger_joint")
        self.home = np.zeros(len(self.robot.dof_names), np.float32)
        self.home[self.arm_indices] = ARM_HOME
        self.robot.set_default_state(dof_positions=self.home)
        camera = RtxCamera("/World/camera")
        set_camera_view(
            eye=[1.5, 1.5, 1.1],
            target=[0.3, 0.2, 0.25],
            camera_prim_path="/World/camera",
        )
        self.camera = CameraSensor(
            camera, resolution=(image_size, image_size), annotators=["rgb"]
        )
        self.controller = PinkIKController(
            # NVIDIA's tutorial pairs this model with the packaged UR10e USD.
            pink_robot=load_pink_supported_robot("ur10"),
            robot_joint_space=self.robot.dof_names,
            robot_site_space=["tool0"],
            tool_frame="tool0",
            position_cost=0.5,
            orientation_cost=1.0,
            posture_cost=1e-3,
            solver="osqp",
            dt=PHYSICS_DT,
        )
        omni.timeline.get_timeline_interface().play()
        self.app.update()
        # The sample USD's wrist origin is the flange. Its URDF calls that
        # control frame tool0; tool0 is not a rigid link in the USD.
        wrist = self.robot.link_paths[0][self.robot.link_names.index("wrist_3_link")]
        self.tool = GeomPrim(wrist)

    def _estimated_state(self):
        import isaacsim.robot_motion.experimental.motion_generation as mg

        names = self.robot.dof_names
        return mg.RobotState(
            joints=mg.JointState.from_name(
                robot_joint_space=names,
                positions=(names, self.robot.get_dof_positions()),
                velocities=(names, self.robot.get_dof_velocities()),
            )
        )

    def reset(self, *, seed=None, options=None):
        rng = np.random.default_rng(seed)
        self.target = np.array([0.5, 0.4, 0.025], np.float32)
        pickup = np.array([0.5, 0.0, 0.025])
        pickup[:2] += rng.uniform(-0.02, 0.02, 2)
        self.robot.set_dof_positions(self.home)
        self.robot.set_dof_velocities(0.0)
        self.robot.set_dof_position_targets(self.home)
        self.cube.set_world_poses(positions=pickup, orientations=[1.0, 0.0, 0.0, 0.0])
        self.cube.set_velocities(
            linear_velocities=np.zeros(3), angular_velocities=np.zeros(3)
        )
        self.marker.set_world_poses(positions=[*self.target[:2], 0.001])
        for _ in range(30):
            self.app.update()
        if not self.controller.reset(self._estimated_state(), None, t=0.0):
            raise RuntimeError("PINK could not initialize from the robot's joint state")
        self.steps = 0
        self.lifted = False
        self.settled_steps = 0
        return self._observe(), {"is_success": False}

    def step(self, action):
        import isaacsim.robot_motion.experimental.motion_generation as mg
        import warp as wp

        action = np.asarray(action, dtype=np.float32)
        if action.shape != (4,) or not np.isfinite(action).all():
            raise ValueError(
                "Expected four finite values: tool x, y, z and gripper joint angle"
            )
        action = np.clip(
            action, [0.2, -0.4, 0.18, 0.0], [0.8, 0.7, 0.8, GRIPPER_CLOSED]
        )
        # Absolute world-space tool position; keep the gripper pointing down.
        setpoint = mg.RobotState(
            sites=mg.SpatialState.from_name(
                spatial_space=["tool0"],
                positions=(["tool0"], wp.array(action[None, :3], dtype=wp.float32)),
                orientations=(
                    ["tool0"],
                    wp.array([[0.0, 0.0, 1.0, 0.0]], dtype=wp.float32),
                ),
            )
        )
        for substep in range(CONTROL_SUBSTEPS):
            time = (self.steps * CONTROL_SUBSTEPS + substep) * PHYSICS_DT
            desired = self.controller.forward(self._estimated_state(), setpoint, time)
            if (
                desired is None
                or desired.joints is None
                or desired.joints.positions is None
            ):
                raise RuntimeError("PINK failed to produce a joint target")
            self.robot.set_dof_position_targets(
                desired.joints.positions, dof_indices=desired.joints.position_indices
            )
            self.robot.set_dof_position_targets(
                [action[3]], dof_indices=[self.finger_index]
            )
            self.app.update()
            self.lifted |= bool(self.cube.get_world_poses()[0].numpy()[0, 2] > 0.10)
        self.steps += 1
        obs = self._observe()
        distance = float(np.linalg.norm(obs["cube_pos"] - self.target))
        # Require a physical lift, release and retreat, then let the cube settle.
        placed = (
            self.lifted  # cube centre rose above 10 cm at some point
            and distance < 0.035  # within 3.5 cm of the target centre
            and obs["gripper"][0] < 0.08  # fingers open (rad)
            and obs["eef_pos"][2] > 0.28  # flange retracted above the cube
            and np.linalg.norm(self.cube.get_velocities()[0].numpy()[0]) < 0.03  # m/s
        )
        self.settled_steps = self.settled_steps + 1 if placed else 0
        success = self.settled_steps >= 8  # about 0.5 s at 15 Hz control
        truncated = self.steps >= self.max_steps and not success
        info = {"is_success": success, "lifted": self.lifted, "distance": distance}
        return obs, float(success) - distance, success, truncated, info

    def _observe(self):
        rgb, _ = self.camera.get_data("rgb")
        if rgb is None:
            raise RuntimeError("RTX camera has not produced an RGB frame")
        position, orientation = self.tool.get_world_poses()
        joints = self.robot.get_dof_positions().numpy()[0]
        self._image = rgb.numpy()[..., :3].copy()
        return {
            "image": self._image,
            "joint_pos": joints[self.arm_indices].astype(np.float32),
            "eef_pos": position.numpy()[0].astype(np.float32),
            "eef_quat": orientation.numpy()[0].astype(np.float32),
            "gripper": np.array([joints[self.finger_index]], np.float32),
            "cube_pos": self.cube.get_world_poses()[0].numpy()[0].astype(np.float32),
            "target_pos": self.target.copy(),
            "instruction": INSTRUCTION,
        }

    def render(self):
        return self._image

    def close(self):
        pass  # The factory owns SimulationApp and closes it once at server shutdown.


class UR10ePickPlace(rlmesh.EnvFactory):
    workflow_edition = "2026.06"
    params = rlmesh.ParamSpec(
        rlmesh.Param(
            "image_size",
            type="int",
            description="Square RGB camera resolution (at least 128).",
        ),
        rlmesh.Param(
            "max_steps", type="int", description="Control steps before truncation."
        ),
    )
    tags = adapt.EnvTags(
        observation={
            "image": adapt.ImageTag(adapt.IMAGE_PRIMARY),
            "joint_pos": adapt.StateTag(adapt.JOINT_POS),
            "eef_pos": adapt.StateTag(adapt.EEF_POS, frame="world"),
            "eef_quat": adapt.StateTag(
                adapt.EEF_ROT, encoding="quat_wxyz", frame="world"
            ),
            "gripper": adapt.StateTag(adapt.GRIPPER_POS, range=(0.0, GRIPPER_CLOSED)),
            "cube_pos": adapt.StateTag("x/cube_pos", frame="world"),
            "target_pos": adapt.StateTag("x/target_pos", frame="world"),
            "instruction": adapt.TextTag(adapt.INSTRUCTION),
        },
        action=adapt.Action(
            adapt.Actuator(adapt.ACTION_EEF_POS, dim=3, frame="world"),
            adapt.Actuator(
                adapt.ACTION_GRIPPER, dim=1, range=(0.0, GRIPPER_CLOSED), clip=True
            ),
        ),
    )

    def prepare(self):
        from isaacsim import SimulationApp

        # Kit parses sys.argv; keep RLMesh's server arguments out of its parser.
        argv = sys.argv
        sys.argv = sys.argv[:1]
        try:
            self.app = SimulationApp({"headless": True})
        finally:
            sys.argv = argv

        def exit_on_error(exc_type, exc_value, exc_traceback):
            # Kit's default handler can turn an uncaught server error into exit 0.
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            sys.stderr.flush()
            os._exit(1)

        sys.excepthook = exit_on_error
        import omni.kit.app

        omni.kit.app.get_app().get_extension_manager().set_extension_enabled_immediate(
            "isaacsim.robot_motion.pink", True
        )

    def make(self, *, image_size=224, max_steps=600):
        if image_size < 128 or max_steps < 1:
            raise ValueError("image_size must be at least 128 and max_steps at least 1")
        return PickPlaceEnv(self.app, image_size, max_steps)

    def close(self):
        self.app.close()
