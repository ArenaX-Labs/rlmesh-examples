"""LIBERO tasks with camera observations and a fixed initial state per trial."""

import pathlib

import numpy as np
import rlmesh
import rlmesh.adapters as adapt
import rlmesh.spaces as spaces

# Let the scene settle with the gripper open before the policy acts.
SETTLE_STEPS = 10
SETTLE_ACTION = np.array([0.0] * 6 + [-1.0], dtype=np.float32)

# Episode budgets used by LIBERO evaluations.
SUITE_MAX_STEPS = {
    "libero_spatial": 220,
    "libero_object": 280,
    "libero_goal": 300,
    "libero_10": 520,
    "libero_90": 400,
}

IMAGE_KEYS = ("agentview_image", "robot0_eye_in_hand_image")
STATE_KEYS = {"robot0_eef_pos": 3, "robot0_eef_quat": 4, "robot0_gripper_qpos": 2}


class LiberoEnv:
    """One LIBERO task, observed as two images + proprio + instruction."""

    def __init__(self, env, initial_states, instruction, image_size, max_steps):
        self.env = env
        self.initial_states = initial_states
        self.instruction = instruction
        self.max_steps = max_steps
        self.observation_space = spaces.Dict(
            {
                **{key: spaces.Box(0, 255, (image_size, image_size, 3), "uint8") for key in IMAGE_KEYS},
                **{key: spaces.Box("-inf", "inf", (dim,), "float32") for key, dim in STATE_KEYS.items()},
                "instruction": spaces.Text(max_length=256),
            }
        )
        self.action_space = spaces.Box(-1.0, 1.0, (7,), "float32")

    def reset(self, *, seed=None, options=None):
        # reset_options tells RLMesh to supply the episode's trial number.
        trial = rlmesh.trial_index(options)
        if trial is None:
            raise RuntimeError(
                "reset() received no trial_index; on a hand-driven reset pass options={'trial_index': k}"
            )
        self.env.seed(seed)
        self.env.reset()
        obs = self.env.set_init_state(self.initial_states[trial % len(self.initial_states)])
        for _ in range(SETTLE_STEPS):
            obs, *_ = self.env.step(SETTLE_ACTION)
        self.steps = 0
        return self._obs(obs), {}

    def step(self, action):
        # robosuite returns (obs, reward, done, info); with ignore_done=True,
        # `done` is LIBERO's task-success check and the budget is ours.
        obs, reward, success, info = self.env.step(action)
        self.steps += 1
        info["is_success"] = bool(success)
        return self._obs(obs), reward, bool(success), self.steps >= self.max_steps, info

    def render(self):
        return self._last["agentview_image"][::-1]

    def close(self):
        self.env.close()

    def _obs(self, obs):
        self._last = {
            **{key: obs[key] for key in IMAGE_KEYS},
            **{key: np.asarray(obs[key], dtype=np.float32) for key in STATE_KEYS},
        }
        self._last["instruction"] = self.instruction
        return self._last


class Libero(rlmesh.EnvFactory):
    workflow_edition = "2026.06"

    tags = adapt.EnvTags(
        observation={
            "agentview_image": adapt.ImageTag(adapt.IMAGE_PRIMARY, upside_down=True),
            "robot0_eye_in_hand_image": adapt.ImageTag(adapt.IMAGE_WRIST, upside_down=True),
            "robot0_eef_pos": adapt.StateTag(adapt.EEF_POS),
            "robot0_eef_quat": adapt.StateTag(adapt.EEF_ROT, encoding="quat_xyzw"),
            "robot0_gripper_qpos": adapt.StateTag(adapt.GRIPPER_POS),
            "instruction": adapt.TextTag(adapt.INSTRUCTION),
        },
        # OSC_POSE delta control: position, axis-angle rotation, gripper.
        action=adapt.Action(
            adapt.Actuator(adapt.ACTION_DELTA_POS, dim=3),
            adapt.Actuator(adapt.ACTION_DELTA_ROT, dim=3, encoding="axis_angle"),
            adapt.Actuator(adapt.ACTION_GRIPPER, dim=1, range=(-1.0, 1.0)),
            clip=(-1.0, 1.0),
        ),
    )
    reset_options = ("trial_index",)

    params = rlmesh.ParamSpec(
        rlmesh.Param("task_suite", type="str", description="LIBERO task suite to load."),
        rlmesh.Param("task_id", type="int", description="Index of the task within the suite."),
        rlmesh.Param("image_size", type="int", description="Camera image height and width in pixels."),
        rlmesh.Param(
            "max_episode_steps",
            type="int",
            description="Steps before the episode truncates. Defaults to upstream's budget for the suite.",
        ),
    )

    @classmethod
    def enumerate_variants(cls):
        from libero.libero import benchmark

        suites = benchmark.get_benchmark_dict()
        for task_suite in benchmark.libero_task_map:
            for idx, task in enumerate(suites[task_suite]().tasks):
                yield rlmesh.Variant(
                    f"{task_suite}/{idx}",
                    {"task_suite": task_suite, "task_id": idx},
                    name=task.name,
                    instruction=task.language,
                )

    def make(self, *, task_suite="libero_10", task_id=0, image_size=256, max_episode_steps=None):
        from libero.libero import benchmark, get_libero_path
        from libero.libero.envs import OffScreenRenderEnv

        if image_size < 1:
            raise ValueError("image_size must be at least 1")
        max_steps = SUITE_MAX_STEPS[task_suite] if max_episode_steps is None else max_episode_steps
        if max_steps < 1:
            raise ValueError("max_episode_steps must be at least 1")
        suite = benchmark.get_benchmark_dict()[task_suite]()
        if not 0 <= task_id < len(suite.tasks):
            raise ValueError(f"task_id must be between 0 and {len(suite.tasks) - 1}")
        task = suite.get_task(task_id)
        bddl = pathlib.Path(get_libero_path("bddl_files")) / task.problem_folder / task.bddl_file
        # The wrapper owns the episode budget; disable robosuite's horizon.
        env = OffScreenRenderEnv(
            bddl_file_name=bddl, camera_heights=image_size, camera_widths=image_size, ignore_done=True
        )
        return LiberoEnv(
            env,
            suite.get_task_init_states(task_id),
            task.language,
            image_size,
            max_steps,
        )
