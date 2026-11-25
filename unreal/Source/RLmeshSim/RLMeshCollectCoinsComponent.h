#pragma once

#include "CoreMinimal.h"
#include "Math/RandomStream.h"
#include "RLMeshEnvComponent.h"

#include "RLMeshCollectCoinsComponent.generated.h"

class UMaterialInterface;

/**
 * Collect every coin, moving the owning actor on the XY plane.
 * Observation: a Dict, "nearest_coin", the XY offset to the nearest coin left (2), and "coins_left".
 * Action: a direction, Box([-1, 1], 2).
 */
UCLASS(ClassGroup = (RLmeshSim), meta = (BlueprintSpawnableComponent))
class RLMESHSIM_API URLMeshCollectCoinsComponent : public URLMeshEnvComponent
{
	GENERATED_BODY()

public:
	URLMeshCollectCoinsComponent();

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float StepSize = 50.f;

	/** Farthest a coin is placed from the start. */
	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float CoinRange = 1000.f;

	/** Nearest a coin is placed to the start. */
	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float MinClearance = 200.f;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	int32 MaxSteps = 400;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1", ClampMax = "16"))
	int32 NumCoins = 3;

	UPROPERTY(EditAnywhere, Category = "RLMesh", meta = (ClampMin = "1"))
	float PickupRadius = 40.f;

	UPROPERTY(EditAnywhere, Category = "RLMesh")
	TObjectPtr<UMaterialInterface> CoinMaterial;

protected:
	virtual void BeginPlay() override;

	virtual rlmesh::spaces::Space ObservationSpace() const override;
	virtual rlmesh::spaces::Space ActionSpace() const override;
	virtual rlmesh::ResetResult ResetEnv(std::optional<int64_t> Seed,
										 const std::optional<rlmesh::InfoDict>& Options) override;
	virtual rlmesh::StepResult StepEnv(const std::optional<rlmesh::Value>& Action) override;

private:
	FVector2D OffsetTo(const AActor* Coin) const;
	AActor* NearestCoin() const;
	int32 CoinsLeft() const;
	rlmesh::Value Observe() const;

	FVector Start = FVector::ZeroVector;
	int32 Steps = 0;
	FRandomStream Random;

	UPROPERTY()
	TArray<TObjectPtr<AActor>> Coins;
};
