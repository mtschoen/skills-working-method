using System;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

public static class FixtureBuild
{
    private const string ScenePath = "Assets/Scenes/Probe.unity";

    public static void Build()
    {
        string backend = ArgumentAfter("-backend") ?? "mono";
        string outputDirectory = ArgumentAfter("-outDir") ?? "Build";

        ScriptingImplementation implementation = backend == "il2cpp"
            ? ScriptingImplementation.IL2CPP
            : ScriptingImplementation.Mono2x;
        PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, implementation);

        Scene scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
        var probe = new GameObject("DamageProbe");
        probe.AddComponent<DamageProbe>();
        System.IO.Directory.CreateDirectory("Assets/Scenes");
        EditorSceneManager.SaveScene(scene, ScenePath);

        var options = new BuildPlayerOptions
        {
            scenes = new[] { ScenePath },
            locationPathName = outputDirectory + "/FixtureProject.exe",
            target = BuildTarget.StandaloneWindows64,
            options = BuildOptions.None,
        };
        BuildReport report = BuildPipeline.BuildPlayer(options);
        if (report.summary.result != BuildResult.Succeeded)
        {
            throw new Exception("FixtureBuild failed: " + report.summary.result);
        }
        Debug.Log("FixtureBuild succeeded: " + backend + " -> " + outputDirectory);
    }

    private static string ArgumentAfter(string flag)
    {
        string[] arguments = Environment.GetCommandLineArgs();
        for (int index = 0; index < arguments.Length - 1; index++)
        {
            if (arguments[index] == flag)
            {
                return arguments[index + 1];
            }
        }
        return null;
    }
}
