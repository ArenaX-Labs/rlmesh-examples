// Copyright (c) 2026 ArenaX Labs

#include "RLMeshReachDemoActor.h"

#include "Components/ActorComponent.h"
#include "Components/StaticMeshComponent.h"
#include "RLmeshSim.h"
#include "UObject/ConstructorHelpers.h"
#include "UObject/UnrealType.h"

ARLMeshReachDemoActor::ARLMeshReachDemoActor()
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
}

void ARLMeshReachDemoActor::BeginPlay()
{
	Super::BeginPlay();

	if (ReachTarget)
	{
		return;
	}

	UClass* ReachClass = LoadClass<UActorComponent>(
		nullptr, TEXT("/Script/RLMeshUnreal.RLMeshReachTargetComponent"));
	if (!ReachClass)
	{
		UE_LOG(LogRLmeshSim, Error, TEXT("RLMeshReachDemoActor: could not load RLMeshReachTargetComponent"));
		return;
	}

	ReachTarget = NewObject<UActorComponent>(this, ReachClass, TEXT("ReachTarget"));
	if (!ReachTarget)
	{
		return;
	}

	auto SetStr = [this](const TCHAR* Name, const FString& Value)
	{
		if (FStrProperty* Prop = FindFProperty<FStrProperty>(ReachTarget->GetClass(), Name))
		{
			Prop->SetPropertyValue_InContainer(ReachTarget, Value);
		}
	};
	auto SetFloat = [this](const TCHAR* Name, float Value)
	{
		if (FFloatProperty* Prop = FindFProperty<FFloatProperty>(ReachTarget->GetClass(), Name))
		{
			Prop->SetPropertyValue_InContainer(ReachTarget, Value);
		}
	};
	auto SetInt = [this](const TCHAR* Name, int32 Value)
	{
		if (FIntProperty* Prop = FindFProperty<FIntProperty>(ReachTarget->GetClass(), Name))
		{
			Prop->SetPropertyValue_InContainer(ReachTarget, Value);
		}
	};

	SetStr(TEXT("Address"), TEXT("127.0.0.1:7447/env"));
	SetStr(TEXT("EnvId"), TEXT("Unreal-ReachTarget-v0"));
	SetFloat(TEXT("StepSize"), 50.f);
	SetFloat(TEXT("TargetRange"), 1000.f);
	SetInt(TEXT("MaxSteps"), 200);

	if (IsValid(TargetActor))
	{
		if (FObjectPropertyBase* Prop =
				FindFProperty<FObjectPropertyBase>(ReachTarget->GetClass(), TEXT("TargetActor")))
		{
			Prop->SetObjectPropertyValue_InContainer(ReachTarget, TargetActor);
		}
	}

	AddInstanceComponent(ReachTarget);
	ReachTarget->RegisterComponent();
}
