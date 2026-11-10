// Copyright (c) 2026 ArenaX Labs

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "RLMeshDemoGameMode.generated.h"

/**
 * Spawns an ARLMeshReachDemoActor at Play if the level has none, so any map
 * can demo the RLMesh Reach Target env without hand-placing the actor.
 */
UCLASS()
class RLMESHSIM_API ARLMeshDemoGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	ARLMeshDemoGameMode();

protected:
	virtual void BeginPlay() override;

	/** World location for an auto-spawned demo actor. */
	UPROPERTY(EditAnywhere, Category = "RLMesh")
	FVector DemoSpawnLocation = FVector(0.f, 0.f, 50.f);
};
