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
| Interface mismatch | [`interface-mismatch/`](interface-mismatch/) |         2 | A `dm_control` env and chunked VLA-style model behind RLMesh adapters.              |

## Why RLMesh

RLMesh lets RL components that can't share a process run side by side and talk over a common remote
API. Two recurring problems it solves:

- **Dependency conflicts:** no single Python environment can satisfy every pin, so two components
  can't be installed together.
- **API mismatch:** a useful environment or model doesn't speak the interface a platform can drive
  directly.

RLMesh changes the boundary: each component keeps its own environment and process, and RLMesh
bridges them.

The demos in this repo are concrete instances of these problems (incompatible simulator stacks, a
modern checkpoint that can't coexist with an older env, a non-standard environment interface), but
the pattern applies to any RL components with incompatible or non-standard pieces.

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
- [`interface-mismatch/README.md`](interface-mismatch/)

First run creates that component's `.venv`; later runs reuse it.

## Repo Layout

```text
env-stack-conflict/
  agent/
  sim-modern/
  sim-safety/

interface-mismatch/
  agent/
  sim-dmcontrol/

model-env-conflict/
  agent/
  sim-safety/
  proof/
```
