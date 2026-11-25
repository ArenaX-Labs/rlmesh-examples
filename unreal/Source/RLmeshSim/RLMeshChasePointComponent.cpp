#include "RLMeshChasePointComponent.h"

#include "Components/SceneComponent.h"
#include "GameFramework/Actor.h"

#include <limits>

URLMeshChasePointComponent::URLMeshChasePointComponent()
{
	EnvId = TEXT("Unreal-ChasePoint-v0");
}

void URLMeshChasePointComponent::BeginPlay()
{
	// Steps move the owner and the goal, which a Static root refuses.
	for (AActor* Actor : {GetOwner(), GoalActor.Get()})
	{
		if (USceneComponent* Root = Actor ? Actor->GetRootComponent() : nullptr)
		{
			Root->SetMobility(EComponentMobility::Movable);
		}
	}
	Start = GetOwner()->GetActorLocation();
	if (IsValid(GoalActor))
	{
		GoalHome = FVector2D(GoalActor->GetActorLocation());
	}
	Random.GenerateNewSeed();
	Super::BeginPlay();
}

rlmesh::spaces::Space URLMeshChasePointComponent::ObservationSpace() const
{
	const double Infinity = std::numeric_limits<double>::infinity();
	return rlmesh::spaces::Box(-Infinity, Infinity, {2});
}

rlmesh::spaces::Space URLMeshChasePointComponent::ActionSpace() const
{
	return rlmesh::spaces::Box(-1.0, 1.0, {2});
}

rlmesh::ResetResult URLMeshChasePointComponent::ResetEnv(std::optional<int64_t> Seed,
														 const std::optional<rlmesh::InfoDict>&)
{
	if (Seed)
	{
		const uint64 Bits = static_cast<uint64>(*Seed);
		Random.Initialize(static_cast<int32>(Bits ^ (Bits >> 32)));
	}
	GetOwner()->SetActorLocation(Start);
	if (!IsValid(GoalActor))
	{
		const double X = Random.FRandRange(-GoalRange, GoalRange);
		const double Y = Random.FRandRange(-GoalRange, GoalRange);
		GoalHome = FVector2D(Start) + FVector2D(X, Y);
	}
	MoveGoal(GoalHome);
	Steps = 0;
	return {Observe(), {}};
}

rlmesh::StepResult URLMeshChasePointComponent::StepEnv(const std::optional<rlmesh::Value>& Action)
{
	const rlmesh::Tensor Direction = Action.value().as_tensor();
	if (Direction.dtype() != rlmesh::DType::Float32 || Direction.size() != 2)
	{
		throw rlmesh::RecoverableEnvironmentException("step needs a float32 action of shape (2,)");
	}
	const float* D = reinterpret_cast<const float*>(Direction.buffer().data());
	const double Travel = FMath::Min(static_cast<double>(StepSize), GoalOffset().Size());
	GetOwner()->AddActorWorldOffset(FVector(FVector2D(D[0], D[1]).GetSafeNormal() * Travel, 0.0));
	++Steps;

	if (Steps <= GoalMoveSteps)
	{
		// Wander in a random direction away from the agent, staying near home.
		const float Angle = Random.FRandRange(0.f, 2.f * UE_PI);
		FVector2D Heading(FMath::Cos(Angle), FMath::Sin(Angle));
		if (FVector2D::DotProduct(Heading, GoalOffset()) < 0.0)
		{
			Heading = -Heading;
		}
		const FVector2D FromHome = Goal + Heading * GoalStepSize - GoalHome;
		MoveGoal(GoalHome + FromHome.GetClampedToMaxSize(GoalWanderRadius));
	}

	const double Distance = GoalOffset().Size();
	const bool bReached = Distance <= FMath::Max(1.0, StepSize * 0.05);
	return {Observe(), -Distance / GoalRange, bReached, !bReached && Steps >= MaxSteps, {{"success", bReached}}};
}

FVector2D URLMeshChasePointComponent::GoalOffset() const
{
	return Goal - FVector2D(GetOwner()->GetActorLocation());
}

void URLMeshChasePointComponent::MoveGoal(const FVector2D& NewGoal)
{
	Goal = NewGoal;
	if (IsValid(GoalActor))
	{
		GoalActor->SetActorLocation(FVector(Goal, GoalActor->GetActorLocation().Z));
	}
}

rlmesh::Value URLMeshChasePointComponent::Observe() const
{
	const FVector2D Offset = GoalOffset();
	const float Observation[2] = {static_cast<float>(Offset.X), static_cast<float>(Offset.Y)};
	return rlmesh::Tensor(Observation, sizeof(Observation), {2}, rlmesh::DType::Float32);
}
