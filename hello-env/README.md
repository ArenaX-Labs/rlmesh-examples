# Hello Env

A small Gymnasium environment served through RLMesh. The policy walks left or right until it reaches
a target. Use this example as a starting point for your own environment container.

| File           | Purpose                                                            |
| -------------- | ------------------------------------------------------------------ |
| `hello_env.py` | `LineWalk`, the environment, and `HelloEnv`, its factory           |
| `Dockerfile`   | Installs dependencies and serves `hello_env:HelloEnv` on port 7447 |
| `run.py`       | Runs five episodes with a policy that moves toward the target      |

Hardware: CPU. Docker for the container steps.

## Run without Docker

```bash
cd hello-env
RLMESH_ADDRESS=127.0.0.1:7447 uv run python -m rlmesh.serve --env hello_env:HelloEnv
```

Wait for `RLMesh serving env`, then leave the server running. In a second terminal:

```bash
cd hello-env
uv run run.py
```

The client prints `episodes=5`, a mean reward, and a step count. Rewards and steps vary because each
episode starts at random positions. Stop the server with Ctrl-C.

## Build and run the container

```bash
docker build -t rlmesh-examples/hello-env hello-env
cd hello-env
uv run run.py --image rlmesh-examples/hello-env
```

`--image` starts the image as an `rlmesh.SandboxEnv`: RLMesh runs the container, gives it a session
key, connects to it, and removes it when the run ends. The policy is the same; the environment now
runs inside Docker. To start the container yourself instead, see
[running the container yourself](../byo-container/#running-the-container-yourself).

## How the factory works

`HelloEnv.make()` returns an environment wrapped in Gymnasium's `TimeLimit`. RLMesh serves the
factory through this Dockerfile command:

```dockerfile
CMD ["python", "-m", "rlmesh.serve", "--env", "hello_env:HelloEnv"]
```

| Factory member         | Purpose                                                                    |
| ---------------------- | -------------------------------------------------------------------------- |
| `params`               | Describes construction parameters; defaults live in the `make()` signature |
| `enumerate_variants()` | Publishes named presets, here `short` and `long`                           |
| `make()`               | Creates a Gymnasium-style environment                                      |

To serve a different line size, pass construction parameters as JSON:

```bash
RLMESH_MAKE_KWARGS='{"size": 50}' RLMESH_ADDRESS=127.0.0.1:7447 \
  uv run python -m rlmesh.serve --env hello_env:HelloEnv
```

To inspect the factory's description without starting a server:

```bash
docker run --rm rlmesh-examples/hello-env rlmesh describe hello_env:HelloEnv
```

## Make it yours

Replace `LineWalk` with your environment, or return `gym.make(...)` from `make()`. Add its
dependencies to `pyproject.toml` and rebuild the image. Keep the same RLMesh version in the image
and the client.

## Run on RLMesh Managed

Sign in from `hello-env/`:

```bash
uv run rlmesh login
uv run rlmesh registry login
```

Build for the Managed architecture, then tag and push the image under your organization's namespace
(shown in the Managed dashboard):

```bash
docker build --platform linux/amd64 -t rlmesh-examples/hello-env hello-env
docker tag rlmesh-examples/hello-env registry.rlmesh.dev/your-namespace/hello-env:latest
docker push registry.rlmesh.dev/your-namespace/hello-env:latest
```

Managed sets `RLMESH_ADDRESS` and the session key itself. Wait for the image's probe to pass under
Registry before selecting it for an evaluation. `run.py` is a local client, not a model image.
