#pragma once

#include "CoreMinimal.h"
#include "RLMeshEnvComponent.h"

#include "RLMeshAvoidHazardsComponent.generated.h"

class UMaterialInterface;

/**
 * Reach a goal on the XY plane without touching the hazard cubes placed between it and the start.
 * Observation: a Dict of XY offsets, "goal" (2) and "hazards" (NumHazards, 2).
 * Action: a direction, Box([-1, 1], 2).
 */
UCLASS(ClassGroup = (RLmeshSim), meta = (BlueprintSpawnableComponent))
class RLMESHSIM_API URLMeshAvoidHazardsComponent : public URLMeshEnvComponent
{
	GENERATED_BODY()

public:
	URLMeshAvoidHazardsComponent();

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float StepSize = 50.f;

	/** Farthest a random goal is placed from the start. */
	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float GoalRange = 1000.f;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	int32 MaxSteps = 300;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1", ClampMax = "16"))
	int32 NumHazards = 4;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float HazardHalfExtent = 50.f;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float AgentHalfExtent = 25.f;

	/** How far a hazard may sit to either side of the straight path to the goal. */
	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "0"))
	float CorridorHalfWidth = 120.f;

	UPROPERTY(EditAnywhere, Category = "RLMesh")
	float HazardPenalty = 1.f;

	/** When set, the goal is this actor's location instead of a random point. */
	UPROPERTY(EditAnywhere, Category = "RLMesh")
	TObjectPtr<AActor> GoalActor;

	UPROPERTY(EditAnywhere, Category = "RLMesh")
	TObjectPtr<UMaterialInterface> HazardMaterial;

protected:
	virtual void BeginPlay() override;

	virtual rlmesh::spaces::Space ObservationSpace() const override;
	virtual rlmesh::spaces::Space ActionSpace() const override;
	virtual rlmesh::ResetResult ResetEnv(std::optional<int64_t> Seed,
										 const std::optional<rlmesh::InfoDict>& Options) override;
	virtual rlmesh::StepResult StepEnv(const std::optional<rlmesh::Value>& Action) override;

private:
	FVector2D OffsetTo(const FVector& Location) const;
	bool TouchesHazard() const;
	rlmesh::Value Observe() const;

	FVector Start = FVector::ZeroVector;
	FVector Goal = FVector::ZeroVector;
	int32 Steps = 0;

	UPROPERTY()
	TArray<TObjectPtr<AActor>> Hazards;
};
