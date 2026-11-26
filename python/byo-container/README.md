# Bring your own container

Hand-written env and model images: you own the Dockerfile and a small entrypoint, RLMesh runs the
image, locally as a sandbox or on RLMesh Managed.

## Run it

```bash
for part in env model; do docker build -t my-$part:latest python/byo-container/$part; done
uv run --directory python/byo-container run.py
```

It runs the model image against the env image and prints `episodes=2 steps=20`.

## The RLMesh part

The env image serves a factory ([`env/entrypoint.py`](env/entrypoint.py)):

```python
class MyEnv(EnvFactory):
    def make(self, **kwargs: object) -> gym.Env:
        return gym.make("CartPole-v1")


def main() -> None:
    address = os.environ.get("RLMESH_ADDRESS", "0.0.0.0:7447")
    name = os.environ.get("RLMESH_NAME", "env")
    MyEnv().serve(f"{address}/{name}")
```

The model image serves a policy ([`model/entrypoint.py`](model/entrypoint.py)):

```python
class MyPolicy(Model):
    def load(self) -> None:
        self.bias = 0

    def predict(self, observation: object) -> int:
        return self.bias


serve_model(MyPolicy, address, name=name)
```

and [`run.py`](run.py) starts both and runs one against the other:

```python
with (
    rlmesh.SandboxEnv(f"image://{args.env_image}") as env,
    rlmesh.SandboxModel(f"image://{args.model_image}") as model,
):
    result = model.run(env, episodes=args.episodes)
```

`SandboxModel(...).run(env)` also takes a local env, served beside the model, and `model.bind(env)`
steps it by hand.

## Needs

CPU and Docker.

## Next

- **Run the container yourself.** Listening beyond loopback, as `0.0.0.0` in a container does, a
  session host starts only under a host identity its launcher makes. `rlmesh host-identity new`
  prints one and the keyed address to dial; pass the identity through the environment (it is a
  secret), never argv:

  ```bash
  uv run --directory python/byo-container rlmesh host-identity new --out model.identity \
    --address 127.0.0.1:7447 --participant model    # prints address=127.0.0.1:7447#<key>/model
  RLMESH_HOST_IDENTITY="$(cat python/byo-container/model.identity)" \
    docker run --rm -e RLMESH_HOST_IDENTITY -p 7447:7447 my-model:latest
  ```

  Then `rlmesh.Model("127.0.0.1:7447#<key>/model").run(MyLocalEnv(), episodes=1)`, or
  `rlmesh.RemoteEnv(address)` for an env. From another machine, dial the same key at an address that
  reaches the published port. In Python, `rlmesh.launch` makes the identity and address.

- **Health.** Each image sets `RLMESH_READY_FILE`. The file
  (`{"kind", "participant", "address", "port", "pid"}`) appears once the server answers and goes
  away when it stops, so `docker ps` shows the container healthy and a launcher can wait on it.
- **Wire contract.** A session host listens on one TCP port (7447 here) that every participant
  dials; a container serves as `RLMESH_NAME` on `RLMESH_ADDRESS`. A sandbox publishes the
  container's port to the same number on loopback, so an address means the same inside and out.
- **Versions.** Pin the same `rlmesh` in each Dockerfile (`RLMESH_VERSION`) as the host that drives
  it: builds talk when their session wire revisions match, and a sandbox refuses an image built with
  rlmesh 0.1.
