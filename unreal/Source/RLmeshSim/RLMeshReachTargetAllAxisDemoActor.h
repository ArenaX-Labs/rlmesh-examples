// Copyright (c) 2026 ArenaX Labs

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RLMeshReachTargetAllAxisDemoActor.generated.h"

class UStaticMeshComponent;
class URLMeshReachTargetAllAxisComponent;

/**
 * Visible cube with a URLMeshReachTargetAllAxisComponent (CreateDefaultSubobject).
 * Serves Unreal-ReachTargetAllAxis-v0.
 */
UCLASS()
class RLMESHSIM_API ARLMeshReachTargetAllAxisDemoActor : public AActor
{
	GENERATED_BODY()

public:
	ARLMeshReachTargetAllAxisDemoActor();

protected:
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "RLMesh")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "RLMesh")
	TObjectPtr<URLMeshReachTargetAllAxisComponent> ReachTarget;

	/**
	 * Optional level actor used as the goal (world XYZ).
	 * Copied onto URLMeshReachTargetAllAxisComponent::TargetActor at BeginPlay.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "RLMesh")
	TObjectPtr<AActor> TargetActor;
};
