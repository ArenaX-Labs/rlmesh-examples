# Isaac Sim

A Franka Panda reaches a random target on Isaac Sim 6.1, with an RTX camera. This is the batched GPU
example: a vector env, a vendor base image, and a simulator that only works from one thread.

Read [`hello-env`](../../hello-env/) first for the factory → Dockerfile → run loop.

The client uses `Model(predict, spec=rlmesh.NO_ADAPTER)`: its policy reads the environment's keys
and returns the environment's three-value delta action directly. `FrankaReach.tags` describes those
fields for other models, but this client requests no conversion. For a resolved `ModelSpec` that
changes camera, pose, and gripper formats, see [`ur10e-pick-place`](../ur10e-pick-place/).

| File              | What it is                                                                          |
| ----------------- | ----------------------------------------------------------------------------------- |
| `franka_reach.py` | `FrankaReachEnv` (a batched gymnasium `VectorEnv`) behind the `FrankaReach` factory |
| `Dockerfile`      | `nvcr.io/nvidia/isaac-sim:6.1.0` with `rlmesh` pip-installed into Isaac's Python    |
| `run.py`          | A scripted policy that moves the hand straight at the target                        |

## What's new compared to the CPU examples

`prepare()` starts Kit once per process, and `make(lanes=N)` builds N Frankas in one stage. Isaac
Sim needs its calls on the main thread; `rlmesh.serve` runs `prepare()`, `make()` and every env call
there.

At `lanes=1`, RLMesh serves the batched environment as a scalar environment. With multiple lanes, it
steps them together in lockstep. Finished lanes reset on their next step (Gymnasium `NEXT_STEP`),
and the environment enforces `max_steps`. Multi-lane runs accept `episodes=`, but per-episode
`seeds=` and `max_episode_steps=` are only supported with one lane.

The vendor image supplies Python 3.12. The Dockerfile installs RLMesh into that interpreter and uses
`exec` in its entrypoint so shutdown signals reach the server.

Observations are `image` (224×224 RGB), `joint_pos`, `eef_pos` and `target_pos`. The action is a 3-D
hand delta of up to 5 cm per axis; the env solves the arm IK.

## Run

Hardware: an RTX GPU with a driver Isaac Sim 6.1 supports, the NVIDIA container runtime, and about
11 GB of RAM. Assets stream from NVIDIA's S3 at startup, so the container needs network access. The
Dockerfile sets NVIDIA's EULA and privacy-consent variables; review those terms before use.

The container serves on every interface, so it needs a host identity: make one, pass it to the
container, and dial the keyed address it prints.

```bash
docker build -t rlmesh-examples/isaacsim python/isaacsim/franka-reach
cd python/isaacsim/franka-reach
uv run rlmesh host-identity new --out env.identity --address 127.0.0.1:7447 --participant env
# prints address=127.0.0.1:7447#<key>/env
RLMESH_HOST_IDENTITY="$(cat env.identity)" docker run --rm --gpus all --memory=16g \
  -e RLMESH_HOST_IDENTITY -e 'RLMESH_MAKE_KWARGS={"lanes": 4}' \
  -p 127.0.0.1:7447:7447 rlmesh-examples/isaacsim
```

Wait for `RLMesh serving env` in the container logs (about 45 s). Then, in a second terminal:

```bash
cd python/isaacsim/franka-reach
RLMESH_ENV_ADDRESS='127.0.0.1:7447#<key>/env' uv run run.py
```

The client prints the episode count, steps, and success rate. Step counts and success vary with the
sampled targets. `--memory` caps the container, so running out of memory kills the container instead
of your desktop. Stop the container with Ctrl-C when finished.

## Coming from Isaac Lab

| In Isaac Lab                                                                         | Here                                                                                                                                         |
| ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| The env is always batched, even at `num_envs=1`                                      | Same. Write one batched env; RLMesh serves one lane as a scalar env and N lanes in lockstep.                                                 |
| Finished envs reset inside `step()` (`SAME_STEP`); the terminal frame is in `extras` | Hold the reset for the lane's next step (`NEXT_STEP`) and return the real terminal frame, as `step()` does here. RLMesh refuses `SAME_STEP`. |
| The policy gets a batch of observations                                              | `predict()` gets one lane's observation. Override `predict_batch()` for one batched forward pass.                                            |
| `AppLauncher` starts the app in your script                                          | `prepare()` starts it; `make()` builds the scene.                                                                                            |
| Torch tensors on the GPU                                                             | Return numpy, or subclass `rlmesh.torch.EnvFactory` to serve torch values without converting.                                                |

## Run on RLMesh Managed

Push the image as in [hello-env](../../hello-env/#run-on-rlmesh-managed). The `gpu` tag in the
image's `dev.rlmesh.package` label asks RLMesh Managed for a GPU node, and Managed supplies the
address and host identity itself.
