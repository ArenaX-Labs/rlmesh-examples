// Copyright (c) 2026 ArenaX Labs

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RLMeshReachDemoActor.generated.h"

class UStaticMeshComponent;
class UActorComponent;

/**
 * Visible cube that attaches URLMeshReachTargetComponent at BeginPlay and
 * serves the Reach Target env. Avoids including rlmesh.hpp in this module.
 */
UCLASS()
class RLMESHSIM_API ARLMeshReachDemoActor : public AActor
{
	GENERATED_BODY()

public:
	ARLMeshReachDemoActor();

protected:
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "RLMesh")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "RLMesh")
	TObjectPtr<UActorComponent> ReachTarget;
};
