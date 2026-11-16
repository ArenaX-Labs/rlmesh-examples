// Copyright (c) 2026 ArenaX Labs

#include "RLMeshAvoidHazardsDemoActor.h"

#include "Components/StaticMeshComponent.h"
#include "RLMeshAvoidHazardsComponent.h"
#include "UObject/ConstructorHelpers.h"

ARLMeshAvoidHazardsDemoActor::ARLMeshAvoidHazardsDemoActor()
{
	PrimaryActorTick.bCanEverTick = false;

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	SetRootComponent(Mesh);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetSimulatePhysics(false);
	Mesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Mesh->SetCollisionProfileName(TEXT("OverlapAllDynamic"));

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

	AvoidHazards = CreateDefaultSubobject<URLMeshAvoidHazardsComponent>(TEXT("AvoidHazards"));
	AvoidHazards->Address = TEXT("127.0.0.1:7447/env");
	AvoidHazards->EnvId = TEXT("Unreal-AvoidHazards-v0");
	AvoidHazards->StepSize = 50.f;
	AvoidHazards->GoalRange = 1000.f;
	AvoidHazards->HazardHalfExtent = 50.f;
	AvoidHazards->AgentHalfExtent = 25.f;
	AvoidHazards->MinClearance = 150.f;
	AvoidHazards->HazardPenalty = 1.f;
	AvoidHazards->MaxSteps = 300;
	AvoidHazards->NumHazards = 4;
}

void ARLMeshAvoidHazardsDemoActor::BeginPlay()
{
	Super::BeginPlay();

	if (AvoidHazards && IsValid(GoalActor))
	{
		AvoidHazards->GoalActor = GoalActor;
	}
}
