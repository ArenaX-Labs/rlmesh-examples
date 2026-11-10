// Copyright (c) 2026 ArenaX Labs

using UnrealBuildTool;

public class RLmeshSim : ModuleRules
{
	public RLmeshSim(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		// rlmesh.hpp reports failures as C++ exceptions.
		bEnableExceptions = true;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",
			"RLMeshUnreal",
		});

		PrivateDependencyModuleNames.AddRange(new string[] { });
	}
}
