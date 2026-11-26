# dm_control

A `dm_control` env and a chunk-emitting model, neither of which speaks the Gymnasium env/model
interface directly, run through RLMesh.

| Piece           | Native interface                    | What RLMesh sees                                  |
| --------------- | ----------------------------------- | ------------------------------------------------- |
| `bring_ball.py` | `dm_env.TimeStep` objects and specs | `reset`, `step`, `render`, Gymnasium-style spaces |
| `run.py`        | state → a chunk of eight actions    | a model with `native_chunk = 8`                   |
| Observation     | named arrays plus a rendered camera | `{image, state, instruction}`                     |

`DmControlEnv` translates `dm_env` reset, step and specs. `dm_env` marks an episode's end with
`last()` and a terminal state with a zero `discount`; the wrapper maps that onto `terminated` and
`truncated`.

`ChunkPolicy` stands in for a VLA action head: it implements `predict_chunk()` and declares
`native_chunk`, and `run(..., execution_horizon=8)` plays all eight actions before asking for the
next chunk, so the model runs once every eight env steps. Without `execution_horizon` it would
replan every step. Its weights are random; replace `predict_chunk()` with your model's inference and
keep the returned shape `(8, 5)` within the env's action bounds.

## Run

Hardware: CPU. MuJoCo renders with EGL (`MUJOCO_GL=egl`) or, without a GPU driver, OSMesa
(`MUJOCO_GL=osmesa`, `libosmesa6` on Debian/Ubuntu, `mesa-libOSMesa` on Fedora).

```bash
cd dm-control
MUJOCO_GL=egl RLMESH_ADDRESS=127.0.0.1:7447 uv run python -m rlmesh.serve --env bring_ball:BringBall
```

In a second terminal:

```bash
cd dm-control
uv run run.py --episodes 2
```

```text
episodes=2 steps=800 model_calls=100
```

Stop the server with Ctrl-C when finished.
