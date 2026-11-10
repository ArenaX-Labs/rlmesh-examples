// Copyright (c) 2026 ArenaX Labs

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "PlayerPawn.generated.h"

class UCameraComponent;
class UFloatingPawnMovement;
class USceneComponent;

/**
 * Fly camera with Unreal Editor-style viewport controls:
 * RMB look + WASD/QE fly, scroll dolly, MMB pan.
 */
UCLASS()
class RLMESHSIM_API APlayerPawn : public APawn
{
	GENERATED_BODY()

public:
	APlayerPawn();

	virtual void Tick(float DeltaTime) override;
	virtual void PossessedBy(AController* NewController) override;
	virtual void UnPossessed() override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera")
	TObjectPtr<USceneComponent> Root;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera")
	TObjectPtr<UCameraComponent> Camera;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Movement")
	TObjectPtr<UFloatingPawnMovement> Movement;

	/** Units per second while flying with RMB + WASD/QE. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Camera|Controls", meta = (ClampMin = "1.0"))
	float MoveSpeed = 1200.f;

	/** Degrees per mouse-pixel while looking with RMB. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Camera|Controls", meta = (ClampMin = "0.01"))
	float LookSensitivity = 0.15f;

	/** Units of dolly per mouse-wheel notch. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Camera|Controls", meta = (ClampMin = "1.0"))
	float ZoomSpeed = 200.f;

	/** Units of pan per mouse-pixel while holding MMB. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Camera|Controls", meta = (ClampMin = "0.01"))
	float PanSpeed = 2.f;

private:
	void ApplyEditorStyleInput(float DeltaTime);
	void UpdateMouseCapture(APlayerController* PC, bool bCapturing);
};
