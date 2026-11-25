#include "RLMeshDemoArenaDemoActor.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "RLMeshDemoArenaComponent.h"
#include "UObject/ConstructorHelpers.h"

ARLMeshDemoArenaDemoActor::ARLMeshDemoArenaDemoActor()
{
	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	SetRootComponent(Mesh);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> Blue(TEXT("/Game/Blue.Blue"));
	Mesh->SetStaticMesh(Cube.Object);
	Mesh->SetMaterial(0, Blue.Object);
	Mesh->SetWorldScale3D(FVector(0.5f));

	DemoArena = CreateDefaultSubobject<URLMeshDemoArenaComponent>(TEXT("DemoArena"));
}
