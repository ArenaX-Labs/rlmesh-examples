#include "RLMeshDemoArenaComponent.h"

#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Actor.h"

#include <limits>
#include <vector>

URLMeshDemoArenaComponent::URLMeshDemoArenaComponent()
{
	EnvId = TEXT("Unreal-DemoArena-v0");
}

void URLMeshDemoArenaComponent::BeginPlay()
{
	// Steps move the owner, which a Static root refuses.
	if (USceneComponent* Root = GetOwner()->GetRootComponent())
	{
		Root->SetMobility(EComponentMobility::Movable);
	}
	Start = GetOwner()->GetActorLocation();

	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		AActor* Actor = *It;
		const FString Class = Actor->GetClass()->GetName();
		if (Actor == GetOwner())
		{
			continue;
		}
		if (!Goal && Class.Contains(TEXT("Goal")))
		{
			Goal = Actor;
		}
		else if (Coins.Num() < NumCoins && Class.Contains(TEXT("Coin")))
		{
			Coins.Add(Actor);
		}
		else if (Obstacles.Num() < NumObstacles && Class.Contains(TEXT("Obstacle")))
		{
			Obstacles.Add(Actor);
		}
	}
	// The agent collects a pickup by moving onto it, so pickups must not block its sweeps.
	for (AActor* Pickup : Pickups())
	{
		Pickup->SetActorEnableCollision(false);
	}
	Super::BeginPlay();
}

rlmesh::spaces::Space URLMeshDemoArenaComponent::ObservationSpace() const
{
	const double Infinity = std::numeric_limits<double>::infinity();
	return rlmesh::spaces::Dict({
		{"goal", rlmesh::spaces::Box(-Infinity, Infinity, {2}).spec()},
		{"coins", rlmesh::spaces::Box(-Infinity, Infinity, {NumCoins, 2}).spec()},
		{"obstacles", rlmesh::spaces::Box(-Infinity, Infinity, {NumObstacles, 2}).spec()},
		{"walls", rlmesh::spaces::Box(0.0, WallSenseRange, {NumWallRays}).spec()},
	});
}

rlmesh::spaces::Space URLMeshDemoArenaComponent::ActionSpace() const
{
	return rlmesh::spaces::Box(-1.0, 1.0, {2});
}

rlmesh::ResetResult URLMeshDemoArenaComponent::ResetEnv(std::optional<int64_t>, const std::optional<rlmesh::InfoDict>&)
{
	GetOwner()->SetActorLocation(Start);
	for (AActor* Pickup : Pickups())
	{
		Pickup->SetActorHiddenInGame(false);
	}
	Steps = 0;
	return {Observe(), {}};
}

rlmesh::StepResult URLMeshDemoArenaComponent::StepEnv(const std::optional<rlmesh::Value>& Action)
{
	const rlmesh::Tensor Direction = Action.value().as_tensor();
	if (Direction.dtype() != rlmesh::DType::Float32 || Direction.size() != 2)
	{
		throw rlmesh::RecoverableEnvironmentException("step needs a float32 action of shape (2,)");
	}
	const float* D = reinterpret_cast<const float*>(Direction.buffer().data());
	const FVector2D Heading = FVector2D(D[0], D[1]).GetSafeNormal();

	// Stop on the nearest pickup rather than stepping past it.
	double Travel = StepSize;
	if (const AActor* Target = NearestPickup())
	{
		const FVector2D ToTarget = OffsetTo(Target);
		if (FVector2D::DotProduct(Heading, ToTarget) > 0.0)
		{
			Travel = FMath::Min(Travel, ToTarget.Size());
		}
	}
	const FVector To = GetOwner()->GetActorLocation() + FVector(Heading * Travel, 0.0);
	FHitResult Hit;
	GetOwner()->SetActorLocation(To, true, &Hit);
	// Grazing the floor would stop every sweep; only walls block.
	if (Hit.bBlockingHit && Hit.ImpactNormal.Z > 0.7)
	{
		GetOwner()->SetActorLocation(To);
	}
	++Steps;

	const bool bHitObstacle = TouchesObstacle();
	int32 Collected = 0;
	if (!bHitObstacle)
	{
		for (AActor* Pickup : Pickups())
		{
			if (!Pickup->IsHidden() && OffsetTo(Pickup).Size() <= PickupRadius)
			{
				Pickup->SetActorHiddenInGame(true);
				++Collected;
			}
		}
	}

	const AActor* Remaining = NearestPickup();
	const double Reward = Collected - (Remaining ? OffsetTo(Remaining).Size() / GoalRange : 0.0);
	const bool bTerminated = bHitObstacle || !Remaining;
	const bool bSuccess = !bHitObstacle && !Remaining;
	return {Observe(), Reward, bTerminated, !bTerminated && Steps >= MaxSteps, {{"success", bSuccess}}};
}

FVector2D URLMeshDemoArenaComponent::OffsetTo(const AActor* Actor) const
{
	if (!Actor || Actor->IsHidden())
	{
		return FVector2D::ZeroVector;
	}
	return FVector2D(Actor->GetActorLocation() - GetOwner()->GetActorLocation());
}

TArray<AActor*> URLMeshDemoArenaComponent::Pickups() const
{
	TArray<AActor*> Out;
	for (AActor* Coin : Coins)
	{
		Out.Add(Coin);
	}
	if (Goal)
	{
		Out.Add(Goal.Get());
	}
	return Out;
}

AActor* URLMeshDemoArenaComponent::NearestPickup() const
{
	AActor* Nearest = nullptr;
	double NearestDistance = std::numeric_limits<double>::infinity();
	for (AActor* Pickup : Pickups())
	{
		if (!Pickup->IsHidden() && OffsetTo(Pickup).Size() < NearestDistance)
		{
			Nearest = Pickup;
			NearestDistance = OffsetTo(Pickup).Size();
		}
	}
	return Nearest;
}

bool URLMeshDemoArenaComponent::TouchesObstacle() const
{
	const double Reach = AgentHalfExtent + ObstacleHalfExtent;
	for (const AActor* Obstacle : Obstacles)
	{
		const FVector2D Offset = OffsetTo(Obstacle);
		if (FMath::Abs(Offset.X) <= Reach && FMath::Abs(Offset.Y) <= Reach)
		{
			return true;
		}
	}
	return false;
}

rlmesh::Value URLMeshDemoArenaComponent::Observe() const
{
	const FVector2D GoalOffset = OffsetTo(Goal);
	const float GoalXY[2] = {static_cast<float>(GoalOffset.X), static_cast<float>(GoalOffset.Y)};

	std::vector<float> CoinXY(2 * NumCoins, 0.f);
	for (int32 i = 0; i < Coins.Num(); ++i)
	{
		const FVector2D Offset = OffsetTo(Coins[i]);
		CoinXY[2 * i] = static_cast<float>(Offset.X);
		CoinXY[2 * i + 1] = static_cast<float>(Offset.Y);
	}

	std::vector<float> ObstacleXY(2 * NumObstacles, 0.f);
	for (int32 i = 0; i < Obstacles.Num(); ++i)
	{
		const FVector2D Offset = OffsetTo(Obstacles[i]);
		ObstacleXY[2 * i] = static_cast<float>(Offset.X);
		ObstacleXY[2 * i + 1] = static_cast<float>(Offset.Y);
	}

	std::vector<float> Walls(NumWallRays, WallSenseRange);
	const FVector Origin = GetOwner()->GetActorLocation();
	const FCollisionQueryParams Params(SCENE_QUERY_STAT(DemoArenaWalls), false, GetOwner());
	for (int32 i = 0; i < NumWallRays; ++i)
	{
		const double Angle = 2.0 * UE_DOUBLE_PI * i / NumWallRays;
		const FVector End = Origin + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.0) * WallSenseRange;
		FHitResult Hit;
		if (GetWorld()->LineTraceSingleByChannel(Hit, Origin, End, ECC_Visibility, Params))
		{
			Walls[i] = Hit.Distance;
		}
	}

	const size_t CoinCount = static_cast<size_t>(NumCoins);
	const size_t ObstacleCount = static_cast<size_t>(NumObstacles);
	const size_t RayCount = static_cast<size_t>(NumWallRays);
	return rlmesh::Metadata{
		{"goal", rlmesh::Tensor(GoalXY, sizeof(GoalXY), {2}, rlmesh::DType::Float32)},
		{"coins", rlmesh::Tensor(CoinXY.data(), CoinXY.size() * sizeof(float), {CoinCount, 2}, rlmesh::DType::Float32)},
		{"obstacles", rlmesh::Tensor(ObstacleXY.data(), ObstacleXY.size() * sizeof(float), {ObstacleCount, 2},
									 rlmesh::DType::Float32)},
		{"walls", rlmesh::Tensor(Walls.data(), Walls.size() * sizeof(float), {RayCount}, rlmesh::DType::Float32)},
	};
}
