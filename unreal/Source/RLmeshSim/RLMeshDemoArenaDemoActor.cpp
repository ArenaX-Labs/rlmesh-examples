// Copyright (c) 2026 ArenaX Labs

#include "RLMeshDemoArenaDemoActor.h"

#include "Components/ActorComponent.h"
#include "Components/StaticMeshComponent.h"
#include "UObject/ConstructorHelpers.h"
#include "UObject/UnrealType.h"

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
}

void ARLMeshDemoArenaDemoActor::BeginPlay()
{
	Super::BeginPlay();

	if (DemoArena)
	{
		return;
	}

	UClass* ArenaClass = LoadClass<UActorComponent>(
		nullptr, TEXT("/Script/RLMeshUnreal.RLMeshDemoArenaComponent"));
	if (!ArenaClass)
	{
		UE_LOG(LogTemp, Error,
			   TEXT("RLMeshDemoArenaDemoActor: could not load RLMeshDemoArenaComponent"));
		return;
	}

	DemoArena = NewObject<UActorComponent>(this, ArenaClass, TEXT("DemoArena"));
	if (!DemoArena)
	{
		return;
	}

	auto SetStr = [this](const TCHAR* Name, const FString& Value)
	{
		if (FStrProperty* Prop = FindFProperty<FStrProperty>(DemoArena->GetClass(), Name))
		{
			Prop->SetPropertyValue_InContainer(DemoArena, Value);
		}
	};
	auto SetFloat = [this](const TCHAR* Name, float Value)
	{
		if (FFloatProperty* Prop = FindFProperty<FFloatProperty>(DemoArena->GetClass(), Name))
		{
			Prop->SetPropertyValue_InContainer(DemoArena, Value);
		}
	};
	auto SetInt = [this](const TCHAR* Name, int32 Value)
	{
		if (FIntProperty* Prop = FindFProperty<FIntProperty>(DemoArena->GetClass(), Name))
		{
			Prop->SetPropertyValue_InContainer(DemoArena, Value);
		}
	};

	SetStr(TEXT("Address"), TEXT("127.0.0.1:7447/env"));
	SetStr(TEXT("EnvId"), TEXT("Unreal-DemoArena-v0"));
	SetFloat(TEXT("StepSize"), 50.f);
	SetFloat(TEXT("GoalRange"), 2000.f);
	SetFloat(TEXT("PickupRadius"), 40.f);
	SetFloat(TEXT("AgentHalfExtent"), 25.f);
	SetFloat(TEXT("ObstacleHalfExtent"), 50.f);
	SetInt(TEXT("MaxSteps"), 400);
	SetInt(TEXT("NumCoins"), 3);
	SetInt(TEXT("NumObstacles"), 1);

	if (IsValid(GoalActor))
	{
		if (FObjectPropertyBase* Prop =
				FindFProperty<FObjectPropertyBase>(DemoArena->GetClass(), TEXT("GoalActor")))
		{
			Prop->SetObjectPropertyValue_InContainer(DemoArena, GoalActor);
		}
	}

	AddInstanceComponent(DemoArena);
	DemoArena->RegisterComponent();
}
