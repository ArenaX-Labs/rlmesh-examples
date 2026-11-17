// Copyright (c) 2026 ArenaX Labs

#include "RLMeshReachTargetAllAxisDemoActor.h"

#include "Components/StaticMeshComponent.h"
#include "RLMeshReachTargetAllAxisComponent.h"
#include "UObject/ConstructorHelpers.h"

ARLMeshReachTargetAllAxisDemoActor::ARLMeshReachTargetAllAxisDemoActor()
{
	PrimaryActorTick.bCanEverTick = false;

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	SetRootComponent(Mesh);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetSimulatePhysics(false);
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

	ReachTarget = CreateDefaultSubobject<URLMeshReachTargetAllAxisComponent>(TEXT("ReachTarget"));
	ReachTarget->Address = TEXT("127.0.0.1:7447/env");
	ReachTarget->EnvId = TEXT("Unreal-ReachTargetAllAxis-v0");
	ReachTarget->StepSize = 50.f;
	ReachTarget->TargetRange = 1000.f;
	ReachTarget->MaxSteps = 200;
}

void ARLMeshReachTargetAllAxisDemoActor::BeginPlay()
{
	Super::BeginPlay();

	if (ReachTarget && IsValid(TargetActor))
	{
		ReachTarget->TargetActor = TargetActor;
	}
}
