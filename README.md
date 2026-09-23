# RLMesh Examples

Examples for running environments locally with RLMesh and packaging them as Docker images. Start
with [`hello-env`](hello-env/): it includes an environment, a Dockerfile, and a policy that runs
against either the local process or the container.

## Build an environment

| Example                    | What it adds                                                                     | Hardware |
| -------------------------- | -------------------------------------------------------------------------------- | -------- |
| [`hello-env/`](hello-env/) | A small Gymnasium env, an `EnvFactory`, and the complete build/run loop          | CPU      |
| [`metaworld/`](metaworld/) | An upstream Gymnasium simulator with camera, state, and instruction observations | CPU      |
| [`libero/`](libero/)       | A non-Gymnasium simulator with fixed initial states and bundled assets           | CPU      |
| [`isaacsim/`](isaacsim/)   | A GPU simulator with a vendor base image and batched environments                | RTX GPU  |

Each example serves an `EnvFactory` through `python -m rlmesh.serve`. The factory's `make()` method
creates the environment; the Dockerfile installs its dependencies and starts the server. The client
in `run.py` connects to that server and runs a policy.

## Setup

Install [`uv`](https://docs.astral.sh/uv/) and Docker to follow the container examples. The MuJoCo
examples also include instructions for serving directly on your host.

Each component has its own `pyproject.toml`, `uv.lock`, and `.venv`. Run `uv` from that component's
directory. There is no root Python project, and the conflict demos deliberately use packages that
cannot share a virtual environment.

The examples currently pin `rlmesh==0.1.0rc15`. Use the same SDK version in the client and
container. When updating it, update the project pins and lockfiles together, including the Isaac Sim
Dockerfile's `RLMESH_VERSION`.

[`mise`](https://mise.jdx.dev/) is optional. Its component configs select Python and activate that
component's `.venv`; run `mise trust` in each directory when prompted. Without it, `uv run` uses the
Python version required by the component's `pyproject.toml`.

Run one example at a time: most servers use port 50051. Commands that start with `cd` assume a fresh
terminal at the repo root. Leave the server running while you use the client in another terminal,
then stop it with Ctrl-C.

## Dependency and interface demos

These demos show why you might separate a model and environment into different processes. They
include evaluation loops and recording code in addition to the serving code.

| Demo                                         | What it shows                                                                                      |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| [`env-stack-conflict/`](env-stack-conflict/) | One policy against Safety-Gymnasium/MuJoCo 2.x and Gymnasium/MuJoCo 3.x, each in its own container |
| [`model-env-conflict/`](model-env-conflict/) | A SAC checkpoint evaluated against a Safety-Gymnasium env with incompatible dependencies           |
| [`interface-mismatch/`](interface-mismatch/) | Adapting `dm_control` time steps and a model that returns chunks of actions                        |

## Run on RLMesh Managed

The environment images use the standard `rlmesh.serve` command, which lets Managed discover their
parameters and variants from the handshake. Keep that command and the `RLMESH_ADDRESS` environment
variable when adapting an example. Isaac Sim also declares GPU and memory requirements in its image
label.

Build for `linux/amd64` when targeting Managed, use the SDK version required by your deployment, and
test the image locally before uploading it. The
[hello-env walkthrough](hello-env/#run-on-rlmesh-managed) shows the tag and push steps. An upload
must pass the Managed probe before it can run there.
