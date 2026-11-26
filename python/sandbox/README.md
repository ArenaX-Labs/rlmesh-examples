# Sandbox Examples

These examples start an owned Docker-backed environment and connect to it like any other RLMesh
remote environment. They do not need a separate `EnvServer` terminal.

Hardware: CPU and Docker. Run commands from `python/sandbox/`.

## Gymnasium Sandbox

Start here. It builds a sandbox for Gymnasium `CartPole-v1`, samples actions, and stops the
container when the script exits.

```bash
uv run gym_sandbox.py
```

The script passes `build=SandboxBuild(packages=["gymnasium==1.3.0"], imports=["gymnasium"])` so the
dependency is installed and checked inside the sandbox.

## Hugging Face Sandbox

`hf_sandbox.py` shows the single-env client loop for a Hugging Face EnvHub source:

```bash
uv run hf_sandbox.py
```

It uses `hf://lerobot/cartpole-env:cartpole_suite/0`. The selector chooses suite `cartpole_suite`,
task `0`.

The example uses `SandboxEnv` because it requests one environment. Use `SandboxVectorEnv` when you
want more than one environment from the same source.

## Model Drives Env

`rlmesh.SandboxModel("image://<tag>")` is the managed sibling of `rlmesh.Model(address)`: it starts
the policy in its own container, which hosts a session, and its `run(env)` and `bind(env)` drive it
there, serving a local env in that session. The policy executes in its own container, not in your
process. The model container is a prebuilt image you build yourself with rlmesh 0.2 -- see
[`byo-container`](../byo-container/) for the Dockerfile and entrypoint:

```python
import rlmesh

with rlmesh.SandboxModel("image://my-model:latest") as model:
    result = model.run(my_env, episodes=4)
```

## Which rlmesh the sandbox installs

The generated image installs the same `rlmesh` version from PyPI as the host that builds it, so the
two always talk. To test a wheel you built yourself, pass its path:
`build=SandboxBuild(rlmesh_package="path/to/rlmesh-....whl")`, or set
`RLMESH_SANDBOX_RLMESH_PACKAGE`. It must load in the container, so build a manylinux wheel rather
than one for a newer host glibc.
