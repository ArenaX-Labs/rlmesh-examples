// Copyright (c) 2026 ArenaX Labs

#include "RLMeshCollectCoinsDemoActor.h"

#include "Components/ActorComponent.h"
#include "Components/StaticMeshComponent.h"
#include "UObject/ConstructorHelpers.h"
#include "UObject/UnrealType.h"

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
}

void ARLMeshCollectCoinsDemoActor::BeginPlay()
{
	Super::BeginPlay();

	if (CollectCoins)
	{
		return;
	}

	UClass* CollectClass = LoadClass<UActorComponent>(
		nullptr, TEXT("/Script/RLMeshUnreal.RLMeshCollectCoinsComponent"));
	if (!CollectClass)
	{
		UE_LOG(LogTemp, Error,
			   TEXT("RLMeshCollectCoinsDemoActor: could not load RLMeshCollectCoinsComponent"));
		return;
	}

	CollectCoins = NewObject<UActorComponent>(this, CollectClass, TEXT("CollectCoins"));
	if (!CollectCoins)
	{
		return;
	}

	auto SetStr = [this](const TCHAR* Name, const FString& Value)
	{
		if (FStrProperty* Prop = FindFProperty<FStrProperty>(CollectCoins->GetClass(), Name))
		{
			Prop->SetPropertyValue_InContainer(CollectCoins, Value);
		}
	};
	auto SetFloat = [this](const TCHAR* Name, float Value)
	{
		if (FFloatProperty* Prop = FindFProperty<FFloatProperty>(CollectCoins->GetClass(), Name))
		{
			Prop->SetPropertyValue_InContainer(CollectCoins, Value);
		}
	};
	auto SetInt = [this](const TCHAR* Name, int32 Value)
	{
		if (FIntProperty* Prop = FindFProperty<FIntProperty>(CollectCoins->GetClass(), Name))
		{
			Prop->SetPropertyValue_InContainer(CollectCoins, Value);
		}
	};

	SetStr(TEXT("Address"), TEXT("127.0.0.1:7447/env"));
	SetStr(TEXT("EnvId"), TEXT("Unreal-CollectCoins-v0"));
	SetFloat(TEXT("StepSize"), 50.f);
	SetFloat(TEXT("CoinRange"), 1000.f);
	SetFloat(TEXT("PickupRadius"), 40.f);
	SetFloat(TEXT("MinClearance"), 200.f);
	SetFloat(TEXT("CoinHalfExtent"), 30.f);
	SetInt(TEXT("MaxSteps"), 400);
	SetInt(TEXT("NumCoins"), 3);

	AddInstanceComponent(CollectCoins);
	CollectCoins->RegisterComponent();
}
