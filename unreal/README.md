# RLmeshSim

Example Unreal Engine **5.6** project for [RLMesh](https://github.com/ArenaX-Labs/rlmesh). It hosts RL envs with the RLMesh plugin and drives them from Python.

**Dependency direction:** this project depends on rlmesh. The plugin does not depend on this project.

## What you get

| Piece | Role |
|-------|------|
| Plugin (from rlmesh) | **Reach Target** + base `URLMeshEnvComponent` |
| This game module | Chase Point, Avoid Hazards, Collect Coins, Demo Arena |
| Python clients | `Scripts/demos/` — plain `rlmesh.numpy.Model` + `rlmesh.run` |
| Optional editor helper | HTTP API on `:8878` to swap environments and Press Play |

## Requirements

- Unreal Engine **5.6**
- [rlmesh](https://github.com/ArenaX-Labs/rlmesh) checkout (or matching release artifacts):
  - Plugin: `integrations/unreal/RLMesh` + unpacked ThirdParty `rlmesh_capi`
  - Python: `mise run setup:python` (or the checkout `.venv`)
- Editor **Python Script Plugin** (enabled in this `.uproject`)

## Setup

1. Clone this repo and clone/build [rlmesh](https://github.com/ArenaX-Labs/rlmesh).
2. Install the plugin into `Plugins/RLMesh/` (copy or junction from rlmesh `integrations/unreal/RLMesh`).
3. Unpack matching `rlmesh_capi` under `Plugins/RLMesh/Source/ThirdParty/rlmesh/` (see rlmesh `docs/unreal-local.md`).
4. Generate project files, open, build.
5. Optional stable Serving `#keys` (once per machine):

   ```bash
   rlmesh host-identity new --out "%LOCALAPPDATA%/rlmesh/unreal_host_identity"
   ```

## Run demos

Use a Python that has the `rlmesh` package (rlmesh `.venv` recommended). Copy the Serving address from LogRLMesh after Play (or pass it via `--address` / `RLMESH_UNREAL_ADDR`).

**Reach Target** (plugin component; client in rlmesh):

```powershell
python Scripts/demo_client.py ensure reach_target
<path-to-rlmesh>\.venv\Scripts\python.exe integrations/unreal/demos/reach_target/toward_target.py "127.0.0.1:7447#<key>/env"
```

**Chase / Avoid / Collect / Demo Arena** (components + clients in this project):

```powershell
# From RLmeshSim root — use the rlmesh venv python
<path-to-rlmesh>\.venv\Scripts\python.exe Scripts/demos/chase_point/app.py --verbose --address "127.0.0.1:7447#<key>/env"
<path-to-rlmesh>\.venv\Scripts\python.exe Scripts/demos/avoid_hazards/app.py --verbose --address "…"
<path-to-rlmesh>\.venv\Scripts\python.exe Scripts/demos/collect_coins/app.py --verbose --address "…"
<path-to-rlmesh>\.venv\Scripts\python.exe Scripts/demos/demo_arena/app.py --verbose --address "…"
```

Each `app.py` calls the optional `:8878` helper unless you pass `--no-ensure` (then Press Play yourself).

## Layout

| Path | Role |
|------|------|
| `Content/` | Maps, materials, prop Blueprints |
| `Source/RLmeshSim/` | Game module: demo actors + Chase/Avoid/Collect/Demo Arena components |
| `Scripts/demo_control_server.py` | Optional in-editor load/play HTTP API |
| `Scripts/demo_client.py` | CLI for that API |
| `Scripts/envs/` | Environment swap |
| `Scripts/demos/` | Python `Model` + `rlmesh.run` clients |
| `Plugins/RLMesh/` | From rlmesh (gitignored when junctioned) |

## Notes

- Keep one Serving env active at a time.
- Source the plugin from rlmesh so this sample stays a consumer.
- Licensed dual MIT / Apache-2.0. See `LICENSE-MIT` and `LICENSE-APACHE`.
