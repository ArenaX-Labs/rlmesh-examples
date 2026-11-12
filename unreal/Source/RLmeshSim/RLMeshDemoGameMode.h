// Copyright (c) 2026 ArenaX Labs

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "RLMeshDemoGameMode.generated.h"

/**
 * On Play: starts the demo control HTTP API (editor Python) and only auto-spawns
 * a Reach Target demo actor when the level has no RLMesh env yet.
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

private:
	void EnsureDemoControlServer();
	bool LevelAlreadyHasEnv() const;
};
