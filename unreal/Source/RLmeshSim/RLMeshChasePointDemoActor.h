// Copyright (c) 2026 ArenaX Labs

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RLMeshChasePointDemoActor.generated.h"

class UStaticMeshComponent;
class URLMeshChasePointComponent;

/**
 * Visible cube with a URLMeshChasePointComponent (CreateDefaultSubobject).
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
	TObjectPtr<URLMeshChasePointComponent> ChasePoint;

	/** Optional level actor used as the Chase Point goal (world XY). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "RLMesh")
	TObjectPtr<AActor> GoalActor;
};
