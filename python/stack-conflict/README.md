# Stack conflict

A pretrained SAC policy evaluated on a Safety-Gymnasium env it cannot share a Python environment
with: each side keeps its own stack, and RLMesh carries observations and actions between them.

## Run it

```bash
docker build -t rlmesh-examples/stack-conflict-safety python/stack-conflict/sim-safety
uv run --directory python/stack-conflict/agent run.py --image rlmesh-examples/stack-conflict-safety
```

```text
modern-halfcheetah-v5        steps= 100 return=   310.7 cost=   0.0
safety-halfcheetah-velocity  steps= 100 return=   327.7 cost=  63.0
```

The checkpoint loads once, in the stack it was trained on, and runs `HalfCheetah-v5` locally and the
safety env remotely. The two tasks differ, so the returns do not isolate simulator drift; only
Safety-Gymnasium reports a constraint `cost`.

## The RLMesh part

The safety side is a factory in Python 3.10 with Gymnasium 0.28 and MuJoCo 2.3
([`sim-safety/env.py`](sim-safety/env.py)):

```python
class HalfCheetahSafety(rlmesh.EnvFactory):
    def make(self):
        env = safety_gymnasium.make("SafetyHalfCheetahVelocity-v1", render_mode="rgb_array")
        return SafetyGymnasium2Gymnasium(env)
```

The agent, in Python 3.11 with Gymnasium 1.x, MuJoCo 3 and NumPy 2, steps the remote env like a
local one ([`agent/run.py`](agent/run.py)):

```python
model = SAC.load(CHECKPOINT, device="cpu")
with gym.make("HalfCheetah-v5") as env:
    print(f"modern-halfcheetah-v5        {rollout(env, model, **run)}")
remote = SandboxEnv(f"image://{args.image}") if args.image else RemoteEnv(args.address)
with remote as env:
    print(f"safety-halfcheetah-velocity  {rollout(env, model, **run)}")
```

One Python cannot hold both:

```text
$ uv pip install "stable-baselines3>=2.7" "safety-gymnasium==1.0.0"
  x No solution found:
    stable-baselines3>=2.7.0 depends on gymnasium>=0.29.1,<1.3.0
    and safety-gymnasium==1.0.0 depends on gymnasium==0.28.1
```

and the older SB3 that fits beside Safety-Gymnasium resolves to NumPy 1.23.5, which cannot load a
checkpoint saved with NumPy 2.

## Needs

CPU. Docker for the image.

## Next

- Serve the safety env on the host instead, with EGL or OSMesa for MuJoCo's renderer:
  `MUJOCO_GL=egl uv run --directory python/stack-conflict/sim-safety python -m rlmesh.serve --env env:HalfCheetahSafety --address 127.0.0.1:7447`,
  then `uv run --directory python/stack-conflict/agent run.py`.
- The checkpoint comes from [`agent/train.py`](agent/train.py) (see
  [`agent/models/README.md`](agent/models/README.md));
  `uv run --directory python/stack-conflict/agent train.py` retrains it.
