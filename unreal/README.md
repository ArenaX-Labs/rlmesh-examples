# RLMesh Unreal Engine demos

An Unreal Engine 5.6 project that serves game worlds as
[RLMesh](https://github.com/ArenaX-Labs/rlmesh) environments and drives them from Python. Press
Play, run a client, and watch a policy move the blue cube.

| Demo                  | Map                | The policy has to                                | Client                             |
| --------------------- | ------------------ | ------------------------------------------------ | ---------------------------------- |
| Reach Target All Axis | `GameScene`        | fly to a target in 3D                            | `Scripts/reach_target_all_axis.py` |
| Demo Arena            | `GameScene_Demo`   | collect three coins, then the goal, around walls | `Scripts/demo_arena.py`            |
| Chase Point           | add to `GameScene` | catch a goal that wanders                        | `Scripts/chase_point.py`           |
| Avoid Hazards         | add to `GameScene` | reach a goal past hazard cubes                   | `Scripts/avoid_hazards.py`         |
| Collect Coins         | add to `GameScene` | collect coins scattered on the floor             | `Scripts/collect_coins.py`         |

## How it works

An environment is an actor component. Subclass the plugin's `URLMeshEnvComponent`, describe the
observation and action spaces, and implement reset and step; the plugin serves it while the game
plays and runs `ResetEnv` and `StepEnv` on the game thread. This is Reach Target All Axis, trimmed
([full source](Source/RLmeshSim/RLMeshReachTargetAllAxisComponent.cpp)):

```cpp
rlmesh::spaces::Space URLMeshReachTargetAllAxisComponent::ObservationSpace() const
{
	const double Infinity = std::numeric_limits<double>::infinity();
	return rlmesh::spaces::Box(-Infinity, Infinity, {3}); // offset to the target
}

rlmesh::spaces::Space URLMeshReachTargetAllAxisComponent::ActionSpace() const
{
	return rlmesh::spaces::Box(-1.0, 1.0, {3}); // a direction to move in
}

rlmesh::ResetResult URLMeshReachTargetAllAxisComponent::ResetEnv(std::optional<int64_t>,
																 const std::optional<rlmesh::InfoDict>&)
{
	GetOwner()->SetActorLocation(Start);
	Target = Start + FVector(Random.FRandRange(-TargetRange, TargetRange), Random.FRandRange(-TargetRange, TargetRange),
							 Random.FRandRange(-TargetRange, TargetRange));
	Steps = 0;
	return {Observe(), {}};
}

rlmesh::StepResult URLMeshReachTargetAllAxisComponent::StepEnv(const std::optional<rlmesh::Value>& Action)
{
	const std::vector<float> D = rlmesh::ext::to_vector<float>(Action->as_tensor());
	GetOwner()->AddActorWorldOffset(FVector(D[0], D[1], D[2]).GetSafeNormal() * StepSize);
	++Steps;

	const double Distance = FVector::Dist(GetOwner()->GetActorLocation(), Target);
	const bool bReached = Distance <= StepSize / 2.0;
	return {Observe(), -Distance / TargetRange, bReached, !bReached && Steps >= MaxSteps, {{"success", bReached}}};
}

rlmesh::Value URLMeshReachTargetAllAxisComponent::Observe() const
{
	const FVector Offset = Target - GetOwner()->GetActorLocation();
	return rlmesh::ext::from_vector<float>(
		{static_cast<float>(Offset.X), static_cast<float>(Offset.Y), static_cast<float>(Offset.Z)}, {3});
}
```

The plugin does the rest: it makes the actor Movable, reseeds `Random` from the client's seed, and
refuses an action whose dtype or shape does not fit `ActionSpace()` before `StepEnv` runs (a `Box`
value outside its bounds still arrives, with a warning, by default), so the env holds only game
logic.

Any RLMesh model can then connect to the address the component serves on, `127.0.0.1:7447/env` by
default. The Python client is a policy and one `rlmesh.run` call
([full source](Scripts/reach_target_all_axis.py)):

```python
import numpy as np
import rlmesh
from rlmesh.numpy import Model


class TowardTarget(Model):
    def predict(self, observation):
        offset = observation  # (x, y, z) from the cube to the target
        return (offset / max(np.linalg.norm(offset), 1e-6)).astype(np.float32)


print(rlmesh.run(TowardTarget(), "127.0.0.1:7447/env", episodes=3))
```

## Requirements

- Unreal Engine 5.6 with a C++ toolchain: Visual Studio 2022 on Windows, or the clang toolchain
  Unreal installs on Linux.
- The RLMesh Unreal plugin and the RLMesh C/C++ package for your platform, from the same RLMesh
  release as the Python package.
- Until the next RLMesh release, an rlmesh checkout with the plugin changes of
  [ArenaX-Labs/rlmesh#115](https://github.com/ArenaX-Labs/rlmesh/pull/115) and the C++ tensor
  helpers of [ArenaX-Labs/rlmesh#145](https://github.com/ArenaX-Labs/rlmesh/pull/145), with the
  C/C++ package built from it (`mise run release:cxx:package`).
- [`uv`](https://docs.astral.sh/uv/), which installs Python and the pinned `rlmesh` from
  `pyproject.toml`.

The plugin supports Windows (Win64) and Linux. The steps below use Windows; on Linux use `/` in
paths, and build with
`Engine/Build/BatchFiles/Linux/Build.sh RLmeshSimEditor Linux Development -Project="$PWD/RLmeshSim.uproject"`
from your Unreal install.

## Setup

1. Clone this repository and the [rlmesh](https://github.com/ArenaX-Labs/rlmesh) repository at the
   release `pyproject.toml` pins.
2. Install the plugin as its
   [README](https://github.com/ArenaX-Labs/rlmesh/tree/main/integrations/unreal/RLMesh#install)
   describes: copy `integrations/unreal/RLMesh` to `Plugins/RLMesh` in this project, and unpack the
   RLMesh C/C++ package into `Plugins/RLMesh/Source/ThirdParty/rlmesh`. When a release has no
   package for your platform, build one from the rlmesh checkout as the
   [C API README](https://github.com/ArenaX-Labs/rlmesh/blob/main/crates/rlmesh-capi/README.md)
   describes (`mise run release:cxx:package`).
3. Right-click `RLmeshSim.uproject`, choose **Generate Visual Studio project files**, then open the
   project and let it build the `RLmeshSim` module (or build the `RLmeshSimEditor` target from
   Visual Studio).

## Run a demo

Each demo is the same three steps: open its map, press **Play**, and run its client from `unreal/`
with `uv run`, which installs the pinned `rlmesh` on first use. The Output Log shows
`LogRLMesh: Serving ...` once the env is up. Only one env can serve on port 7447 at a time.

**Reach Target All Axis.** `GameScene` opens by default.

```powershell
uv run Scripts\reach_target_all_axis.py
```

**Demo Arena.** Open `Content/GameScene_Demo`.

```powershell
uv run Scripts\demo_arena.py
```

**Chase Point, Avoid Hazards and Collect Coins.** These are components without a map of their own;
add one to `GameScene`:

1. Delete the blue `Agent` cube, which serves Reach Target All Axis.
2. Place a cube (**Quick Add > Shapes > Cube**) and set its scale to 0.5.
3. In its Details panel, **Add** the **RLMesh Chase Point**, **RLMesh Avoid Hazards** or **RLMesh
   Collect Coins** component. For Chase Point and Avoid Hazards, set **Goal Actor** to the `Goal`
   actor so you can see the goal; optionally set **Hazard Material** to `Red` or **Coin Material**
   to `Gold`.
4. Press **Play** and run the client:

   ```powershell
   uv run Scripts\chase_point.py
   uv run Scripts\avoid_hazards.py
   uv run Scripts\collect_coins.py
   ```

Every client takes the env's address as its one argument, for an env served elsewhere
(`uv run Scripts\chase_point.py 192.168.1.20:7447/env`). To serve to other machines, set the
component's **Address** and give the editor a host identity in `RLMESH_HOST_IDENTITY`; see the
[RLMesh CLI reference](https://github.com/ArenaX-Labs/rlmesh/blob/main/docs/reference/cli.md).

Each step takes at least one frame, so the project caps the frame rate at 120 FPS with VSync off
(`Config/DefaultEngine.ini`) and keeps the editor running at full speed while another window has
focus (`Config/DefaultEditorPerProjectUserSettings.ini`).

## Layout

| Path                                                    | Contents                                                                        |
| ------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `Source/RLmeshSim/RLMesh*Component.*`                   | One RLMesh env per demo                                                         |
| `Source/RLmeshSim/RLMesh*DemoActor.*`                   | The cubes `GameScene` and `GameScene_Demo` place, each holding an env component |
| `Source/RLmeshSim/PlayerPawn.*`, `RLMeshDemoGameMode.*` | A fly camera: hold the right mouse button to look, WASD and QE to move          |
| `Scripts/`                                              | One Python client per demo                                                      |
| `Content/`                                              | Maps, materials and the coin, goal and obstacle Blueprints                      |
