#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

#include "RLMeshReachTargetAllAxisDemoActor.generated.h"

class UStaticMeshComponent;
class URLMeshReachTargetAllAxisComponent;

// TODO: GameScene places this actor; once the map holds a cube with the component instead, delete this class.
UCLASS()
class RLMESHSIM_API ARLMeshReachTargetAllAxisDemoActor : public AActor
{
	GENERATED_BODY()

public:
	ARLMeshReachTargetAllAxisDemoActor();

protected:
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere, Category = "RLMesh")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, Category = "RLMesh")
	TObjectPtr<URLMeshReachTargetAllAxisComponent> ReachTarget;

	/** Copied to the component's TargetActor, where GameScene saved it. */
	UPROPERTY(EditAnywhere, Category = "RLMesh")
	TObjectPtr<AActor> TargetActor;
};
