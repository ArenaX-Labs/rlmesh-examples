#include "RLMeshChasePointComponent.h"

#include "Components/SceneComponent.h"
#include "GameFramework/Actor.h"

#include <limits>
#include <vector>

URLMeshChasePointComponent::URLMeshChasePointComponent()
{
	EnvId = TEXT("Unreal-ChasePoint-v0");
}

void URLMeshChasePointComponent::BeginPlay()
{
	Start = GetOwner()->GetActorLocation();
	if (IsValid(GoalActor))
	{
		// Steps move the goal, which a Static root refuses.
		if (USceneComponent* Root = GoalActor->GetRootComponent())
		{
			Root->SetMobility(EComponentMobility::Movable);
		}
		GoalHome = FVector2D(GoalActor->GetActorLocation());
	}
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

rlmesh::ResetResult URLMeshChasePointComponent::ResetEnv(std::optional<int64_t>, const std::optional<rlmesh::InfoDict>&)
{
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
	const std::vector<float> D = rlmesh::ext::to_vector<float>(Action->as_tensor());
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
	return rlmesh::ext::from_vector<float>({static_cast<float>(Offset.X), static_cast<float>(Offset.Y)}, {2});
}
