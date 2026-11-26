# dm_control

A `dm_control` task and a model that emits chunks of eight actions, neither of which speaks the
Gymnasium interface, run against each other through RLMesh.

## Run it

```bash
MUJOCO_GL=egl uv run --directory python/dm-control python -m rlmesh.serve --env bring_ball:BringBall --address 127.0.0.1:7447
uv run --directory python/dm-control run.py --episodes 2    # in a second terminal
```

It prints `episodes=2 steps=800 model_calls=100`: the model runs once every eight env steps.

## The RLMesh part

The env maps `dm_env`'s time steps onto reset and step: `last()` ends an episode and a zero
`discount` marks it terminal ([`bring_ball.py`](bring_ball.py)):

```python
def step(self, action):
    time_step = self._env.step(np.asarray(action, dtype=self._action_dtype))
    # dm_env ends an episode with last(); a zero discount marks a terminal state.
    terminated = time_step.last() and time_step.discount == 0.0
    truncated = time_step.last() and not terminated
    reward = float(time_step.reward) if time_step.reward is not None else 0.0
    return self._observation(time_step), reward, terminated, truncated, {}
```

The model stands in for a VLA action head: it declares its chunk length and returns a chunk per
call, and `execution_horizon` plays the whole chunk before asking again ([`run.py`](run.py)):

```python
class ChunkPolicy(Model):
    native_chunk = CHUNK

    def predict_chunk(self, observation):
        self.calls += 1
        chunk = np.tanh(observation["state"] @ self.weights)
        return chunk.reshape(CHUNK, ACTION_DIM).astype(np.float32)


result = model.run(args.address, episodes=args.episodes, execution_horizon=CHUNK)
```

## Needs

CPU. MuJoCo renders the camera with EGL, or OSMesa without a GPU driver (`MUJOCO_GL=osmesa`,
`libosmesa6` or `mesa-libOSMesa`).

## Next

- Replace `predict_chunk()` with your model's inference, keeping the `(8, 5)` shape within the env's
  action bounds. Without `execution_horizon` the model replans every step.
- [`vla-adapters`](../vla-adapters/): chunking with temporal ensembling as a custom adapter.
