# Meta-World

Serve a Meta-World MT1 task with a camera image, robot state, and language instruction. The wrapper
adds these observations to an upstream Gymnasium environment.

This builds on [`hello-env`](../hello-env/). Read that first for the factory → Dockerfile → run
loop; this one covers what changes when the env is a robot sim.

## Files

| File               | What it is                                                               |
| ------------------ | ------------------------------------------------------------------------ |
| `metaworld_env.py` | `MetaWorld` factory: params, variants, tags, and the observation wrapper |
| `tasks.py`         | The 50 MT1 task names and their language instructions                    |
| `Dockerfile`       | Python 3.10, OSMesa for headless MuJoCo, Meta-World at a pinned git rev  |
| `run.py`           | Random actions; prints the observation a model receives                  |

## What's new compared to hello-env

| Concept               | Where                | Why it matters                                                                            |
| --------------------- | -------------------- | ----------------------------------------------------------------------------------------- |
| Headless rendering    | `Dockerfile`         | `MUJOCO_GL=osmesa` renders without a GPU or display.                                      |
| Dict observations     | `observation_space`  | `image` (HxWx3 uint8), `state` (39-D), `task` (text)                                      |
| `tags`                | `MetaWorld.tags`     | Describe the camera, state, instruction, and action fields for compatible model adapters. |
| Variants from a table | `enumerate_variants` | One variant per MT1 task, each carrying its instruction                                   |
| Pinned upstream       | `pyproject.toml`     | Install the same Meta-World source revision on each build                                 |

## Run

Hardware: CPU. Docker for the container; OSMesa to serve on the host.

```bash
docker build -t rlmesh-examples/metaworld python/metaworld
cd python/metaworld
uv run run.py --image rlmesh-examples/metaworld
```

`--image` starts the image as an `rlmesh.SandboxEnv` and removes the container when the run ends.

```text
image=(256, 256, 3) state=(39,) task='Reach a goal position'
episodes=2 mean_reward=<float> steps=200
```

`run.py` uses `spec=rlmesh.NO_ADAPTER` so you see the env's observation exactly as served. A model
can declare its own spec; RLMesh uses the env's `tags` to resolve supported field mappings. Matching
fields does not make a policy trained for another robot solve the task.

## Picking a task

`env_name` selects the MT1 task (default `reach-v3`). `camera_name` and `image_size` set the camera.
The params are listed in `metaworld_env.py`, or ask the image:

```bash
docker run --rm rlmesh-examples/metaworld rlmesh describe metaworld_env:MetaWorld
```

Pass the task to the factory as JSON:

```bash
uv run run.py --image rlmesh-examples/metaworld --make-kwargs '{"env_name": "push-v3"}'
```

## Without Docker

You need OSMesa on the host (`libosmesa6` on Debian/Ubuntu, `mesa-libOSMesa` on Fedora):

```bash
cd python/metaworld
MUJOCO_GL=osmesa RLMESH_ADDRESS=127.0.0.1:7447 uv run python -m rlmesh.serve --env metaworld_env:MetaWorld
```

Then run `uv run run.py` from `python/metaworld/` in a second terminal. `RLMESH_MAKE_KWARGS` takes
the same JSON as `--make-kwargs` when serving this way.
