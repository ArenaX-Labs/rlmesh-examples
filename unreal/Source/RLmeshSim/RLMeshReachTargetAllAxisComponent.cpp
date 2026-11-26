#include "RLMeshReachTargetAllAxisComponent.h"

#include "GameFramework/Actor.h"

#include <limits>
#include <vector>

URLMeshReachTargetAllAxisComponent::URLMeshReachTargetAllAxisComponent()
{
	EnvId = TEXT("Unreal-ReachTargetAllAxis-v0");
}

void URLMeshReachTargetAllAxisComponent::BeginPlay()
{
	Start = GetOwner()->GetActorLocation();
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

rlmesh::ResetResult URLMeshReachTargetAllAxisComponent::ResetEnv(std::optional<int64_t>,
																 const std::optional<rlmesh::InfoDict>&)
{
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
	const std::vector<float> D = rlmesh::ext::to_vector<float>(Action->as_tensor());
	GetOwner()->AddActorWorldOffset(FVector(D[0], D[1], D[2]).GetSafeNormal() * StepSize);
	++Steps;

	const double Distance = FVector::Dist(GetOwner()->GetActorLocation(), Target);
	const bool bReached = Distance <= StepSize / 2.0;
	return {Observe(), -Distance / TargetRange, bReached, !bReached && Steps >= MaxSteps, {{"success", bReached}}};
}

rlmesh::Value URLMeshReachTargetAllAxisComponent::Observe() const
{
	const FVector Offset = Target - GetOwner()->GetActorLocation();
	return rlmesh::ext::from_vector<float>(
		{static_cast<float>(Offset.X), static_cast<float>(Offset.Y), static_cast<float>(Offset.Z)}, {3});
}
