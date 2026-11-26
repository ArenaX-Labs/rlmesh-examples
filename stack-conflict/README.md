# Stack Conflict

A pretrained SAC policy evaluates a safety env it cannot share a virtual environment with.

The Stable-Baselines3 SAC checkpoint was trained on Gymnasium 1.x, MuJoCo 3 and NumPy 2.
Safety-Gymnasium 1.0.0 pins Gymnasium 0.28.1, MuJoCo 2.3.3 and Python 3.10. Each side gets its own
Python, and RLMesh carries observations and actions between them.

| Piece        | Stack                                                               | Role                                                |
| ------------ | ------------------------------------------------------------------- | --------------------------------------------------- |
| `sim-safety` | Safety-Gymnasium 1.0.0, Gymnasium 0.28.1, MuJoCo 2.3.3, Python 3.10 | serves `env:HalfCheetahSafety`                      |
| `agent`      | Stable-Baselines3 SAC, Gymnasium 1.x, MuJoCo 3, Python 3.11         | runs `HalfCheetah-v5` here, the safety env remotely |

```text
sim-safety (Python 3.10)            agent/eval.py (Python 3.11)
Safety-Gymnasium / MuJoCo 2.3       SAC checkpoint, Gymnasium / MuJoCo 3
        <------------------------>  RemoteEnv
```

Hardware: CPU. Docker for the container.

## Run

Build the safety env image and run the agent against it as a sandbox:

```bash
docker build -t rlmesh-examples/stack-conflict-safety stack-conflict/sim-safety
cd stack-conflict/agent
uv run eval.py --image rlmesh-examples/stack-conflict-safety
```

Or serve the env on the host, with OSMesa or EGL for MuJoCo's renderer:

```bash
cd stack-conflict/sim-safety
MUJOCO_GL=egl RLMESH_ADDRESS=127.0.0.1:7447 uv run python -m rlmesh.serve --env env:HalfCheetahSafety
```

and run `uv run eval.py` from `stack-conflict/agent` in a second terminal.

```text
modern-halfcheetah-v5        steps= 100 return=   310.7 cost=   0.0
safety-halfcheetah-velocity  steps= 100 return=   327.7 cost=  63.0
```

| Signal             | Meaning                                                                                  |
| ------------------ | ---------------------------------------------------------------------------------------- |
| One checkpoint     | The policy loads once, in the stack it was trained on.                                   |
| Two returns        | The tasks and simulator stacks differ; this does not isolate simulator drift.            |
| Safety `cost` only | Safety-Gymnasium reports a constraint cost in `info["cost"]`; `HalfCheetah-v5` does not. |

## Why one Python fails

```text
$ uv pip install "stable-baselines3>=2.7" "safety-gymnasium==1.0.0"
  x No solution found:
    stable-baselines3>=2.7.0 depends on gymnasium>=0.29.1,<1.3.0
    and safety-gymnasium==1.0.0 depends on gymnasium==0.28.1
```

The older SB3 that fits beside Safety-Gymnasium resolves to NumPy 1.23.5, which cannot load a
checkpoint saved with NumPy 2 (`ModuleNotFoundError: No module named 'numpy._core'`).

## The checkpoint

`agent/models/sac-halfcheetah-v5-modern.zip` comes from `agent/train.py` (see
[`agent/models/README.md`](agent/models/README.md)). Retrain it with `uv run train.py` from
`stack-conflict/agent`.
