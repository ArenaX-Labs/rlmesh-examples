// Copyright (c) 2026 ArenaX Labs

#include "RLMeshDemoGameMode.h"

#include "Components/ActorComponent.h"
#include "EngineUtils.h"
#include "PlayerPawn.h"
#include "RLMeshChasePointDemoActor.h"
#include "RLMeshDemoControl.h"
#include "RLMeshReachDemoActor.h"

ARLMeshDemoGameMode::ARLMeshDemoGameMode()
{
	DefaultPawnClass = APlayerPawn::StaticClass();
}

bool ARLMeshDemoGameMode::LevelAlreadyHasEnv() const
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return false;
	}

	for (TActorIterator<ARLMeshReachDemoActor> It(World); It; ++It)
	{
		return true;
	}
	for (TActorIterator<ARLMeshChasePointDemoActor> It(World); It; ++It)
	{
		return true;
	}

	if (UClass* EnvClass =
			LoadClass<UActorComponent>(nullptr, TEXT("/Script/RLMeshUnreal.RLMeshEnvComponent")))
	{
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			if (It->FindComponentByClass(EnvClass))
			{
				return true;
			}
		}
	}
	return false;
}

void ARLMeshDemoGameMode::BeginPlay()
{
	Super::BeginPlay();

	RLMeshEnsureDemoControlServer();

	if (LevelAlreadyHasEnv())
	{
		return;
	}

	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}

	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	World->SpawnActor<ARLMeshReachDemoActor>(DemoSpawnLocation, FRotator::ZeroRotator, Params);
}
