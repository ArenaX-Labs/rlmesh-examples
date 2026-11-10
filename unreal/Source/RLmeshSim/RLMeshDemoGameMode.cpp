// Copyright (c) 2026 ArenaX Labs

#include "RLMeshDemoGameMode.h"

#include "Components/ActorComponent.h"
#include "EngineUtils.h"
#include "PlayerPawn.h"
#include "RLMeshReachDemoActor.h"

ARLMeshDemoGameMode::ARLMeshDemoGameMode()
{
	DefaultPawnClass = APlayerPawn::StaticClass();
}

void ARLMeshDemoGameMode::BeginPlay()
{
	Super::BeginPlay();

	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}

	for (TActorIterator<ARLMeshReachDemoActor> It(World); It; ++It)
	{
		return;
	}

	// A Blueprint (e.g. /Game/RLMesh) may already host Reach Target — don't double-serve.
	if (UClass* ReachClass = LoadClass<UActorComponent>(
			nullptr, TEXT("/Script/RLMeshUnreal.RLMeshReachTargetComponent")))
	{
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			if (It->FindComponentByClass(ReachClass))
			{
				return;
			}
		}
	}

	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	World->SpawnActor<ARLMeshReachDemoActor>(DemoSpawnLocation, FRotator::ZeroRotator, Params);
}
