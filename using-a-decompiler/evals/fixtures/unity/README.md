# Unity fixture

A one-script Unity project built twice, as a Mono and an IL2CPP Windows 64-bit
player, so the Unity reference can be exercised against our own players.

`Assets/Scripts/DamageProbe.cs` holds `CombatMath.ApplyDamage`, a small damage
formula with an armor multiplier and a clamp at zero. `Assets/Editor/FixtureBuild.cs`
is the batch-mode build entry point.

## Run

```bash
python make-unity-fixture.py --editor PATH/TO/Unity.exe --out SCRATCH_DIR [--backends mono,il2cpp]
```

The editor must have the Windows IL2CPP module installed, and IL2CPP builds need
Visual Studio with the C++ workload. Pass the editor path on the command line;
it is machine-specific and never stored here.

## Output

Everything lands in the scratch directory: `FixtureProject/`, `create.log`,
`build-mono.log`, `build-il2cpp.log`, `player-mono/` and `player-il2cpp/`.
Nothing built is committed.
