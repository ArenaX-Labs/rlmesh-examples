# Interface Mismatch

A `dm_control` env and chunk-emitting VLA-style model run through RLMesh, neither of which speaks
the standard env/model interface directly.

`dm_control` returns `dm_env.TimeStep` objects and specs. The environment wrapper translates these
to Gymnasium-style reset/step results and spaces. The included untrained Torch model returns chunks
of eight actions; its wrapper buffers the chunk and returns one action per `predict()` call.

The model is a small stand-in for testing the adapter, not a trained robot policy.

## At A Glance

| Piece           | Stack                                                                   | Address / Role     |
| --------------- | ----------------------------------------------------------------------- | ------------------ |
| `sim-dmcontrol` | `dm-control` 1.0.31, MuJoCo 3.3.5, Gymnasium space adapter, Python 3.11 | `5558`             |
| `agent`         | Torch CPU VLA stand-in, `rlmesh.numpy.Model`, Python 3.11               | connects to `5558` |

This demo is about API shape, not resolver conflicts:

| Component   | Native Interface                         | RLMesh-Facing Interface                           |
| ----------- | ---------------------------------------- | ------------------------------------------------- |
| Env         | `dm_env.TimeStep`, `dm_env` specs        | `reset`, `step`, `render`, Gymnasium-style spaces |
| Model       | image + instruction + state -> chunk     | per-step `predict(observation) -> action`         |
| Observation | named arrays plus a rendered camera view | `{image, state, instruction}`                     |

## What RLMesh Changes

The wrappers connect the components through RLMesh:

```text
sim-dmcontrol (:5558)             agent/run.py
Python 3.11                       Python 3.11
dm_control / dm_env               Torch VLA stand-in
RLMeshDmControlWrapper            RLMeshVLAWrapper
        ----------------------->   model predict()
```

The env wrapper translates `dm_env` reset/step/specs. The model wrapper buffers action chunks and
returns one action per RLMesh `predict` call.

## Run

Open two terminals from the repo root.

### Terminal 1

```bash
cd interface-mismatch/sim-dmcontrol
uv run serve.py
```

### Terminal 2

```bash
cd interface-mismatch/agent
uv run run.py
```

First run creates each `.venv`. On a headless host, use `MUJOCO_GL=egl uv run serve.py` with an EGL
driver, or `MUJOCO_GL=osmesa PYOPENGL_PLATFORM=osmesa uv run serve.py` with OSMesa installed. Stop
the server with Ctrl-C when finished.

## Expected Output

The agent runs one episode and records the model's camera frames:

```text
VLA: <steps>step [...]
[agent] wrote videos/rollout.mp4
[agent] done
```

Read it as:

| Signal                | Meaning                                                                 |
| --------------------- | ----------------------------------------------------------------------- |
| Progress bar advances | RLMesh is driving the remote `dm_control` env through the model worker. |
| `rollout.mp4`         | The model received rendered image observations.                         |
| `[agent] done`        | The VLA wrapper produced a valid per-step action stream.                |

## Why Direct Integration Fails

RLMesh expects a small env/model contract. These components start elsewhere:

| Wall        | What Happens                                                                                                                            |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Env API     | `dm_control` returns `dm_env.TimeStep` objects and `dm_env` specs, not Gymnasium-style tuples and spaces.                               |
| Episode end | `dm_env` encodes terminal vs time-limit endings through `last()` and `discount`; the wrapper maps that to `terminated` and `truncated`. |
| Model API   | A VLA emits a chunk of future actions from image, language, and state, not one action from one observation.                             |

`RLMeshDmControlWrapper` adapts the env. `RLMeshVLAWrapper` adapts chunked actions.

## Using a trained model

Replace `VLAModel.predict_chunk()` with your model's inference call. Keep the returned shape
`(chunk_length, 5)` and match the environment's action bounds. A different model may also need image
preprocessing, state conversion, and robot-specific action mapping; replacing the weights alone is
not sufficient.

## Recording

Recording is on by default:

```python
RECORD = True
```

Change the setting at the top of `agent/run.py`.

| Setting          | Effect                                                             |
| ---------------- | ------------------------------------------------------------------ |
| `RECORD = True`  | Save the model's image observations to `agent/videos/rollout.mp4`. |
| `RECORD = False` | Faster run with no video output.                                   |

## Troubleshooting

| Symptom                         | Fix                                                                            |
| ------------------------------- | ------------------------------------------------------------------------------ |
| `mise.toml` is not trusted      | Run `mise trust` in that folder.                                               |
| MuJoCo cannot initialize OpenGL | Run `MUJOCO_GL=egl uv run serve.py` from `sim-dmcontrol`.                      |
| Port already in use             | Stop the process using `5558`, or update `ADDRESS` and `ENV_ADDRESS` together. |
| Need RLMesh traffic logs        | Run the env server with `RUST_LOG=info uv run serve.py`.                       |
