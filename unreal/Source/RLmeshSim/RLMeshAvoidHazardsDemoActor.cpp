// Copyright (c) 2026 ArenaX Labs

#include "RLMeshAvoidHazardsDemoActor.h"

#include "Components/ActorComponent.h"
#include "Components/StaticMeshComponent.h"
#include "UObject/ConstructorHelpers.h"
#include "UObject/UnrealType.h"

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
}

void ARLMeshAvoidHazardsDemoActor::BeginPlay()
{
	Super::BeginPlay();

	if (AvoidHazards)
	{
		return;
	}

	UClass* AvoidClass = LoadClass<UActorComponent>(
		nullptr, TEXT("/Script/RLMeshUnreal.RLMeshAvoidHazardsComponent"));
	if (!AvoidClass)
	{
		UE_LOG(LogTemp, Error,
			   TEXT("RLMeshAvoidHazardsDemoActor: could not load RLMeshAvoidHazardsComponent"));
		return;
	}

	AvoidHazards = NewObject<UActorComponent>(this, AvoidClass, TEXT("AvoidHazards"));
	if (!AvoidHazards)
	{
		return;
	}

	auto SetStr = [this](const TCHAR* Name, const FString& Value)
	{
		if (FStrProperty* Prop = FindFProperty<FStrProperty>(AvoidHazards->GetClass(), Name))
		{
			Prop->SetPropertyValue_InContainer(AvoidHazards, Value);
		}
	};
	auto SetFloat = [this](const TCHAR* Name, float Value)
	{
		if (FFloatProperty* Prop = FindFProperty<FFloatProperty>(AvoidHazards->GetClass(), Name))
		{
			Prop->SetPropertyValue_InContainer(AvoidHazards, Value);
		}
	};
	auto SetInt = [this](const TCHAR* Name, int32 Value)
	{
		if (FIntProperty* Prop = FindFProperty<FIntProperty>(AvoidHazards->GetClass(), Name))
		{
			Prop->SetPropertyValue_InContainer(AvoidHazards, Value);
		}
	};

	SetStr(TEXT("Address"), TEXT("127.0.0.1:7447/env"));
	SetStr(TEXT("EnvId"), TEXT("Unreal-AvoidHazards-v0"));
	SetFloat(TEXT("StepSize"), 50.f);
	SetFloat(TEXT("GoalRange"), 1000.f);
	SetFloat(TEXT("HazardHalfExtent"), 50.f);
	SetFloat(TEXT("AgentHalfExtent"), 25.f);
	SetFloat(TEXT("MinClearance"), 150.f);
	SetFloat(TEXT("HazardPenalty"), 1.f);
	SetInt(TEXT("MaxSteps"), 300);
	SetInt(TEXT("NumHazards"), 4);

	if (IsValid(GoalActor))
	{
		if (FObjectPropertyBase* Prop =
				FindFProperty<FObjectPropertyBase>(AvoidHazards->GetClass(), TEXT("GoalActor")))
		{
			Prop->SetObjectPropertyValue_InContainer(AvoidHazards, GoalActor);
		}
	}

	AddInstanceComponent(AvoidHazards);
	AvoidHazards->RegisterComponent();
}
