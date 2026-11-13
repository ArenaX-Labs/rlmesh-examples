// Copyright (c) 2026 ArenaX Labs

#include "RLMeshDemoArenaDemoActor.h"

#include "Components/StaticMeshComponent.h"
#include "RLMeshDemoArenaComponent.h"
#include "UObject/ConstructorHelpers.h"

ARLMeshDemoArenaDemoActor::ARLMeshDemoArenaDemoActor()
{
	PrimaryActorTick.bCanEverTick = false;

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	SetRootComponent(Mesh);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetSimulatePhysics(false);
	// Block so swept steps collide with authored walls/floor.
	Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	Mesh->SetCollisionProfileName(TEXT("BlockAll"));

	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (CubeMesh.Succeeded())
	{
		Mesh->SetStaticMesh(CubeMesh.Object);
	}
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> BlueMat(TEXT("/Game/Blue.Blue"));
	if (BlueMat.Succeeded())
	{
		Mesh->SetMaterial(0, BlueMat.Object);
	}
	Mesh->SetWorldScale3D(FVector(0.5f));

	DemoArena = CreateDefaultSubobject<URLMeshDemoArenaComponent>(TEXT("DemoArena"));
	DemoArena->Address = TEXT("127.0.0.1:7447/env");
	DemoArena->EnvId = TEXT("Unreal-DemoArena-v0");
	DemoArena->StepSize = 50.f;
	DemoArena->GoalRange = 2000.f;
	DemoArena->PickupRadius = 40.f;
	DemoArena->AgentHalfExtent = 25.f;
	DemoArena->ObstacleHalfExtent = 50.f;
	DemoArena->MaxSteps = 400;
	DemoArena->NumCoins = 3;
	DemoArena->NumObstacles = 1;
}

void ARLMeshDemoArenaDemoActor::BeginPlay()
{
	Super::BeginPlay();

	if (DemoArena && IsValid(GoalActor))
	{
		DemoArena->GoalActor = GoalActor;
	}
}
