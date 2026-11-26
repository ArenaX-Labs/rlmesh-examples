# LIBERO

LIBERO builds each task from a BDDL file on top of robosuite and provides a fixed list of initial
states. This factory adapts its reset and step methods to RLMesh and exposes camera images, robot
state, and an instruction.

Read [`hello-env`](../hello-env/) and [`metaworld`](../metaworld/) first. This example covers
episode limits, trial indices, and simulator assets.

## Files

| File            | What it is                                                                  |
| --------------- | --------------------------------------------------------------------------- |
| `libero_env.py` | `Libero` factory: params, per-task variants, tags, and the LIBERO wrapper   |
| `Dockerfile`    | Python 3.10, OSMesa, `hf-libero` from PyPI, sim assets baked into the image |
| `run.py`        | Random actions; prints the observation a model receives                     |

## What's new compared to metaworld

| Concept             | Implementation                                                                                                                                        |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Gymnasium-style API | Convert robosuite's four step results to five, report `is_success`, and enforce an episode budget.                                                    |
| Reset options       | `reset_options = ("trial_index",)` asks RLMesh to send the trial number on reset. Use it to select an initial state, wrapping at the end of the list. |
| Bundled assets      | Download meshes and textures during the Docker build so a container can start offline.                                                                |
| Task variants       | Read task names and instructions from LIBERO's benchmark table.                                                                                       |

## Run

Hardware: CPU. Docker for the container; OSMesa and a C/C++ toolchain to serve on the host.

```bash
docker build -t rlmesh-examples/libero libero
cd libero
uv run run.py --image rlmesh-examples/libero
```

`--image` starts the image as an `rlmesh.SandboxEnv` and removes the container when the run ends.

```text
agentview_image            (256, 256, 3)
instruction                put both the alphabet soup and the tomato sauce in the basket
robot0_eef_pos             (3,)
robot0_eef_quat            (4,)
robot0_eye_in_hand_image   (256, 256, 3)
robot0_gripper_qpos        (2,)
episodes=2 success_rate=0.00 steps=100
```

The random policy checks the serving path; it is not trained to solve these tasks.

## Picking a task

`task_suite` (default `libero_10`) and `task_id` (default `0`) select the task. `max_episode_steps`
defaults to upstream's budget for the suite (`libero_10`: 520). The full param list is in
`libero_env.py`, or run `docker run --rm rlmesh-examples/libero rlmesh describe libero_env:Libero`.

To select a task, pass its suite and index:

```bash
uv run run.py --image rlmesh-examples/libero \
  --make-kwargs '{"task_suite": "libero_spatial", "task_id": 0}'
```

## Without Docker

Install OSMesa (`libosmesa6` on Debian/Ubuntu, `mesa-libOSMesa` on Fedora) and a C/C++ toolchain
with CMake and Make for `egl-probe` (with CMake 4, also set `CMAKE_POLICY_VERSION_MINIMUM=3.5`).
From the repo root:

```bash
cd libero
uv run --group sim python -c "from libero.libero import get_assets_path; print(get_assets_path())"
MUJOCO_GL=osmesa PYOPENGL_PLATFORM=osmesa RLMESH_ADDRESS=127.0.0.1:7447 \
  uv run --group sim python -m rlmesh.serve --env libero_env:Libero
```

On the first import, answer `N` to LIBERO's custom dataset path prompt. The first command also
downloads the simulator assets. Run `uv run run.py` from `libero/` in a second terminal; the client
installs only `rlmesh`, while the `sim` group holds the simulator.

## About the LIBERO package

This uses [`hf-libero`](https://pypi.org/project/hf-libero/), the Hugging Face–maintained fork that
LeRobot evaluates on. It runs on MuJoCo 3. Benchmark comparisons also depend on the policy, reset
protocol, and episode budget; sharing a simulator version does not establish matching success rates.

The Dockerfile installs a C toolchain because `egl-probe`, a LIBERO dependency, only ships as
source.
