# Unreal Engine demo arena

An Unreal Engine 5.6 project whose game worlds are RLMesh envs: each demo is an actor component the
RLMesh plugin serves while the game plays, driven by a Python policy.

<!-- TODO: record media/demo-arena.gif (Demo Arena: the blue cube collecting the coins, then the goal) on a Windows UE 5.6 machine and embed it here. -->

## Run it

Open `unreal/RLmeshSim.uproject` with the plugin installed (see [Needs](#needs)), press **Play**,
and once the Output Log shows `LogRLMesh: Serving ...`:

```bash
uv run --directory unreal Scripts/reach_target_all_axis.py
```

| Demo                  | Map                   | The policy has to                                | Client                             |
| --------------------- | --------------------- | ------------------------------------------------ | ---------------------------------- |
| Reach Target All Axis | `GameScene` (default) | fly to a target in 3D                            | `Scripts/reach_target_all_axis.py` |
| Demo Arena            | `GameScene_Demo`      | collect three coins, then the goal, around walls | `Scripts/demo_arena.py`            |
| Chase Point           | add to `GameScene`    | catch a goal that wanders                        | `Scripts/chase_point.py`           |
| Avoid Hazards         | add to `GameScene`    | reach a goal past hazard cubes                   | `Scripts/avoid_hazards.py`         |
| Collect Coins         | add to `GameScene`    | collect coins scattered on the floor             | `Scripts/collect_coins.py`         |

Chase Point, Avoid Hazards and Collect Coins are components without a map: in `GameScene`, delete
the blue `Agent` cube, place a cube (**Quick Add > Shapes > Cube**, scale 0.5), **Add** the **RLMesh
Chase Point**, **RLMesh Avoid Hazards** or **RLMesh Collect Coins** component, and for the first two
set **Goal Actor** to `Goal`. Only one env serves on port 7447 at a time.

## The RLMesh part

An env is an actor component: subclass the plugin's `URLMeshEnvComponent`, describe the spaces, and
implement reset and step, which the plugin runs on the game thread. This is Reach Target All Axis,
trimmed ([full source](Source/RLmeshSim/RLMeshReachTargetAllAxisComponent.cpp)):

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

The plugin makes the actor Movable, reseeds `Random` from the client's seed, and refuses an action
whose dtype or shape does not fit `ActionSpace()` before `StepEnv` runs, so the component holds only
game logic. The Python client is a policy and one `rlmesh.run` call
([`Scripts/reach_target_all_axis.py`](Scripts/reach_target_all_axis.py)):

```python
class TowardTarget(Model):
    def predict(self, observation):
        offset = observation  # (x, y, z) from the cube to the target
        return (offset / max(np.linalg.norm(offset), 1e-6)).astype(np.float32)


if __name__ == "__main__":
    address = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:7447/env"
    print(rlmesh.run(TowardTarget(), address, episodes=3))
```

## Needs

- Unreal Engine 5.6 with a C++ toolchain: Visual Studio 2022 on Windows, or the clang toolchain
  Unreal installs on Linux
  (`Engine/Build/BatchFiles/Linux/Build.sh RLmeshSimEditor Linux Development -Project="$PWD/RLmeshSim.uproject"`).
- The RLMesh Unreal plugin and C/C++ package from the rlmesh release `pyproject.toml` pins. Until
  the next release, build them from an rlmesh checkout with the plugin changes of
  [ArenaX-Labs/rlmesh#115](https://github.com/ArenaX-Labs/rlmesh/pull/115) and the C++ tensor
  helpers of [ArenaX-Labs/rlmesh#145](https://github.com/ArenaX-Labs/rlmesh/pull/145)
  (`mise run release:cxx:package`). Install them as the plugin's
  [README](https://github.com/ArenaX-Labs/rlmesh/tree/main/integrations/unreal/RLMesh#install)
  describes: `integrations/unreal/RLMesh` to `unreal/Plugins/RLMesh`, and the package into
  `Plugins/RLMesh/Source/ThirdParty/rlmesh`
  ([C API README](https://github.com/ArenaX-Labs/rlmesh/blob/main/crates/rlmesh-capi/README.md)).
- Then right-click `RLmeshSim.uproject`, **Generate Visual Studio project files**, and open it to
  build the `RLmeshSim` module.

## Next

- Every client takes the env's address as its one argument
  (`uv run --directory unreal Scripts/chase_point.py 192.168.1.20:7447/env`). To serve to other
  machines, set the component's **Address** and give the editor a host identity in
  `RLMESH_HOST_IDENTITY`
  ([CLI reference](https://github.com/ArenaX-Labs/rlmesh/blob/main/docs/reference/cli.md)).
- Each step takes at least one frame, so the project caps the frame rate at 120 FPS with VSync off
  ([`Config/DefaultEngine.ini`](Config/DefaultEngine.ini)) and keeps the editor at full speed
  without focus
  ([`Config/DefaultEditorPerProjectUserSettings.ini`](Config/DefaultEditorPerProjectUserSettings.ini)).
- `Source/RLmeshSim/RLMesh*Component.*` holds one env per demo, `RLMesh*DemoActor.*` the cubes the
  maps place, and `PlayerPawn.*` a fly camera (right mouse to look, WASD and QE to move).
