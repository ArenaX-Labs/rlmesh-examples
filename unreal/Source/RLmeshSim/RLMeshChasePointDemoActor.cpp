// Copyright (c) 2026 ArenaX Labs

#include "RLMeshChasePointDemoActor.h"

#include "Components/StaticMeshComponent.h"
#include "RLMeshChasePointComponent.h"
#include "UObject/ConstructorHelpers.h"

ARLMeshChasePointDemoActor::ARLMeshChasePointDemoActor()
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

	ChasePoint = CreateDefaultSubobject<URLMeshChasePointComponent>(TEXT("ChasePoint"));
	ChasePoint->Address = TEXT("127.0.0.1:7447/env");
	ChasePoint->EnvId = TEXT("Unreal-ChasePoint-v0");
	ChasePoint->StepSize = 50.f;
	ChasePoint->GoalRange = 1000.f;
	ChasePoint->GoalStepSize = 35.f;
	ChasePoint->GoalWanderRadius = 600.f;
	ChasePoint->MaxSteps = 300;
	ChasePoint->GoalMoveSteps = 40;
}

void ARLMeshChasePointDemoActor::BeginPlay()
{
	Super::BeginPlay();

	if (ChasePoint && IsValid(GoalActor))
	{
		ChasePoint->GoalActor = GoalActor;
	}
}
