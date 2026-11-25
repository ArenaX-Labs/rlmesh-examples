#include "RLMeshReachTargetAllAxisComponent.h"

#include "Components/SceneComponent.h"
#include "GameFramework/Actor.h"

#include <limits>

URLMeshReachTargetAllAxisComponent::URLMeshReachTargetAllAxisComponent()
{
	EnvId = TEXT("Unreal-ReachTargetAllAxis-v0");
}

void URLMeshReachTargetAllAxisComponent::BeginPlay()
{
	// Steps move the owner, which a Static root refuses.
	if (USceneComponent* Root = GetOwner()->GetRootComponent())
	{
		Root->SetMobility(EComponentMobility::Movable);
	}
	Start = GetOwner()->GetActorLocation();
	Random.GenerateNewSeed();
	Super::BeginPlay();
}

rlmesh::spaces::Space URLMeshReachTargetAllAxisComponent::ObservationSpace() const
{
	const double Infinity = std::numeric_limits<double>::infinity();
	return rlmesh::spaces::Box(-Infinity, Infinity, {3});
}

rlmesh::spaces::Space URLMeshReachTargetAllAxisComponent::ActionSpace() const
{
	return rlmesh::spaces::Box(-1.0, 1.0, {3});
}

rlmesh::ResetResult URLMeshReachTargetAllAxisComponent::ResetEnv(std::optional<int64_t> Seed,
																 const std::optional<rlmesh::InfoDict>&)
{
	if (Seed)
	{
		const uint64 Bits = static_cast<uint64>(*Seed);
		Random.Initialize(static_cast<int32>(Bits ^ (Bits >> 32)));
	}
	GetOwner()->SetActorLocation(Start);
	if (IsValid(TargetActor))
	{
		Target = TargetActor->GetActorLocation();
	}
	else
	{
		const double X = Random.FRandRange(-TargetRange, TargetRange);
		const double Y = Random.FRandRange(-TargetRange, TargetRange);
		const double Z = Random.FRandRange(-TargetRange, TargetRange);
		Target = Start + FVector(X, Y, Z);
	}
	Steps = 0;
	return {Observe(), {}};
}

rlmesh::StepResult URLMeshReachTargetAllAxisComponent::StepEnv(const std::optional<rlmesh::Value>& Action)
{
	const rlmesh::Tensor Direction = Action.value().as_tensor();
	if (Direction.dtype() != rlmesh::DType::Float32 || Direction.size() != 3)
	{
		throw rlmesh::RecoverableEnvironmentException("step needs a float32 action of shape (3,)");
	}
	const float* D = reinterpret_cast<const float*>(Direction.buffer().data());
	GetOwner()->AddActorWorldOffset(FVector(D[0], D[1], D[2]).GetSafeNormal() * StepSize);
	++Steps;

	const double Distance = FVector::Dist(GetOwner()->GetActorLocation(), Target);
	const bool bReached = Distance <= StepSize / 2.0;
	return {Observe(), -Distance / TargetRange, bReached, !bReached && Steps >= MaxSteps, {{"success", bReached}}};
}

rlmesh::Value URLMeshReachTargetAllAxisComponent::Observe() const
{
	const FVector Offset = Target - GetOwner()->GetActorLocation();
	const float Observation[3] = {static_cast<float>(Offset.X), static_cast<float>(Offset.Y),
								  static_cast<float>(Offset.Z)};
	return rlmesh::Tensor(Observation, sizeof(Observation), {3}, rlmesh::DType::Float32);
}
