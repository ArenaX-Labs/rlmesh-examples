// Copyright (c) 2026 ArenaX Labs

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RLMeshAvoidHazardsDemoActor.generated.h"

class UStaticMeshComponent;
class UActorComponent;

/**
 * Visible cube that attaches URLMeshAvoidHazardsComponent at BeginPlay.
 */
UCLASS()
class RLMESHSIM_API ARLMeshAvoidHazardsDemoActor : public AActor
{
	GENERATED_BODY()

public:
	ARLMeshAvoidHazardsDemoActor();

protected:
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "RLMesh")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "RLMesh")
	TObjectPtr<UActorComponent> AvoidHazards;

	/** Optional level actor used as the Avoid Hazards goal (world XY). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "RLMesh")
	TObjectPtr<AActor> GoalActor;
};
