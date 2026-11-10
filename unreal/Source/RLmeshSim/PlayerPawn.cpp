// Copyright (c) 2026 ArenaX Labs

#include "PlayerPawn.h"

#include "Camera/CameraComponent.h"
#include "Components/SceneComponent.h"
#include "GameFramework/FloatingPawnMovement.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"

APlayerPawn::APlayerPawn()
{
	PrimaryActorTick.bCanEverTick = true;

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(Root);
	Camera->bUsePawnControlRotation = true;

	Movement = CreateDefaultSubobject<UFloatingPawnMovement>(TEXT("Movement"));
	Movement->MaxSpeed = MoveSpeed;

	bUseControllerRotationYaw = true;
	bUseControllerRotationPitch = true;
	bUseControllerRotationRoll = false;
}

void APlayerPawn::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	ApplyEditorStyleInput(DeltaTime);
}

void APlayerPawn::PossessedBy(AController* NewController)
{
	Super::PossessedBy(NewController);

	if (APlayerController* PC = Cast<APlayerController>(NewController))
	{
		PC->bShowMouseCursor = true;
		PC->bEnableClickEvents = false;
		PC->bEnableMouseOverEvents = false;

		FInputModeGameAndUI InputMode;
		InputMode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
		InputMode.SetHideCursorDuringCapture(false);
		PC->SetInputMode(InputMode);

		UpdateMouseCapture(PC, false);
	}
}

void APlayerPawn::UnPossessed()
{
	if (APlayerController* PC = Cast<APlayerController>(Controller))
	{
		UpdateMouseCapture(PC, false);
		PC->bShowMouseCursor = true;
	}

	Super::UnPossessed();
}

void APlayerPawn::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);
	// Chorded editor-style input is polled in Tick.
}

void APlayerPawn::ApplyEditorStyleInput(float DeltaTime)
{
	APlayerController* PC = Cast<APlayerController>(Controller);
	if (!PC || !PC->PlayerInput)
	{
		return;
	}

	const bool bRightMouse = PC->IsInputKeyDown(EKeys::RightMouseButton);
	const bool bMiddleMouse = PC->IsInputKeyDown(EKeys::MiddleMouseButton);
	const bool bCapturing = bRightMouse || bMiddleMouse;

	UpdateMouseCapture(PC, bCapturing);
	PC->bShowMouseCursor = !bCapturing;

	float MouseX = 0.f;
	float MouseY = 0.f;
	PC->GetInputMouseDelta(MouseX, MouseY);

	if (bRightMouse)
	{
		AddControllerYawInput(MouseX * LookSensitivity);
		AddControllerPitchInput(-MouseY * LookSensitivity);

		FVector LocalMove = FVector::ZeroVector;
		if (PC->IsInputKeyDown(EKeys::W))
		{
			LocalMove.X += 1.f;
		}
		if (PC->IsInputKeyDown(EKeys::S))
		{
			LocalMove.X -= 1.f;
		}
		if (PC->IsInputKeyDown(EKeys::D))
		{
			LocalMove.Y += 1.f;
		}
		if (PC->IsInputKeyDown(EKeys::A))
		{
			LocalMove.Y -= 1.f;
		}
		if (PC->IsInputKeyDown(EKeys::E))
		{
			LocalMove.Z += 1.f;
		}
		if (PC->IsInputKeyDown(EKeys::Q))
		{
			LocalMove.Z -= 1.f;
		}

		if (!LocalMove.IsNearlyZero())
		{
			LocalMove.Normalize();
			const FRotator ControlRot = GetControlRotation();
			const FRotationMatrix RotMatrix(ControlRot);
			const FVector WorldMove =
				RotMatrix.GetScaledAxis(EAxis::X) * LocalMove.X +
				RotMatrix.GetScaledAxis(EAxis::Y) * LocalMove.Y +
				FVector::UpVector * LocalMove.Z;

			AddMovementInput(WorldMove, 1.f);
			if (Movement)
			{
				Movement->MaxSpeed = MoveSpeed;
			}
		}
	}

	if (bMiddleMouse)
	{
		const FRotator ControlRot = GetControlRotation();
		const FRotationMatrix RotMatrix(ControlRot);
		const FVector Right = RotMatrix.GetScaledAxis(EAxis::Y);
		const FVector Up = RotMatrix.GetScaledAxis(EAxis::Z);
		const FVector PanOffset = (-Right * MouseX + Up * MouseY) * PanSpeed;
		AddActorWorldOffset(PanOffset, false);
	}

	const float WheelDelta = PC->GetInputAnalogKeyState(EKeys::MouseWheelAxis);
	if (!FMath::IsNearlyZero(WheelDelta))
	{
		const FVector Forward = GetControlRotation().Vector();
		AddActorWorldOffset(Forward * WheelDelta * ZoomSpeed, false);
	}
}

void APlayerPawn::UpdateMouseCapture(APlayerController* PC, bool bCapturing)
{
	if (!PC)
	{
		return;
	}

	if (bCapturing)
	{
		PC->SetIgnoreLookInput(false);
		FInputModeGameOnly InputMode;
		InputMode.SetConsumeCaptureMouseDown(true);
		PC->SetInputMode(InputMode);
	}
	else
	{
		FInputModeGameAndUI InputMode;
		InputMode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
		InputMode.SetHideCursorDuringCapture(false);
		PC->SetInputMode(InputMode);
	}
}
