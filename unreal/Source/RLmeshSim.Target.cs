// Copyright (c) 2026 ArenaX Labs

using UnrealBuildTool;
using System.Collections.Generic;

public class RLmeshSimTarget : TargetRules
{
	public RLmeshSimTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V5;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_6;
		ExtraModuleNames.Add("RLmeshSim");
	}
}
