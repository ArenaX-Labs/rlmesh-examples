#pragma once

#include "CoreMinimal.h"
#include "Math/RandomStream.h"
#include "RLMeshEnvComponent.h"

#include "RLMeshChasePointComponent.generated.h"

/**
 * Catch a goal that wanders for the first GoalMoveSteps steps, moving the owning actor on the XY plane.
 * Observation: the XY offset to the goal, Box(2). Action: a direction, Box([-1, 1], 2).
 */
UCLASS(ClassGroup = (RLmeshSim), meta = (BlueprintSpawnableComponent))
class RLMESHSIM_API URLMeshChasePointComponent : public URLMeshEnvComponent
{
	GENERATED_BODY()

public:
	URLMeshChasePointComponent();

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float StepSize = 50.f;

	/** Farthest a random goal is placed from the start. */
	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float GoalRange = 1000.f;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	int32 MaxSteps = 300;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "0"))
	int32 GoalMoveSteps = 40;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "0"))
	float GoalStepSize = 35.f;

	/** How far the goal may wander from where it started the episode. */
	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float GoalWanderRadius = 600.f;

	/** Shows the goal; when set, every episode's goal starts where this actor was placed. */
	UPROPERTY(EditAnywhere, Category = "RLMesh")
	TObjectPtr<AActor> GoalActor;

protected:
	virtual void BeginPlay() override;

	virtual rlmesh::spaces::Space ObservationSpace() const override;
	virtual rlmesh::spaces::Space ActionSpace() const override;
	virtual rlmesh::ResetResult ResetEnv(std::optional<int64_t> Seed,
										 const std::optional<rlmesh::InfoDict>& Options) override;
	virtual rlmesh::StepResult StepEnv(const std::optional<rlmesh::Value>& Action) override;

private:
	FVector2D GoalOffset() const;
	void MoveGoal(const FVector2D& NewGoal);
	rlmesh::Value Observe() const;

	FVector Start = FVector::ZeroVector;
	FVector2D GoalHome = FVector2D::ZeroVector;
	FVector2D Goal = FVector2D::ZeroVector;
	int32 Steps = 0;
	FRandomStream Random;
};
