# RLmeshSim

Example Unreal Engine **5.6** project for [RLMesh](https://github.com/ArenaX-Labs/rlmesh). It shows how to host RL envs inside Unreal with the RLMesh plugin and drive them from Python.

**Dependency direction:** this project depends on rlmesh. The plugin does not depend on this project.

## What you get

| Piece | Role |
|-------|------|
| Four plugin env hosts | Reach Target, Chase Point, Avoid Hazards, Collect Coins (plugin components on demo actors) |
| Demo Arena | Authored map `/Game/GameScene_Demo` + game-module component (this sample only) |
| Optional editor helper | HTTP API on `:8878` to swap environments and Press Play while iterating |

## Requirements

- Unreal Engine **5.6**
- [rlmesh](https://github.com/ArenaX-Labs/rlmesh) checkout (or matching release artifacts):
  - Plugin: `integrations/unreal/RLMesh` + unpacked ThirdParty `rlmesh_capi`
  - Python: `mise run setup:python` in the rlmesh checkout
- Editor **Python Script Plugin** (enabled in this `.uproject`)

## Setup

1. Clone this repo and clone/build [rlmesh](https://github.com/ArenaX-Labs/rlmesh).
2. Install the plugin into `Plugins/RLMesh/` (copy or directory junction from rlmesh `integrations/unreal/RLMesh`).
3. Unpack the matching `rlmesh_capi` package under `Plugins/RLMesh/Source/ThirdParty/rlmesh/` (see rlmesh [`docs/unreal-local.md`](https://github.com/ArenaX-Labs/rlmesh/blob/main/docs/unreal-local.md)).
4. Right-click `RLmeshSim.uproject` → **Generate Visual Studio project files**, then open and build if prompted.
5. Once per machine, from the **rlmesh** checkout:

   ```bash
   python integrations/unreal/demos/reach_target/app.py --init-identity
   ```

   Rebuild or relaunch the editor so LogRLMesh shows `Loaded RLMESH_HOST_IDENTITY`.

## Quick start

1. Open this project. Default map is `/Game/GameScene`. On Play with an empty level, the game mode spawns a Reach Target host so Serving starts immediately.
2. From the **rlmesh** checkout (editor Playing, LogRLMesh shows Serving):

   ```bash
   python integrations/unreal/demos/reach_target/app.py --verbose
   ```

   Use `RLMESH_UNREAL_ADDR` from rlmesh `integrations/unreal/.env`, or pass `--address` from the Serving line in the log.

Other portable clients (same pattern — Press Play with that env Serving first):

```bash
python integrations/unreal/demos/chase_point/app.py --verbose
python integrations/unreal/demos/avoid_hazards/app.py --verbose
python integrations/unreal/demos/collect_coins/app.py --verbose
```

## Switching environments in the editor (optional)

This sample auto-starts a small HTTP helper on `http://127.0.0.1:8878` so you can swap hosts/maps without placing actors by hand:

```bash
python Scripts/demo_client.py list
python Scripts/demo_client.py ensure chase_point
python Scripts/demo_client.py ensure demo_arena
```

Or in the editor Python console (`Scripts/` on `sys.path`):

```python
from envs import activate
activate("chase_point")
```

rlmesh suite clients do **not** call this API — they only need Serving + an address.

## Demo Arena (sample-only)

Level-driven showcase on `/Game/GameScene_Demo` (`URLMeshDemoArenaComponent` in this game module). Bind actors by Outliner label / tag prefix `Goal*`, `Coin*`, `Obstacle*` / `Hazard*`.

```bash
# Editor open; helper loads the arena map and Plays:
python Scripts/demos/demo_arena/app.py --verbose

# Or Play yourself, then:
python Scripts/demos/demo_arena/app.py --no-ensure --verbose
```

Demo Arena Python helpers resolve rlmesh `demos/common` via `RLMESH_ROOT` or a junctioned `Plugins/RLMesh`.

## Layout

| Path | Role |
|------|------|
| `Content/` | Maps, materials, prop Blueprints |
| `Source/RLmeshSim/` | Game module, demo hosts, Demo Arena component, editor helper bootstrap |
| `Scripts/demo_control_server.py` | Optional in-editor load/play HTTP API |
| `Scripts/demo_client.py` | CLI for that API |
| `Scripts/envs/` | Environment swap used by the helper |
| `Scripts/demos/demo_arena/` | Demo Arena Python clients |
| `Plugins/RLMesh/` | From rlmesh (gitignored when junctioned) |

## Notes

- Keep one Serving env active at a time (`envs.activate` removes other hosts).
- Source the plugin from rlmesh so this sample stays a consumer, not a second source of truth.
- Licensed dual MIT / Apache-2.0 (same as rlmesh). See `LICENSE-MIT` and `LICENSE-APACHE`.
