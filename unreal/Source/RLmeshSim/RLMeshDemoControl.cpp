// Copyright (c) 2026 ArenaX Labs

#include "RLMeshDemoControl.h"

#include "Misc/Paths.h"
#include "RLmeshSim.h"

#if WITH_EDITOR
#include "IPythonScriptPlugin.h"
#endif

void RLMeshEnsureDemoControlServer()
{
#if WITH_EDITOR
	const FString ScriptPath =
		FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("Scripts/demo_control_server.py"));
	if (!FPaths::FileExists(ScriptPath))
	{
		UE_LOG(LogRLmeshSim, Warning, TEXT("Env helper: script missing at %s"), *ScriptPath);
		return;
	}

	IPythonScriptPlugin* Python = IPythonScriptPlugin::Get();
	if (!Python || !Python->IsPythonAvailable())
	{
		UE_LOG(LogRLmeshSim, Warning, TEXT("Env helper: Python editor plugin unavailable"));
		return;
	}

	const FString Cmd = FString::Printf(
		TEXT("import runpy; runpy.run_path(r'%s', run_name='__main__')"), *ScriptPath);
	if (!Python->ExecPythonCommand(*Cmd))
	{
		UE_LOG(LogRLmeshSim, Warning, TEXT("Env helper: failed to exec %s"), *ScriptPath);
		return;
	}
	UE_LOG(LogRLmeshSim, Log, TEXT("Env helper: ensured server via %s"), *ScriptPath);
#endif
}
