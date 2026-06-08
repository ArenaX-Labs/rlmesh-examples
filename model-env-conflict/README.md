# Model-Env Conflict

A pretrained SAC agent evaluates a safety env it cannot share a venv with.

## Motivation

At a glance this looks like [`env-stack-conflict`](../env-stack-conflict/): one model, two
environments. The difference is **what conflicts**. There the two *environments* couldn't share a
venv. Here the conflict is between the **model and an environment**.

We trained a Stable-Baselines3 SAC model on a modern `HalfCheetah-v5`, which is why that environment
runs locally in the agent process, since the model already lives in that stack. The environment we
actually care about evaluating is the conflicting one: `SafetyHalfCheetahVelocity-v1`, which requires
an older Python and NumPy that the trained model cannot run under. Porting a Stable-Baselines3
checkpoint back to that older stack is a real headache, so without RLMesh you simply can't evaluate
this model on this environment. RLMesh removes that wall: the model stays where it works and drives
the safety env remotely.

So strictly speaking, the local `HalfCheetah-v5` run isn't required. We only *need* the remote
safety env to make the point. We evaluate on both just to show the model still runs against its
training environment too.

## At A Glance

| Piece        | Stack                                                                    | Address / Role     |
| ------------ | ------------------------------------------------------------------------ | ------------------ |
| `sim-safety` | Safety-Gymnasium 1.0.0, Gymnasium 0.28.1, MuJoCo 2.3.3, Python 3.10      | `5557`             |
| `agent`      | Stable-Baselines3 SAC, Torch, Gymnasium/MuJoCo modern stack, Python 3.11 | connects to `5557` |
| `proof`      | Safety-compatible SB3 stack that tries to load the modern checkpoint     | none               |

One SAC checkpoint runs in two places:

| Environment                    | Where It Runs         | Why                                                      |
| ------------------------------ | --------------------- | -------------------------------------------------------- |
| `HalfCheetah-v5`               | local agent process   | Baseline from the modern stack the model was trained on. |
| `SafetyHalfCheetahVelocity-v1` | remote safety process | Safety stack the model cannot share a venv with.         |

## What RLMesh Changes

The model stack and safety env stack stay separate:

```text
sim-safety (:5557)              agent/eval.py
Python 3.10                     Python 3.11
Safety-Gymnasium                Stable-Baselines3 SAC
Gymnasium 0.28.1                modern Gymnasium/MuJoCo
MuJoCo 2.3.3                    model.predict()
        --------------------->  RemoteEnv(:5557)
```

The agent loads the checkpoint where it works, then drives the safety env over RLMesh.

This is the model-vs-env sibling of [`env-stack-conflict`](../env-stack-conflict/): same idea, but
the model stack is real.

## Run

Open two terminals from the repo root.

### Terminal 1

```bash
cd model-env-conflict/sim-safety
uv run serve.py
```

### Terminal 2

```bash
cd model-env-conflict/agent
uv run eval.py
```

The SAC checkpoint is included. First run creates each `.venv`; later runs reuse it.

No `mise`? Start the safety server with Python 3.10 explicitly:

```bash
cd model-env-conflict/sim-safety
uv run --python 3.10 serve.py
```

## Expected Output

The agent evaluates one policy locally, then remotely:

```text
=== one pretrained SAC policy, two stacks it cannot share a venv with ===
policy: sac-halfcheetah-v5-modern.zip
modern-halfcheetah-v5        steps= 100 return=<float> cost=   0.0
safety-halfcheetah-velocity  steps= 100 return=<float> cost=<float>
```

Read it as:

| Signal                 | Meaning                                                                  |
| ---------------------- | ------------------------------------------------------------------------ |
| Same policy            | The checkpoint loads once in the modern agent stack.                     |
| Remote safety result   | The agent evaluates the safety env without installing it locally.        |
| Non-zero safety `cost` | The safety stack measures a constraint the training env does not expose. |

Results go to `agent/results.json`. Recording is on by default and writes `agent/videos/`.

## Why One Python Fails

Two blockers matter:

| Wall            | What Happens                                                                                 |
| --------------- | -------------------------------------------------------------------------------------------- |
| Install wall    | Modern Stable-Baselines3 requires newer Gymnasium than Safety-Gymnasium 1.0.0 allows.        |
| Checkpoint wall | The older SB3 stack that fits beside Safety-Gymnasium cannot load this NumPy 2.x checkpoint. |

<details>
<summary>Show the install conflict</summary>

```text
$ uv pip compile  (python 3.11)  <<<  "stable-baselines3>=2.7" + "safety-gymnasium==1.0.0"
  x No solution found:
    stable-baselines3>=2.7.0 depends on gymnasium>=0.29.1,<1.3.0
    and safety-gymnasium==1.0.0 depends on gymnasium==0.28.1
```

</details>

<details>
<summary>Show the checkpoint conflict</summary>

The safety-compatible stack resolves to NumPy 1.23.5. The checkpoint was saved with NumPy 2.x, so
loading fails with:

```text
ModuleNotFoundError: No module named 'numpy._core'
```

Run the proof:

```bash
cd model-env-conflict/proof
uv run prove.py
```

Exit 0 means the expected failure happened.

</details>

## The Model

Included checkpoint:

```text
agent/models/sac-halfcheetah-v5-modern.zip
```

It is generated by `agent/train.py` with Stable-Baselines3 SAC on `HalfCheetah-v5`. See
`agent/models/README.md`.

Retrain it with:

```bash
cd model-env-conflict/agent
uv run train.py
```

## Safety Cost

Safety-Gymnasium's native `step` returns `cost`. The server stores it in `info["cost"]`; RLMesh
forwards `info` unchanged.

## Recording

| Setting          | Effect                                   |
| ---------------- | ---------------------------------------- |
| `RECORD = True`  | Default. Save one video per environment. |
| `RECORD = False` | Faster run with no video output.         |

Change the setting at the top of `agent/eval.py`.

## RLMesh Package

This demo depends on the published `rlmesh` package.

## Troubleshooting

| Symptom                                            | Fix                                                         |
| -------------------------------------------------- | ----------------------------------------------------------- |
| `mise.toml` is not trusted                         | Run `mise trust` in that folder.                            |
| Python 3.11 is selected in `sim-safety` or `proof` | Run the command with `uv run --python 3.10`.                |
| Missing checkpoint                                 | Run `cd model-env-conflict/agent && uv run train.py`.       |
| Need RLMesh traffic logs                           | Run the safety server with `RUST_LOG=info uv run serve.py`. |
