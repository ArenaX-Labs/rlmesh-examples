# Env Stack Conflict

One policy, two incompatible simulator stacks.

## At A Glance

| Piece | Stack | Address / Role |
| --- | --- | --- |
| `sim-safety` | Safety-Gymnasium 1.0.0, Gymnasium 0.28.1, MuJoCo 2.3.3, Python 3.10 | `5555` |
| `sim-modern` | Gymnasium/MuJoCo modern stack, Python 3.11 | `5556` |
| `agent` | `rlmesh` + NumPy, Python 3.11 | connects to both |

Both environments expose the same HalfCheetah-shaped interface:

```text
observation: Box(17)
action:      Box(6)
```

The policy can drive both environments. The packages cannot coexist in one
Python environment.

## What RLMesh Changes

RLMesh moves the simulator boundary out of the agent process:

```text
sim-safety (:5555)        sim-modern (:5556)
Python 3.10               Python 3.11
Safety/MuJoCo 2.x         Gymnasium/MuJoCo 3.x
       \                  /
        \                /
         agent/eval.py
         one policy, two RemoteEnv objects
```

The servers keep their incompatible dependencies isolated. The agent imports
`rlmesh`, connects to both servers, and steps them like ordinary environments.

## Run

Open three terminals from the repo root.

### Terminal 1

```bash
cd env-stack-conflict/sim-safety
uv run serve.py
```

### Terminal 2

```bash
cd env-stack-conflict/sim-modern
uv run serve.py
```

### Terminal 3

```bash
cd env-stack-conflict/agent
uv run eval.py
```

> [!TIP]
> The first run in each folder creates that folder's `.venv`. If `mise` asks to
> trust a config, run `mise trust` in that folder once.

No `mise`? Start the safety server with Python 3.10 explicitly:

```bash
cd env-stack-conflict/sim-safety
uv run --python 3.10 serve.py
```

## Expected Output

The agent runs one policy against both environments in lockstep:

```text
=== one policy, two simulator stacks ===
safety/mujoco2.3   obs=(17,) steps=500 return=<float> cost=<float>
modern/mujoco3.3   obs=(17,) steps=500 return=<float> cost=0.0
```

Read it as:

| Signal | Meaning |
| --- | --- |
| Same `obs` shape | One policy can drive both envs. |
| Different returns | Simulator/version drift can be measured side by side. |
| Safety `cost` only | Safety-Gymnasium reports constraint cost; plain `HalfCheetah-v5` does not. |

The agent also writes `agent/results.json`.

## Why One Python Fails

Safety-Gymnasium 1.0.0 pins the old stack:

| Package | Required By Safety-Gymnasium |
| --- | --- |
| Gymnasium | `0.28.1` |
| MuJoCo | `2.3.3` |
| Python | effectively 3.10 because of `pygame==2.1.0` |

The modern simulator uses newer Gymnasium/MuJoCo. There is no single resolver
answer that satisfies both.

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

| Setting | Effect |
| --- | --- |
| `RECORD = True` | Save mp4s under `agent/videos/`. |
| `WATCH = True` | Open live viewer windows with `RemoteEnv.open_viewer()`. |

## Local RLMesh Checkout

This checkout installs RLMesh from:

```text
../../../rlmesh/python/rlmesh
```

From this workspace, that resolves to `~/work/rlmesh/python/rlmesh`.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `mise.toml` is not trusted | Run `mise trust` in that folder. |
| Python 3.11 is selected in `sim-safety` | Run `uv run --python 3.10 serve.py`. |
| Editor imports use the wrong venv | Open the component folder as the editor root. |
| Need RLMesh traffic logs | Run a server with `RUST_LOG=info uv run serve.py`. |
