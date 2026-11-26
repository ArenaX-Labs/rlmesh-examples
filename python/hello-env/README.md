# Hello Env

A small Gymnasium env served through RLMesh and driven by a hand-written policy: the serve, build
and run loop every other example builds on.

## Run it

```bash
uv run --directory python/hello-env python -m rlmesh.serve --env hello_env:HelloEnv --address 127.0.0.1:7447
uv run --directory python/hello-env run.py    # in a second terminal
```

It prints `episodes=5 mean_reward=0.97 steps=22` (episodes start at random positions, so the numbers
vary). The same env as an image, which RLMesh starts as a sandbox and removes afterwards:

```bash
docker build -t rlmesh-examples/hello-env python/hello-env
uv run --directory python/hello-env run.py --image rlmesh-examples/hello-env
```

## The RLMesh part

`LineWalk` is a plain `gym.Env`. A factory makes it, with its parameters and named presets
([`hello_env.py`](hello_env.py)):

```python
class HelloEnv(rlmesh.EnvFactory):
    params = rlmesh.ParamSpec(
        rlmesh.Param(
            "size", type="int", description="Distance between the endpoints (at least 1)."
        ),
    )

    @classmethod
    def enumerate_variants(cls):
        yield rlmesh.Variant("short", {"size": 5}, name="Short line")
        yield rlmesh.Variant("long", {"size": 50}, name="Long line")

    def make(self, *, size: int = 10) -> gym.Env:
        return gym.wrappers.TimeLimit(LineWalk(size), max_episode_steps=4 * size)
```

The [`Dockerfile`](Dockerfile) serves it with
`CMD ["python", "-m", "rlmesh.serve", "--env", "hello_env:HelloEnv"]`. The client is a function and
one `run` call ([`run.py`](run.py)):

```python
def predict(obs):
    pos, target = obs
    return 1 if target > pos else 0


model = Model(predict)
if args.image:
    with SandboxEnv(f"image://{args.image}") as env:
        result = model.run(env, episodes=args.episodes)
else:
    result = model.run(args.address, episodes=args.episodes)
```

## Needs

CPU. Docker for the image.

## Next

- Make it yours: replace `LineWalk` or return `gym.make(...)` from `make()`, and add its
  dependencies to `pyproject.toml`.
- `RLMESH_MAKE_KWARGS='{"size": 50}'` serves another size;
  `docker run --rm rlmesh-examples/hello-env rlmesh describe hello_env:HelloEnv` prints the params
  and variants.
- Run it on RLMesh Managed: `uv run rlmesh login` and `uv run rlmesh registry login`, build with
  `--platform linux/amd64`, then tag and push `registry.rlmesh.dev/<namespace>/hello-env:latest`.
  Managed sets the address and session key itself; select the image once its probe passes.
- [`byo-container`](../byo-container/): write the Dockerfile and entrypoint yourself, for an env and
  a model.
