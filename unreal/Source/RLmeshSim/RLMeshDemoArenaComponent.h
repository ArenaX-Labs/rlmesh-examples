#pragma once

#include "CoreMinimal.h"
#include "RLMeshEnvComponent.h"

#include "RLMeshDemoArenaComponent.generated.h"

/**
 * Collect the level's coins and its goal without touching an obstacle; walls block movement.
 * Coins, the goal and obstacles are the level's actors whose class name contains Coin, Goal or Obstacle.
 *
 * Observation: a Dict of XY offsets, "goal" (2), "coins" (NumCoins, 2) and "obstacles" (NumObstacles, 2),
 * zero once collected or when absent, and "walls", the distance to the nearest wall along NumWallRays
 * directions (ray 0 is +X, then counterclockwise). Action: a direction, Box([-1, 1], 2).
 */
UCLASS(ClassGroup = (RLmeshSim), meta = (BlueprintSpawnableComponent))
class RLMESHSIM_API URLMeshDemoArenaComponent : public URLMeshEnvComponent
{
	GENERATED_BODY()

public:
	URLMeshDemoArenaComponent();

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float StepSize = 50.f;

	/** Scales the per-step penalty for the distance to the nearest remaining pickup. */
	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float GoalRange = 2000.f;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	int32 MaxSteps = 400;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1", ClampMax = "16"))
	int32 NumCoins = 3;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1", ClampMax = "16"))
	int32 NumObstacles = 1;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float PickupRadius = 55.f;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float AgentHalfExtent = 25.f;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float ObstacleHalfExtent = 50.f;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1", ClampMax = "16"))
	int32 NumWallRays = 8;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float WallSenseRange = 350.f;

protected:
	virtual void BeginPlay() override;

	virtual rlmesh::spaces::Space ObservationSpace() const override;
	virtual rlmesh::spaces::Space ActionSpace() const override;
	virtual rlmesh::ResetResult ResetEnv(std::optional<int64_t> Seed,
										 const std::optional<rlmesh::InfoDict>& Options) override;
	virtual rlmesh::StepResult StepEnv(const std::optional<rlmesh::Value>& Action) override;

private:
	TArray<AActor*> Pickups() const;
	FVector2D OffsetTo(const AActor* Actor) const;
	AActor* NearestPickup() const;
	bool TouchesObstacle() const;
	rlmesh::Value Observe() const;

	FVector Start = FVector::ZeroVector;
	int32 Steps = 0;

	UPROPERTY()
	TObjectPtr<AActor> Goal;

	UPROPERTY()
	TArray<TObjectPtr<AActor>> Coins;

	UPROPERTY()
	TArray<TObjectPtr<AActor>> Obstacles;
};
