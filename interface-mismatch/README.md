# Interface Mismatch

A `dm_control` env and chunk-emitting VLA-style model run through RLMesh, neither of which speaks the
standard env/model interface directly.

## Motivation

The other demos are about dependency conflicts: components that can't share a venv. This one is
about a different wall: a useful environment or model that doesn't speak the interface RLMesh
expects, even when there's no dependency clash at all.

You don't have to rewrite the component to fit. You write a small adapter that translates its native
shape into RLMesh's env/model contract. Here the `dm_control` env returns `dm_env.TimeStep` objects
and specs instead of Gymnasium-style tuples and spaces, and the VLA-style model emits a chunk of
future actions rather than one action per observation. A thin wrapper on each side bridges the gap,
and everything downstream sees an ordinary RLMesh env and model. The sections below walk through
those adapters.

You might ask why the model needs an adapter at all. In the other demos the agent owns the loop, so
you could just call the model however you like and never make it conform to anything. That's true
when you control the loop. But the way RLMesh scales up is the managed solution. In the managed solution, you
hand us the set of models and environmentss you want to run, and we run the loops for you. For that to work,
the model has to speak the RLMesh standard so we can drive it without knowing its internals. So the
model-side adapter here is preparation for that managed case.

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

RLMesh gives the env and model a platform-shaped boundary:

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

First run creates each `.venv`. If MuJoCo cannot find GL, start the server with
`MUJOCO_GL=egl uv run serve.py`.

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

## Swapping In SmolVLA

The included model is a tiny CPU stand-in with SmolVLA-shaped inputs and outputs. Real weights use
the same wrapper boundary, for example:

```python
from lerobot.policies.smolvla import SmolVLAPolicy

self._net = SmolVLAPolicy.from_pretrained("lerobot/smolvla_base")
```

The base SmolVLA model was trained for a different robot, so expect well-formed actions, not a
skillful policy, without fine-tuning.

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

## RLMesh Package

This demo depends on the published `rlmesh` package.

## Troubleshooting

| Symptom                         | Fix                                                                            |
| ------------------------------- | ------------------------------------------------------------------------------ |
| `mise.toml` is not trusted      | Run `mise trust` in that folder.                                               |
| MuJoCo cannot initialize OpenGL | Run `MUJOCO_GL=egl uv run serve.py` from `sim-dmcontrol`.                      |
| Port already in use             | Stop the process using `5558`, or update `ADDRESS` and `ENV_ADDRESS` together. |
| Need RLMesh traffic logs        | Run the env server with `RUST_LOG=info uv run serve.py`.                       |
