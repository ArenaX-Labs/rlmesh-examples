// Copyright (c) 2026 ArenaX Labs

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RLMeshChasePointDemoActor.generated.h"

class UStaticMeshComponent;
class UActorComponent;

/**
 * Visible cube that attaches URLMeshChasePointComponent at BeginPlay and
 * serves the Chase Point env. Avoids including rlmesh.hpp in this module.
 */
UCLASS()
class RLMESHSIM_API ARLMeshChasePointDemoActor : public AActor
{
	GENERATED_BODY()

public:
	ARLMeshChasePointDemoActor();

protected:
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "RLMesh")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "RLMesh")
	TObjectPtr<UActorComponent> ChasePoint;

	/**
	 * Optional level actor used as the Chase Point goal (world XY).
	 * Copied onto URLMeshChasePointComponent::GoalActor at BeginPlay.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "RLMesh")
	TObjectPtr<AActor> GoalActor;
};
