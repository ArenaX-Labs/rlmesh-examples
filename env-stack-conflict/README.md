# Env Stack Conflict

One policy, two incompatible simulator stacks, one container each.

Safety-Gymnasium pins Gymnasium and MuJoCo versions that conflict with the modern simulator. Each
environment runs in its own container, and one NumPy policy connects to both through `RemoteEnv`.
Both expose a 17-value observation and a 6-value action.

For a conflict between a trained model and an environment, see
[`model-env-conflict`](../model-env-conflict/).

## At A Glance

| Piece        | Stack                                                               | Serves                  | Host port        |
| ------------ | ------------------------------------------------------------------- | ----------------------- | ---------------- |
| `sim-safety` | Safety-Gymnasium 1.0.0, Gymnasium 0.28.1, MuJoCo 2.3.3, Python 3.10 | `env:HalfCheetahSafety` | `50051`          |
| `sim-modern` | Gymnasium 1.x, MuJoCo 3.3, Python 3.11                              | `env:HalfCheetahModern` | `50052`          |
| `agent`      | `rlmesh` + NumPy, Python 3.11                                       | -                       | connects to both |

Both environments expose the same HalfCheetah-shaped interface:

```text
observation: Box(17)
action:      Box(6)
```

The policy can drive both. The packages cannot share one Python environment.

## What RLMesh Changes

Each simulator is an `EnvFactory` in its own `env.py`, packaged in its own image:

```text
sim-safety image (:50051)   sim-modern image (:50052)
Python 3.10                 Python 3.11
Safety/MuJoCo 2.x           Gymnasium/MuJoCo 3.x
          \                  /
           \                /
            agent/eval.py
            one policy, two RemoteEnv objects
```

The whole env side is a few lines per stack:

```python
class HalfCheetahModern(rlmesh.EnvFactory):
    workflow_edition = "2026.06"

    def make(self) -> gym.Env:
        return gym.make("HalfCheetah-v5", render_mode="rgb_array")
```

## Run

From the repo root, build both images:

```bash
docker build -t rlmesh-examples/env-stack-conflict/sim-safety env-stack-conflict/sim-safety
docker build -t rlmesh-examples/env-stack-conflict/sim-modern env-stack-conflict/sim-modern
```

Start them:

```bash
docker run --rm -d --name sim-safety -p 127.0.0.1:50051:50051 rlmesh-examples/env-stack-conflict/sim-safety
docker run --rm -d --name sim-modern -p 127.0.0.1:50052:50051 rlmesh-examples/env-stack-conflict/sim-modern
```

Run the agent:

```bash
cd env-stack-conflict/agent
uv run eval.py
```

Stop the containers with `docker stop sim-safety sim-modern`.

### Without Docker

Each sim folder is also a plain `uv` project. Install OSMesa if recording or viewing frames
(`libosmesa6` on Debian/Ubuntu, `mesa-libOSMesa` on Fedora). In two terminals:

```bash
cd env-stack-conflict/sim-safety
MUJOCO_GL=osmesa PYOPENGL_PLATFORM=osmesa RLMESH_ADDRESS=127.0.0.1:50051 uv run python -m rlmesh.serve --env env:HalfCheetahSafety
```

```bash
cd env-stack-conflict/sim-modern
MUJOCO_GL=osmesa PYOPENGL_PLATFORM=osmesa RLMESH_ADDRESS=127.0.0.1:50052 uv run python -m rlmesh.serve --env env:HalfCheetahModern
```

## Expected Output

The agent runs one policy against both envs:

```text
=== one policy, two simulator stacks ===
safety/mujoco2.3   obs=(17,) steps=500 return=<float> cost=<float>
modern/mujoco3.3   obs=(17,) steps=500 return=<float> cost=0.0
```

Read it as:

| Signal             | Meaning                                                                                               |
| ------------------ | ----------------------------------------------------------------------------------------------------- |
| Same `obs` shape   | One policy fits both envs.                                                                            |
| Different returns  | Returns differ across tasks and simulator stacks; this is not an isolated measure of simulator drift. |
| Safety `cost` only | Safety-Gymnasium reports constraint cost; plain `HalfCheetah-v5` does not.                            |

The agent also writes `agent/results.json`.

## Why One Python Fails

Safety-Gymnasium 1.0.0 pins the old stack:

| Package   | Required By Safety-Gymnasium                |
| --------- | ------------------------------------------- |
| Gymnasium | `0.28.1`                                    |
| MuJoCo    | `2.3.3`                                     |
| Python    | effectively 3.10 because of `pygame==2.1.0` |

The modern simulator uses newer Gymnasium/MuJoCo. No single venv satisfies both.

<details>
<summary>Show example resolver failures</summary>

```text
$ uv pip install "safety-gymnasium==1.0.0" "mujoco==3.3.5"
  x No solution found: safety-gymnasium==1.0.0 depends on mujoco==2.3.3
    and you require mujoco==3.3.5

$ uv pip install "safety-gymnasium==1.0.0" "gymnasium[mujoco]>=1.2"
  x No solution found: safety-gymnasium==1.0.0 depends on gymnasium==0.28.1
```

</details>

## Recording

Recording is off by default:

```python
RECORD = False
WATCH = False
```

Change those constants in `agent/eval.py`:

| Setting         | Effect                                                   |
| --------------- | -------------------------------------------------------- |
| `RECORD = True` | Save mp4s under `agent/videos/`.                         |
| `WATCH = True`  | Open live viewer windows with `RemoteEnv.open_viewer()`. |

Frames are rendered inside the containers (headless OSMesa) and streamed to the agent.

## Troubleshooting

| Symptom                                 | Fix                                                         |
| --------------------------------------- | ----------------------------------------------------------- |
| Agent can't connect                     | Check `docker ps` shows both containers on 50051 and 50052. |
| Python 3.11 is selected in `sim-safety` | Run `uv run --python 3.10 ...`, or `mise trust` once.       |
| Need RLMesh traffic logs                | Add `-e RUST_LOG=info` to `docker run`.                     |
