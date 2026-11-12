// Copyright (c) 2026 ArenaX Labs

#include "RLmeshSim.h"

#include "Modules/ModuleManager.h"
#include "RLMeshDemoControl.h"

#if WITH_EDITOR
#include "Containers/Ticker.h"
#include "Editor.h"
#include "Misc/CoreDelegates.h"
#endif

class FRLmeshSimModule : public FDefaultGameModuleImpl
{
public:
	virtual void StartupModule() override
	{
		FDefaultGameModuleImpl::StartupModule();
#if WITH_EDITOR
		if (GIsEditor)
		{
			// Start demo control after the editor/Python plugin are ready so
			// host clients can load a scenario before the first Play.
			PostEngineInitHandle = FCoreDelegates::OnPostEngineInit.AddLambda(
				[]()
				{
					FTSTicker::GetCoreTicker().AddTicker(
						FTickerDelegate::CreateLambda(
							[](float)
							{
								RLMeshEnsureDemoControlServer();
								return false; // one-shot
							}),
						1.0f);
				});

			BeginPIEHandle = FEditorDelegates::PostPIEStarted.AddLambda(
				[](const bool /*bIsSimulating*/)
				{
					RLMeshEnsureDemoControlServer();
				});
		}
#endif
	}

	virtual void ShutdownModule() override
	{
#if WITH_EDITOR
		if (PostEngineInitHandle.IsValid())
		{
			FCoreDelegates::OnPostEngineInit.Remove(PostEngineInitHandle);
			PostEngineInitHandle.Reset();
		}
		if (BeginPIEHandle.IsValid())
		{
			FEditorDelegates::PostPIEStarted.Remove(BeginPIEHandle);
			BeginPIEHandle.Reset();
		}
#endif
		FDefaultGameModuleImpl::ShutdownModule();
	}

private:
#if WITH_EDITOR
	FDelegateHandle PostEngineInitHandle;
	FDelegateHandle BeginPIEHandle;
#endif
};

IMPLEMENT_PRIMARY_GAME_MODULE(FRLmeshSimModule, RLmeshSim, "RLmeshSim");
