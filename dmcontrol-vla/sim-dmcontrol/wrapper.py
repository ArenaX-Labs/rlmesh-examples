import numpy as np
from gymnasium import spaces
from rlmesh import spaces as rlmesh_spaces


class RLMeshDmControlWrapper:
    def __init__(self, env, *, instruction, image_size=96, camera_id=0):
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

        self.observation_space = rlmesh_spaces.from_gymnasium_space(
            spaces.Dict(
                {
                    "image": spaces.Box(
                        0, 255, (image_size, image_size, 3), dtype=np.uint8
                    ),
                    "state": spaces.Box(-np.inf, np.inf, (state_dim,), dtype=np.float32),
                    "instruction": spaces.Text(max_length=256),
                }
            )
        )
        self.action_space = rlmesh_spaces.from_gymnasium_space(
            spaces.Box(low, high, dtype=np.float32)
        )
        self.metadata = {"render_fps": round(1.0 / env.control_timestep())}

    def reset(self, *, seed=None, options=None):
        return self._observation(self._env.reset()), {}

    def step(self, action):
        time_step = self._env.step(np.asarray(action, dtype=self._action_dtype))
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
        return {
            "image": self._frame(),
            "state": state,
            "instruction": self._instruction,
        }

    def _frame(self):
        return self._env.physics.render(
            height=self._image_size, width=self._image_size, camera_id=self._camera_id
        )
