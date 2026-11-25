#include "RLMeshAvoidHazardsComponent.h"

#include "Components/SceneComponent.h"
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
	// Steps move the owner, which a Static root refuses.
	if (USceneComponent* Root = GetOwner()->GetRootComponent())
	{
		Root->SetMobility(EComponentMobility::Movable);
	}
	Start = GetOwner()->GetActorLocation();
	Random.GenerateNewSeed();

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
		{"goal", rlmesh::spaces::Box(-Infinity, Infinity, {2}).spec()},
		{"hazards", rlmesh::spaces::Box(-Infinity, Infinity, {NumHazards, 2}).spec()},
	});
}

rlmesh::spaces::Space URLMeshAvoidHazardsComponent::ActionSpace() const
{
	return rlmesh::spaces::Box(-1.0, 1.0, {2});
}

rlmesh::ResetResult URLMeshAvoidHazardsComponent::ResetEnv(std::optional<int64_t> Seed,
														   const std::optional<rlmesh::InfoDict>&)
{
	if (Seed)
	{
		const uint64 Bits = static_cast<uint64>(*Seed);
		Random.Initialize(static_cast<int32>(Bits ^ (Bits >> 32)));
	}
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
	const rlmesh::Tensor Direction = Action.value().as_tensor();
	if (Direction.dtype() != rlmesh::DType::Float32 || Direction.size() != 2)
	{
		throw rlmesh::RecoverableEnvironmentException("step needs a float32 action of shape (2,)");
	}
	const float* D = reinterpret_cast<const float*>(Direction.buffer().data());
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
	const float GoalXY[2] = {static_cast<float>(GoalOffset.X), static_cast<float>(GoalOffset.Y)};
	std::vector<float> HazardXY;
	for (const AActor* Hazard : Hazards)
	{
		const FVector2D Offset = OffsetTo(Hazard->GetActorLocation());
		HazardXY.push_back(static_cast<float>(Offset.X));
		HazardXY.push_back(static_cast<float>(Offset.Y));
	}
	const size_t HazardCount = static_cast<size_t>(Hazards.Num());
	return rlmesh::Metadata{
		{"goal", rlmesh::Tensor(GoalXY, sizeof(GoalXY), {2}, rlmesh::DType::Float32)},
		{"hazards",
		 rlmesh::Tensor(HazardXY.data(), HazardXY.size() * sizeof(float), {HazardCount, 2}, rlmesh::DType::Float32)},
	};
}
