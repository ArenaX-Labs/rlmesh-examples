# Hello Env

A small Gymnasium environment served through RLMesh. The policy walks left or right until it reaches
a target. Use this example as a starting point for your own environment container.

| File           | Purpose                                                             |
| -------------- | ------------------------------------------------------------------- |
| `hello_env.py` | `LineWalk`, the environment, and `HelloEnv`, its factory            |
| `Dockerfile`   | Installs dependencies and serves `hello_env:HelloEnv` on port 50051 |
| `run.py`       | Runs five episodes with a policy that moves toward the target       |

## Run without Docker

From the repo root:

```bash
cd hello-env
RLMESH_ADDRESS=127.0.0.1:50051 uv run python -m rlmesh.serve --env hello_env:HelloEnv
```

Wait for `RLMesh serving env`, then leave the server running. In a second terminal, also from the
repo root:

```bash
cd hello-env
uv run run.py
```

The client prints `episodes=5`, a mean reward, and a step count. Rewards and steps vary because each
episode starts at random positions.

Stop the server with Ctrl-C before running the container below; both use port 50051.

## Build and run the container

From the repo root:

```bash
docker build -t rlmesh-examples/hello-env hello-env
docker run --rm -p 127.0.0.1:50051:50051 rlmesh-examples/hello-env
```

Wait for `RLMesh serving env`, then run `uv run run.py` again from `hello-env/` in the second
terminal. The client code is the same; the environment now runs inside Docker. Stop the container
with Ctrl-C when finished.

## How the factory works

`HelloEnv.make()` returns an environment wrapped in Gymnasium's `TimeLimit`. RLMesh serves the
factory through this Dockerfile command:

```dockerfile
CMD ["python", "-m", "rlmesh.serve", "--env", "hello_env:HelloEnv"]
```

| Factory member         | Purpose                                                                    |
| ---------------------- | -------------------------------------------------------------------------- |
| `workflow_edition`     | Declares the RLMesh behavior the environment was written against           |
| `params`               | Describes construction parameters; defaults live in the `make()` signature |
| `enumerate_variants()` | Publishes named presets, here `short` and `long`                           |
| `make()`               | Creates a Gymnasium-style environment                                      |

To serve a different line size, stop the existing container and pass construction parameters as
JSON:

```bash
docker run --rm -p 127.0.0.1:50051:50051 \
  -e 'RLMESH_MAKE_KWARGS={"size": 50}' rlmesh-examples/hello-env
```

To inspect the factory's description without starting a server:

```bash
docker run --rm rlmesh-examples/hello-env python -m rlmesh._describe --env hello_env:HelloEnv
```

## Make it yours

Replace `LineWalk` with your environment, or return `gym.make(...)` from `make()`. Add its
dependencies to `pyproject.toml` and run `uv lock` in `hello-env/`, then rebuild the image. Keep the
same RLMesh version in the image and the client.

## Run on RLMesh Managed

Use the SDK version required by your deployment. From `hello-env/`, sign in:

```bash
uv run rlmesh login
uv run rlmesh registry login
```

Find your registry host and organization namespace in the Managed dashboard. From the repo root,
build for the Managed architecture, then tag and push the image. Replace `your-namespace` and use
the registry host shown in your dashboard:

```bash
docker build --platform linux/amd64 -t rlmesh-examples/hello-env hello-env
docker tag rlmesh-examples/hello-env registry.rlmesh.dev/your-namespace/hello-env:latest
docker push registry.rlmesh.dev/your-namespace/hello-env:latest
```

Wait for the image's probe to pass under Registry before selecting it for an evaluation. `run.py` is
a local client; it is not a model container to upload.
