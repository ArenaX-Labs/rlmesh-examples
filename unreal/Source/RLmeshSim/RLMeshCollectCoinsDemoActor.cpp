// Copyright (c) 2026 ArenaX Labs

#include "RLMeshCollectCoinsDemoActor.h"

#include "Components/StaticMeshComponent.h"
#include "RLMeshCollectCoinsComponent.h"
#include "UObject/ConstructorHelpers.h"

ARLMeshCollectCoinsDemoActor::ARLMeshCollectCoinsDemoActor()
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

	CollectCoins = CreateDefaultSubobject<URLMeshCollectCoinsComponent>(TEXT("CollectCoins"));
	CollectCoins->Address = TEXT("127.0.0.1:7447/env");
	CollectCoins->EnvId = TEXT("Unreal-CollectCoins-v0");
	CollectCoins->StepSize = 50.f;
	CollectCoins->CoinRange = 1000.f;
	CollectCoins->PickupRadius = 40.f;
	CollectCoins->MinClearance = 200.f;
	CollectCoins->CoinHalfExtent = 30.f;
	CollectCoins->MaxSteps = 400;
	CollectCoins->NumCoins = 3;
}
