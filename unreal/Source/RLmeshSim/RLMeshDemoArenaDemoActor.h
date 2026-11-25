#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

#include "RLMeshDemoArenaDemoActor.generated.h"

class UStaticMeshComponent;
class URLMeshDemoArenaComponent;

// TODO: GameScene_Demo places this actor; once the map holds a cube with the component instead, delete this class.
UCLASS()
class RLMESHSIM_API ARLMeshDemoArenaDemoActor : public AActor
{
	GENERATED_BODY()

public:
	ARLMeshDemoArenaDemoActor();

protected:
	UPROPERTY(VisibleAnywhere, Category = "RLMesh")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, Category = "RLMesh")
	TObjectPtr<URLMeshDemoArenaComponent> DemoArena;
};
