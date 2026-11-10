// Copyright (c) 2026 ArenaX Labs

using UnrealBuildTool;
using System.Collections.Generic;

public class RLmeshSimEditorTarget : TargetRules
{
	public RLmeshSimEditorTarget( TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V5;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_6;
		ExtraModuleNames.Add("RLmeshSim");
	}
}
