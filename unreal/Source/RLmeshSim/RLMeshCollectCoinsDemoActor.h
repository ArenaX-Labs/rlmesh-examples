// Copyright (c) 2026 ArenaX Labs

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RLMeshCollectCoinsDemoActor.generated.h"

class UStaticMeshComponent;
class UActorComponent;

/**
 * Visible cube that attaches URLMeshCollectCoinsComponent at BeginPlay.
 */
UCLASS()
class RLMESHSIM_API ARLMeshCollectCoinsDemoActor : public AActor
{
	GENERATED_BODY()

public:
	ARLMeshCollectCoinsDemoActor();

protected:
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "RLMesh")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "RLMesh")
	TObjectPtr<UActorComponent> CollectCoins;
};
