// Copyright (c) 2026 ArenaX Labs

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RLMeshDemoArenaDemoActor.generated.h"

class UStaticMeshComponent;
class URLMeshDemoArenaComponent;

/**
 * Visible cube that attaches URLMeshDemoArenaComponent at BeginPlay.
 * Intended for GameScene_Demo (walls block; labeled Goal/Coin/Obstacle).
 */
UCLASS()
class RLMESHSIM_API ARLMeshDemoArenaDemoActor : public AActor
{
	GENERATED_BODY()

public:
	ARLMeshDemoArenaDemoActor();

protected:
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "RLMesh")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "RLMesh")
	TObjectPtr<URLMeshDemoArenaComponent> DemoArena;

	/** Optional level Goal actor (world XY); also discoverable by label. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "RLMesh")
	TObjectPtr<AActor> GoalActor;
};
