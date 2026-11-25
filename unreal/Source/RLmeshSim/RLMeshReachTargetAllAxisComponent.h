#pragma once

#include "CoreMinimal.h"
#include "Math/RandomStream.h"
#include "RLMeshEnvComponent.h"

#include "RLMeshReachTargetAllAxisComponent.generated.h"

/**
 * Move the owning actor in 3D to a target. Observation: the offset to the target, Box(3).
 * Action: a direction, Box([-1, 1], 3); each step moves StepSize along it.
 */
UCLASS(ClassGroup = (RLmeshSim), meta = (BlueprintSpawnableComponent))
class RLMESHSIM_API URLMeshReachTargetAllAxisComponent : public URLMeshEnvComponent
{
	GENERATED_BODY()

public:
	URLMeshReachTargetAllAxisComponent();

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float StepSize = 50.f;

	/** Farthest a random target is placed from the start. */
	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float TargetRange = 1000.f;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	int32 MaxSteps = 200;

	/** When set, the target is this actor's location instead of a random point. */
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
	rlmesh::Value Observe() const;

	FVector Start = FVector::ZeroVector;
	FVector Target = FVector::ZeroVector;
	int32 Steps = 0;
	FRandomStream Random;
};
