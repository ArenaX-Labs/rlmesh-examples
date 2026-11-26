# Sandbox

Name an env, and RLMesh builds a container for it, starts it, connects, and removes it afterwards:
no Dockerfile and no server terminal.

## Run it

```bash
uv run --directory python/sandbox run.py       # Gymnasium CartPole-v1
uv run --directory python/sandbox run.py hf    # hf://lerobot/cartpole-env, a Hugging Face EnvHub repo
```

Each prints a reward per step and `episode complete`.

## The RLMesh part

A `SandboxEnv` is a remote env whose container RLMesh owns. `SandboxBuild` says what to install and
import inside it ([`run.py`](run.py)):

```python
SOURCES = {
    "gym": ("CartPole-v1", SandboxBuild(packages=["gymnasium==1.3.0"], imports=["gymnasium"])),
    "hf": (
        "hf://lerobot/cartpole-env:cartpole_suite/0",
        SandboxBuild(trust_remote_code=True, allow_unpinned_hf=True),
    ),
}
...
env = SandboxEnv(source, build=build)
obs, info = env.reset(seed=0)
obs, reward, terminated, truncated, info = env.step(env.action_space.sample())
```

The `hf://` selector picks suite `cartpole_suite`, task `0`.

## Needs

CPU and Docker.

## Next

- `SandboxVectorEnv` gives more than one env from the same source.
- `rlmesh.SandboxModel("image://<tag>")` starts a policy in its own container the same way; see
  [`byo-container`](../byo-container/) for building that image.
- The generated image installs the same `rlmesh` version as the host. To test a wheel you built,
  pass `SandboxBuild(rlmesh_package="path/to/rlmesh-....whl")` or set
  `RLMESH_SANDBOX_RLMESH_PACKAGE`; it must load in the container, so build a manylinux wheel.
