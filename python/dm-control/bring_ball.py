"""dm_control's manipulator bring_ball task behind a Gymnasium-style reset/step."""

import numpy as np
import rlmesh
from gymnasium import spaces

INSTRUCTION = "bring the ball to the target"


class DmControlEnv:
    """Translate dm_env time steps and specs into Gymnasium-style results and spaces."""

    def __init__(self, env, *, instruction, image_size, camera_id=0):
        self._env = env
        self._instruction = instruction
        self._image_size = image_size
        self._camera_id = camera_id

        observation_spec = env.observation_spec()
        action_spec = env.action_spec()
        self._observation_keys = list(observation_spec)
        self._action_dtype = action_spec.dtype
        state_dim = sum(int(np.prod(spec.shape)) for spec in observation_spec.values())
        low = np.broadcast_to(action_spec.minimum, action_spec.shape).astype(np.float32)
        high = np.broadcast_to(action_spec.maximum, action_spec.shape).astype(np.float32)

        self.observation_space = spaces.Dict(
            {
                "image": spaces.Box(0, 255, (image_size, image_size, 3), dtype=np.uint8),
                "state": spaces.Box(-np.inf, np.inf, (state_dim,), dtype=np.float32),
                "instruction": spaces.Text(max_length=256),
            }
        )
        self.action_space = spaces.Box(low, high, dtype=np.float32)
        self.metadata = {"render_fps": round(1.0 / env.control_timestep())}

    def reset(self, *, seed=None, options=None):
        if seed is not None:
            self._env.task.random.seed(seed)
        return self._observation(self._env.reset()), {}

    def step(self, action):
        time_step = self._env.step(np.asarray(action, dtype=self._action_dtype))
        # dm_env ends an episode with last(); a zero discount marks a terminal state.
        terminated = time_step.last() and time_step.discount == 0.0
        truncated = time_step.last() and not terminated
        reward = float(time_step.reward) if time_step.reward is not None else 0.0
        return self._observation(time_step), reward, terminated, truncated, {}

    def render(self):
        return self._frame()

    def close(self):
        self._env.close()

    def _observation(self, time_step):
        state = np.concatenate(
            [
                np.asarray(time_step.observation[key], dtype=np.float32).ravel()
                for key in self._observation_keys
            ]
        )
        return {"image": self._frame(), "state": state, "instruction": self._instruction}

    def _frame(self):
        return self._env.physics.render(
            height=self._image_size, width=self._image_size, camera_id=self._camera_id
        )


class BringBall(rlmesh.EnvFactory):
    params = rlmesh.ParamSpec(
        rlmesh.Param("image_size", type="int", description="Camera image height and width."),
    )

    def make(self, *, image_size=128):
        from dm_control import suite

        env = suite.load("manipulator", "bring_ball", task_kwargs={"time_limit": 4.0})
        return DmControlEnv(env, instruction=INSTRUCTION, image_size=image_size)
