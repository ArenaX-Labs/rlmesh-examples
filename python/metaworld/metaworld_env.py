"""Meta-World MT1 tasks with camera, state, and instruction observations."""

import gymnasium as gym
import metaworld  # noqa: F401  (registers the Meta-World/* envs)
import numpy as np
import rlmesh
import rlmesh.adapters as adapt
import rlmesh.spaces as spaces

from tasks import TASK_DESCRIPTIONS

CAMERA_NAMES = ("topview", "corner", "corner2", "corner3", "behindGripper", "gripperPOV")
STATE_DIM = 39


class MetaWorldEnv:
    """One MT1 task, observed as {image, state, task}."""

    def __init__(self, env, instruction, image_size):
        self.env = env
        self.instruction = instruction
        # reset() picks the goal from the episode seed instead.
        self.env.get_wrapper_attr("toggle_sample_tasks_on_reset")(False)
        self.observation_space = spaces.Dict(
            {
                "image": spaces.Box(0, 255, (image_size, image_size, 3), "uint8"),
                "state": spaces.Box("-inf", "inf", (STATE_DIM,), "float64"),
                "task": spaces.Text(max_length=256),
            }
        )
        self.action_space = spaces.Box(-1.0, 1.0, (4,), "float32")

    def reset(self, *, seed=None, options=None):
        tasks = self.env.get_wrapper_attr("tasks")
        self.env.unwrapped.set_task(tasks[np.random.default_rng(seed).integers(len(tasks))])
        obs, info = self.env.reset(seed=seed, options=options)
        return self._obs(obs), info

    def step(self, action):
        obs, reward, _, truncated, info = self.env.step(action)
        success = bool(info.get("success", 0.0))
        info["is_success"] = success
        return self._obs(obs), reward, success, truncated, info

    def render(self):
        return self.env.render()

    def close(self):
        self.env.close()

    def _obs(self, obs):
        return {"image": self.env.render(), "state": obs, "task": self.instruction}


class MetaWorld(rlmesh.EnvFactory):
    tags = adapt.EnvTags(
        observation={
            # corner2 renders with both axes inverted. Declaring it lets RLMesh
            # rotate the frame for any model that expects it upright.
            "image": adapt.ImageTag(adapt.IMAGE_PRIMARY, upside_down=True),
            "state": adapt.Split(
                adapt.Field(adapt.EEF_POS, 3, frame="world"),
                adapt.Field(adapt.GRIPPER_POS, 1),
                adapt.Field(dim=STATE_DIM - 4),
            ),
            "task": adapt.TextTag(adapt.INSTRUCTION),
        },
        action=adapt.Action(
            adapt.Actuator(adapt.ACTION_DELTA_POS, dim=3),
            adapt.Actuator(adapt.ACTION_GRIPPER, dim=1, range=(-1.0, 1.0)),
            clip=(-1.0, 1.0),
        ),
    )

    params = rlmesh.ParamSpec(
        rlmesh.Param("env_name", type="str", description="MT1 task to load (e.g. 'reach-v3')."),
        rlmesh.Param(
            "camera_name",
            type="enum",
            choices=CAMERA_NAMES,
            description="Camera rendered into the image.",
        ),
        rlmesh.Param(
            "image_size", type="int", description="Rendered image height and width in pixels."
        ),
    )

    @classmethod
    def enumerate_variants(cls):
        for env_name, instruction in TASK_DESCRIPTIONS.items():
            yield rlmesh.Variant(
                env_name, {"env_name": env_name}, name=env_name, instruction=instruction
            )

    def make(self, *, env_name="reach-v3", camera_name="corner2", image_size=256):
        if image_size < 1:
            raise ValueError("image_size must be at least 1")
        env = gym.make(
            "Meta-World/MT1",
            env_name=env_name,
            # Fixed benchmark seed: MT1 samples its 50 candidate goals from the
            # global RNG, so without it every process gets a different goal set.
            seed=0,
            render_mode="rgb_array",
            camera_name=camera_name,
            width=image_size,
            height=image_size,
        )
        return MetaWorldEnv(env, TASK_DESCRIPTIONS.get(env_name, env_name), image_size)
