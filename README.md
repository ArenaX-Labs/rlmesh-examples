# RLMesh Conflict Demos

Real examples where RL models, environments, and simulators cannot live in the
same Python environment, but can still work together through RLMesh.

## TL;DR

- Each demo is split into small `uv` projects with their own virtualenv.
- The conflicting simulator/model stacks never import each other.
- The agent talks to remote environments through RLMesh using a Gymnasium-style
  API.

## Demos

| Demo | Open | Terminals | Shows |
| --- | --- | ---: | --- |
| Env stack conflict | [`env-stack-conflict/`](env-stack-conflict/) | 3 | One policy evaluated against Safety-Gymnasium/MuJoCo 2.x and Gymnasium/MuJoCo 3.x. |
| Model-env conflict | [`model-env-conflict/`](model-env-conflict/) | 2 | A modern SAC checkpoint evaluated on a Safety-Gymnasium env it cannot be installed beside. |

## Why RLMesh

Without RLMesh, these demos are packaging dead ends. A resolver has to find one
Python environment that satisfies every Python, NumPy, Gymnasium, MuJoCo,
Safety-Gymnasium, Torch, and Stable-Baselines3 pin. For these demos, that
environment does not exist.

RLMesh changes the boundary:

| Component | Owns | Python |
| --- | --- | --- |
| Safety simulator | Safety-Gymnasium, Gymnasium 0.28.1, MuJoCo 2.3.3 | 3.10 |
| Modern simulator/model | Gymnasium/MuJoCo 3.x or modern SB3/SAC | 3.11 |
| Agent | `rlmesh`, policy code, rollout/reporting | 3.11 |

The dependency conflict is still real. It just stops blocking evaluation.

## Setup

Install `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

This repo uses `mise.toml` to make the Python split visible:

| Location | Python |
| --- | --- |
| Repo root | 3.11 |
| Safety-Gymnasium folders | 3.10 |

If `mise` asks to trust a config, run:

```bash
mise trust
```

If you do not use `mise`, `uv` can still run the projects from their
`pyproject.toml` files. For a Python 3.10 safety folder, use:

```bash
uv run --python 3.10 serve.py
```

## Local RLMesh Checkout

This repo currently installs RLMesh from the sibling local checkout:

```text
~/work/rlmesh/python/rlmesh
```

That is intentional for local development. To use the published package instead,
remove the component `[tool.uv.sources]` entries and depend on the released
`rlmesh` package.

## Run

Start with one demo README:

- [`env-stack-conflict/README.md`](env-stack-conflict/)
- [`model-env-conflict/README.md`](model-env-conflict/)

The first `uv run` in each component creates that component's `.venv` and
installs its stack. Later runs reuse it.

## Repo Layout

```text
env-stack-conflict/
  agent/
  sim-modern/
  sim-safety/

model-env-conflict/
  agent/
  sim-safety/
  proof/
```
