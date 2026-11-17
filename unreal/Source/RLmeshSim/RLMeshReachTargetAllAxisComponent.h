// Copyright (c) 2026 ArenaX Labs

#pragma once

#include "CoreMinimal.h"
#include "Math/RandomStream.h"
#include "RLMeshEnvComponent.h"

#include "RLMeshReachTargetAllAxisComponent.generated.h"

/**
 * Demo env: move the owning actor in world space toward a 3D target (all axes).
 *
 * Distinct from the plugin Reach Target example (1D Discrete along X).
 *
 * Each reset puts the actor back where play began. If TargetActor is set, the
 * goal is that actor's world location; otherwise a target offset is picked
 * uniformly in [-TargetRange, TargetRange]^3. Observation is the remaining XYZ
 * offset (Box[3]). Action is Box([-1, 1]^3). Reward is minus Euclidean distance
 * over TargetRange; terminates within half a step; truncates after MaxSteps.
 */
UCLASS(ClassGroup = (RLmeshSim), meta = (BlueprintSpawnableComponent))
class RLMESHSIM_API URLMeshReachTargetAllAxisComponent : public URLMeshEnvComponent
{
	GENERATED_BODY()

public:
	URLMeshReachTargetAllAxisComponent();

	/** Distance one step moves the actor, in units. */
	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float StepSize = 50.f;

	/** Farthest a random target is placed from the start. Also scales reward. */
	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float TargetRange = 1000.f;

	/** Steps before an episode truncates. */
	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	int32 MaxSteps = 200;

	/**
	 * Optional level actor used as the 3D goal (e.g. a Target box).
	 * When set, reset uses this actor's world location instead of a random target.
	 */
	UPROPERTY(EditAnywhere, Category = "RLMesh")
	TObjectPtr<AActor> TargetActor;

protected:
	virtual void BeginPlay() override;

	virtual rlmesh::spaces::Space ObservationSpace() const override;
	virtual rlmesh::spaces::Space ActionSpace() const override;
	virtual rlmesh::ResetResult ResetEnv(std::optional<int64_t> Seed,
										 const std::optional<rlmesh::InfoDict>& Options) override;
	virtual rlmesh::StepResult StepEnv(const std::optional<rlmesh::Value>& Action) override;

private:
	FVector Remaining() const;
	double Distance() const;
	rlmesh::Value Observe() const;
	rlmesh::InfoDict MakeInfo() const;

	FVector Start = FVector::ZeroVector;
	/** Goal as world-space offset from Start (TargetWorld - Start). */
	FVector TargetOffset = FVector::ZeroVector;
	int32 Steps = 0;
	FRandomStream Random;
};
