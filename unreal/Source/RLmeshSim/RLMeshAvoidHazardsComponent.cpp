#include "RLMeshAvoidHazardsComponent.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInterface.h"
#include "UObject/UObjectGlobals.h"

#include <limits>
#include <vector>

URLMeshAvoidHazardsComponent::URLMeshAvoidHazardsComponent()
{
	EnvId = TEXT("Unreal-AvoidHazards-v0");
}

void URLMeshAvoidHazardsComponent::BeginPlay()
{
	Start = GetOwner()->GetActorLocation();

	UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	FActorSpawnParameters Spawn;
	Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	for (int32 i = 0; i < NumHazards; ++i)
	{
		AStaticMeshActor* Hazard = GetWorld()->SpawnActor<AStaticMeshActor>(Start, FRotator::ZeroRotator, Spawn);
		UStaticMeshComponent* Mesh = Hazard->GetStaticMeshComponent();
		Mesh->SetMobility(EComponentMobility::Movable);
		Mesh->SetStaticMesh(Cube);
		Mesh->SetMaterial(0, HazardMaterial);
		Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		// The engine's cube is 100 units wide.
		Hazard->SetActorScale3D(FVector(HazardHalfExtent / 50.0));
		Hazards.Add(Hazard);
	}
	Super::BeginPlay();
}

rlmesh::spaces::Space URLMeshAvoidHazardsComponent::ObservationSpace() const
{
	const double Infinity = std::numeric_limits<double>::infinity();
	return rlmesh::spaces::Dict({
		{"goal", rlmesh::spaces::Box(-Infinity, Infinity, {2})},
		{"hazards", rlmesh::spaces::Box(-Infinity, Infinity, {NumHazards, 2})},
	});
}

rlmesh::spaces::Space URLMeshAvoidHazardsComponent::ActionSpace() const
{
	return rlmesh::spaces::Box(-1.0, 1.0, {2});
}

rlmesh::ResetResult URLMeshAvoidHazardsComponent::ResetEnv(std::optional<int64_t>,
														   const std::optional<rlmesh::InfoDict>&)
{
	GetOwner()->SetActorLocation(Start);
	if (IsValid(GoalActor))
	{
		Goal = FVector(FVector2D(GoalActor->GetActorLocation()), Start.Z);
	}
	else
	{
		const float Angle = Random.FRandRange(0.f, 2.f * UE_PI);
		const float Distance = Random.FRandRange(0.5f * GoalRange, GoalRange);
		Goal = Start + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.0) * Distance;
	}

	// Spread the hazards along the straight path, the first one almost on it.
	const FVector Path = Goal - Start;
	const FVector Across = FVector(-Path.Y, Path.X, 0.0).GetSafeNormal();
	for (int32 i = 0; i < Hazards.Num(); ++i)
	{
		const double Along = (i + 1.0) / (Hazards.Num() + 1.0);
		const float Width = i == 0 ? HazardHalfExtent / 4 : CorridorHalfWidth;
		const double Aside = Random.FRandRange(-Width, Width);
		Hazards[i]->SetActorLocation(Start + Path * Along + Across * Aside);
	}
	Steps = 0;
	return {Observe(), {}};
}

rlmesh::StepResult URLMeshAvoidHazardsComponent::StepEnv(const std::optional<rlmesh::Value>& Action)
{
	const std::vector<float> D = rlmesh::ext::to_vector<float>(Action->as_tensor());
	const double Travel = FMath::Min(static_cast<double>(StepSize), OffsetTo(Goal).Size());
	GetOwner()->AddActorWorldOffset(FVector(FVector2D(D[0], D[1]).GetSafeNormal() * Travel, 0.0));
	++Steps;

	const bool bHitHazard = TouchesHazard();
	const double Distance = OffsetTo(Goal).Size();
	const bool bReached = !bHitHazard && Distance <= StepSize / 2.0;
	const double Reward = -Distance / GoalRange - (bHitHazard ? HazardPenalty : 0.0);
	const bool bTerminated = bHitHazard || bReached;
	return {Observe(), Reward, bTerminated, !bTerminated && Steps >= MaxSteps, {{"success", bReached}}};
}

FVector2D URLMeshAvoidHazardsComponent::OffsetTo(const FVector& Location) const
{
	return FVector2D(Location - GetOwner()->GetActorLocation());
}

bool URLMeshAvoidHazardsComponent::TouchesHazard() const
{
	const double Reach = AgentHalfExtent + HazardHalfExtent;
	for (const AActor* Hazard : Hazards)
	{
		const FVector2D Offset = OffsetTo(Hazard->GetActorLocation());
		if (FMath::Abs(Offset.X) <= Reach && FMath::Abs(Offset.Y) <= Reach)
		{
			return true;
		}
	}
	return false;
}

rlmesh::Value URLMeshAvoidHazardsComponent::Observe() const
{
	const FVector2D GoalOffset = OffsetTo(Goal);
	std::vector<float> HazardXY;
	for (const AActor* Hazard : Hazards)
	{
		const FVector2D Offset = OffsetTo(Hazard->GetActorLocation());
		HazardXY.push_back(static_cast<float>(Offset.X));
		HazardXY.push_back(static_cast<float>(Offset.Y));
	}
	return rlmesh::Metadata{
		{"goal",
		 rlmesh::ext::from_vector<float>({static_cast<float>(GoalOffset.X), static_cast<float>(GoalOffset.Y)}, {2})},
		{"hazards", rlmesh::ext::from_vector(HazardXY, {static_cast<size_t>(Hazards.Num()), 2})},
	};
}
