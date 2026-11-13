// Copyright (c) 2026 ArenaX Labs

#include "RLMeshChasePointDemoActor.h"

#include "Components/ActorComponent.h"
#include "Components/StaticMeshComponent.h"
#include "RLmeshSim.h"
#include "UObject/ConstructorHelpers.h"
#include "UObject/UnrealType.h"

ARLMeshChasePointDemoActor::ARLMeshChasePointDemoActor()
{
	PrimaryActorTick.bCanEverTick = false;

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	SetRootComponent(Mesh);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetSimulatePhysics(false);
	// No blocking collision: the agent must be free to teleport onto the goal.
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

void ARLMeshChasePointDemoActor::BeginPlay()
{
	Super::BeginPlay();

	if (ChasePoint)
	{
		return;
	}

	UClass* ChaseClass = LoadClass<UActorComponent>(
		nullptr, TEXT("/Script/RLMeshUnreal.RLMeshChasePointComponent"));
	if (!ChaseClass)
	{
		UE_LOG(LogRLmeshSim, Error,
			   TEXT("RLMeshChasePointDemoActor: could not load RLMeshChasePointComponent"));
		return;
	}

	ChasePoint = NewObject<UActorComponent>(this, ChaseClass, TEXT("ChasePoint"));
	if (!ChasePoint)
	{
		return;
	}

	auto SetStr = [this](const TCHAR* Name, const FString& Value)
	{
		if (FStrProperty* Prop = FindFProperty<FStrProperty>(ChasePoint->GetClass(), Name))
		{
			Prop->SetPropertyValue_InContainer(ChasePoint, Value);
		}
	};
	auto SetFloat = [this](const TCHAR* Name, float Value)
	{
		if (FFloatProperty* Prop = FindFProperty<FFloatProperty>(ChasePoint->GetClass(), Name))
		{
			Prop->SetPropertyValue_InContainer(ChasePoint, Value);
		}
	};
	auto SetInt = [this](const TCHAR* Name, int32 Value)
	{
		if (FIntProperty* Prop = FindFProperty<FIntProperty>(ChasePoint->GetClass(), Name))
		{
			Prop->SetPropertyValue_InContainer(ChasePoint, Value);
		}
	};

	SetStr(TEXT("Address"), TEXT("127.0.0.1:7447/env"));
	SetStr(TEXT("EnvId"), TEXT("Unreal-ChasePoint-v0"));
	SetFloat(TEXT("StepSize"), 50.f);
	SetFloat(TEXT("GoalRange"), 1000.f);
	SetFloat(TEXT("GoalStepSize"), 35.f);
	SetFloat(TEXT("GoalWanderRadius"), 600.f);
	SetInt(TEXT("MaxSteps"), 300);
	SetInt(TEXT("GoalMoveSteps"), 40);

	if (IsValid(GoalActor))
	{
		if (FObjectPropertyBase* Prop =
				FindFProperty<FObjectPropertyBase>(ChasePoint->GetClass(), TEXT("GoalActor")))
		{
			Prop->SetObjectPropertyValue_InContainer(ChasePoint, GoalActor);
		}
	}

	AddInstanceComponent(ChasePoint);
	ChasePoint->RegisterComponent();
}
