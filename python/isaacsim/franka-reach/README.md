# Isaac Sim Franka reach

A batched Isaac Sim 6.1 env: N Franka Pandas in one stage, each reaching a random target with an RTX
camera, served as one vector env that RLMesh steps in lockstep.

## Run it

```bash
docker build -t rlmesh-examples/franka-reach python/isaacsim/franka-reach
uv run --directory python/isaacsim/franka-reach rlmesh host-identity new --out env.identity \
  --address 127.0.0.1:7447 --participant env    # prints address=127.0.0.1:7447#<key>/env
RLMESH_HOST_IDENTITY="$(cat python/isaacsim/franka-reach/env.identity)" docker run --rm --gpus all \
  --memory=16g -e RLMESH_HOST_IDENTITY -e 'RLMESH_MAKE_KWARGS={"lanes": 4}' \
  -p 127.0.0.1:7447:7447 rlmesh-examples/franka-reach
```

Once the container logs `RLMesh serving env` (about 45 s), in a second terminal:

```bash
RLMESH_ENV_ADDRESS='127.0.0.1:7447#<key>/env' uv run --directory python/isaacsim/franka-reach run.py
```

It prints the episode count, steps and success rate. The container serves on every interface, so it
needs the host identity; the keyed address is what the client dials.

## The RLMesh part

`prepare()` starts Kit once per process and `make(lanes=N)` builds the stage; `rlmesh.serve` keeps
both, and every env call, on the main thread Isaac Sim requires
([`franka_reach.py`](franka_reach.py)):

```python
class FrankaReach(rlmesh.EnvFactory):
    def prepare(self):
        from isaacsim import SimulationApp

        ...
        self.app = SimulationApp({"headless": True})

    def make(self, *, lanes=1, image_size=224, max_steps=100):
        ...
        return FrankaReachEnv(self.app, lanes, image_size, max_steps)
```

`FrankaReachEnv` is a `gym.vector.VectorEnv` that resets finished lanes on their next step
(`NEXT_STEP`) and returns the real terminal frame:

```python
def step(self, actions):
    resetting = np.flatnonzero(self.ended)
    self._reset_lanes(resetting)
    delta = np.clip(actions, -MAX_DELTA, MAX_DELTA) / SUBSTEPS
    delta[resetting] = 0.0  # NEXT_STEP discards a resetting lane's action
    ...
    return obs, reward, terminated, truncated, {"is_success": terminated}
```

The client gets one lane's observation per call ([`run.py`](run.py)):

```python
def predict(obs):
    return np.clip(obs["target_pos"] - obs["eef_pos"], -MAX_DELTA, MAX_DELTA).astype(np.float32)


result = Model(predict, spec=rlmesh.NO_ADAPTER).run(args.address, episodes=args.episodes)
```

## Needs

An RTX GPU with a driver Isaac Sim 6.1 supports, Docker with the NVIDIA container runtime, about 11
GB of RAM, and network access (assets stream from NVIDIA at startup). The Dockerfile accepts
NVIDIA's EULA and privacy-consent variables; review those terms before use.

## Next

- **From Isaac Lab:** the env is batched even at one lane (RLMesh serves one lane as a scalar env);
  hold resets for the lane's next step instead of `SAME_STEP`, which RLMesh refuses; `predict()`
  gets one lane, `predict_batch()` all of them; return numpy, or subclass `rlmesh.torch.EnvFactory`
  to serve torch values. Multi-lane runs take `episodes=`; `seeds=` and `max_episode_steps=` need
  one lane.
- **RLMesh Managed:** push the image as in [`hello-env`](../../hello-env/#next). The `gpu` tag in
  the image's `dev.rlmesh.package` label asks Managed for a GPU node.
- [`ur10e-pick-place`](../ur10e-pick-place/): a resolved `ModelSpec` that converts camera, pose and
  gripper formats, where this client takes the env's fields as they are.
