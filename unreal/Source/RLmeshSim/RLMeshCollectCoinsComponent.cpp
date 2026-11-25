#include "RLMeshCollectCoinsComponent.h"

#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInterface.h"
#include "UObject/UObjectGlobals.h"

#include <limits>

URLMeshCollectCoinsComponent::URLMeshCollectCoinsComponent()
{
	EnvId = TEXT("Unreal-CollectCoins-v0");
}

void URLMeshCollectCoinsComponent::BeginPlay()
{
	// Steps move the owner, which a Static root refuses.
	if (USceneComponent* Root = GetOwner()->GetRootComponent())
	{
		Root->SetMobility(EComponentMobility::Movable);
	}
	Start = GetOwner()->GetActorLocation();
	Random.GenerateNewSeed();

	UStaticMesh* Sphere = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	FActorSpawnParameters Spawn;
	Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	for (int32 i = 0; i < NumCoins; ++i)
	{
		AStaticMeshActor* Coin = GetWorld()->SpawnActor<AStaticMeshActor>(Start, FRotator::ZeroRotator, Spawn);
		UStaticMeshComponent* Mesh = Coin->GetStaticMeshComponent();
		Mesh->SetMobility(EComponentMobility::Movable);
		Mesh->SetStaticMesh(Sphere);
		Mesh->SetMaterial(0, CoinMaterial);
		Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Coin->SetActorScale3D(FVector(0.6));
		Coins.Add(Coin);
	}
	Super::BeginPlay();
}

rlmesh::spaces::Space URLMeshCollectCoinsComponent::ObservationSpace() const
{
	const double Infinity = std::numeric_limits<double>::infinity();
	return rlmesh::spaces::Dict({
		{"nearest_coin", rlmesh::spaces::Box(-Infinity, Infinity, {2}).spec()},
		{"coins_left", rlmesh::spaces::Discrete(NumCoins + 1).spec()},
	});
}

rlmesh::spaces::Space URLMeshCollectCoinsComponent::ActionSpace() const
{
	return rlmesh::spaces::Box(-1.0, 1.0, {2});
}

rlmesh::ResetResult URLMeshCollectCoinsComponent::ResetEnv(std::optional<int64_t> Seed,
														   const std::optional<rlmesh::InfoDict>&)
{
	if (Seed)
	{
		const uint64 Bits = static_cast<uint64>(*Seed);
		Random.Initialize(static_cast<int32>(Bits ^ (Bits >> 32)));
	}
	GetOwner()->SetActorLocation(Start);
	for (AActor* Coin : Coins)
	{
		const float Angle = Random.FRandRange(0.f, 2.f * UE_PI);
		const float Distance = Random.FRandRange(MinClearance, FMath::Max(MinClearance, CoinRange));
		Coin->SetActorLocation(Start + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.0) * Distance);
		Coin->SetActorHiddenInGame(false);
	}
	Steps = 0;
	return {Observe(), {}};
}

rlmesh::StepResult URLMeshCollectCoinsComponent::StepEnv(const std::optional<rlmesh::Value>& Action)
{
	const rlmesh::Tensor Direction = Action.value().as_tensor();
	if (Direction.dtype() != rlmesh::DType::Float32 || Direction.size() != 2)
	{
		throw rlmesh::RecoverableEnvironmentException("step needs a float32 action of shape (2,)");
	}
	const float* D = reinterpret_cast<const float*>(Direction.buffer().data());
	const double Travel = FMath::Min(static_cast<double>(StepSize), OffsetTo(NearestCoin()).Size());
	GetOwner()->AddActorWorldOffset(FVector(FVector2D(D[0], D[1]).GetSafeNormal() * Travel, 0.0));
	++Steps;

	int32 Collected = 0;
	for (AActor* Coin : Coins)
	{
		if (!Coin->IsHidden() && OffsetTo(Coin).Size() <= PickupRadius)
		{
			Coin->SetActorHiddenInGame(true);
			++Collected;
		}
	}
	const bool bAllCollected = CoinsLeft() == 0;
	const double Reward = Collected + (bAllCollected ? 1.0 : 0.0) - OffsetTo(NearestCoin()).Size() / CoinRange;
	return {Observe(), Reward, bAllCollected, !bAllCollected && Steps >= MaxSteps, {{"success", bAllCollected}}};
}

FVector2D URLMeshCollectCoinsComponent::OffsetTo(const AActor* Coin) const
{
	if (!Coin)
	{
		return FVector2D::ZeroVector;
	}
	return FVector2D(Coin->GetActorLocation() - GetOwner()->GetActorLocation());
}

AActor* URLMeshCollectCoinsComponent::NearestCoin() const
{
	AActor* Nearest = nullptr;
	for (AActor* Coin : Coins)
	{
		if (!Coin->IsHidden() && (!Nearest || OffsetTo(Coin).Size() < OffsetTo(Nearest).Size()))
		{
			Nearest = Coin;
		}
	}
	return Nearest;
}

int32 URLMeshCollectCoinsComponent::CoinsLeft() const
{
	int32 Left = 0;
	for (const AActor* Coin : Coins)
	{
		Left += Coin->IsHidden() ? 0 : 1;
	}
	return Left;
}

rlmesh::Value URLMeshCollectCoinsComponent::Observe() const
{
	const FVector2D Offset = OffsetTo(NearestCoin());
	const float NearestXY[2] = {static_cast<float>(Offset.X), static_cast<float>(Offset.Y)};
	return rlmesh::Metadata{
		{"nearest_coin", rlmesh::Tensor(NearestXY, sizeof(NearestXY), {2}, rlmesh::DType::Float32)},
		{"coins_left", CoinsLeft()},
	};
}
