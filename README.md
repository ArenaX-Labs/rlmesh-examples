# RLMesh Conflict Demos

Small demos where RLMesh keeps incompatible or non-standard RL pieces in separate Python processes.

## TL;DR

- Each component is its own `uv` project.
- Components depend on the published `rlmesh` package.
- Agents use a Gymnasium-style remote API.

## Demos

| Demo               | Open                                         | Terminals | Shows                                                                               |
| ------------------ | -------------------------------------------- | --------: | ----------------------------------------------------------------------------------- |
| Env stack conflict | [`env-stack-conflict/`](env-stack-conflict/) |         3 | One policy against Safety-Gymnasium/MuJoCo 2.x and Gymnasium/MuJoCo 3.x.            |
| Model-env conflict | [`model-env-conflict/`](model-env-conflict/) |         2 | A modern SAC checkpoint against a Safety-Gymnasium env it cannot share a venv with. |
| DMControl VLA      | [`dmcontrol-vla/`](dmcontrol-vla/)           |         2 | A `dm_control` env and chunked VLA-style model behind RLMesh adapters.              |

## Why RLMesh

Some demos hit resolver conflicts: no single Python environment can satisfy every Python, NumPy,
Gymnasium, MuJoCo, Safety-Gymnasium, Torch, and Stable-Baselines3 pin.

Other demos hit API mismatch: a useful environment or model does not speak the interface a platform
can drive directly.

RLMesh changes the boundary:

| Component              | Owns                                              | Python |
| ---------------------- | ------------------------------------------------- | ------ |
| Safety simulator       | Safety-Gymnasium, Gymnasium 0.28.1, MuJoCo 2.3.3  | 3.10   |
| Modern simulator/model | Gymnasium/MuJoCo 3.x or modern SB3/SAC            | 3.11   |
| Agent                  | `rlmesh`, policy code, rollout/reporting          | 3.11   |
| Interface wrapper demo | `dm_control`, Torch VLA stand-in, RLMesh wrappers | 3.11   |

The conflict or mismatch remains real. It just stops blocking evaluation.

## Setup

Run `uv` from inside each component folder. There is no root `uv` project, so each demo keeps its
own `.venv` and lockfile.

`mise` is optional. It only selects Python versions:

| Location                         | Python |
| -------------------------------- | ------ |
| Safety-Gymnasium folders, proof  | 3.10   |
| Agent, modern sim, DMControl sim | 3.11   |

With `mise`, trust configs once if prompted:

```bash
mise trust
```

Without `mise`, pass Python explicitly in 3.10 folders:

```bash
uv run --python 3.10 serve.py
```

## RLMesh Package

The demos install `rlmesh` from the published package.

## Run

Start with one demo README:

- [`env-stack-conflict/README.md`](env-stack-conflict/)
- [`model-env-conflict/README.md`](model-env-conflict/)
- [`dmcontrol-vla/README.md`](dmcontrol-vla/)

First run creates that component's `.venv`; later runs reuse it.

## Repo Layout

```text
env-stack-conflict/
  agent/
  sim-modern/
  sim-safety/

dmcontrol-vla/
  agent/
  sim-dmcontrol/

model-env-conflict/
  agent/
  sim-safety/
  proof/
```
