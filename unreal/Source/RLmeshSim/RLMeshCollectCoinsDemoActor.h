// Copyright (c) 2026 ArenaX Labs

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RLMeshCollectCoinsDemoActor.generated.h"

class UStaticMeshComponent;
class URLMeshCollectCoinsComponent;

/**
 * Visible cube with a URLMeshCollectCoinsComponent (CreateDefaultSubobject).
 */
UCLASS()
class RLMESHSIM_API ARLMeshCollectCoinsDemoActor : public AActor
{
	GENERATED_BODY()

public:
	ARLMeshCollectCoinsDemoActor();

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "RLMesh")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "RLMesh")
	TObjectPtr<URLMeshCollectCoinsComponent> CollectCoins;
};
