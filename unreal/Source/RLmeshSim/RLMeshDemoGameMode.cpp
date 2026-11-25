#include "RLMeshDemoGameMode.h"

#include "PlayerPawn.h"

ARLMeshDemoGameMode::ARLMeshDemoGameMode()
{
	DefaultPawnClass = APlayerPawn::StaticClass();
}
