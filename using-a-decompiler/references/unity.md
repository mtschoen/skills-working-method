# Unity: Mono players, IL2CPP players, Editor and Engine

Covers reading a Unity player built with the Mono backend, one built with IL2CPP, and the
Editor and Engine binaries. The Mono and IL2CPP sections were verified on Windows on 2026-10-06
against players built from this skill's own fixture (`evals/fixtures/unity/`, Unity 6000.0.64f1,
Win64) with ilspycmd 11.1, Cpp2IL 2022.1.0-pre-release.21 and Ghidra 11.4.2. Linux and macOS
are unverified for the Unity paths. Replace `PLAYER/` with the player folder.

## Which build is it

- `PLAYER/<Name>_Data/Managed/Assembly-CSharp.dll` present: Mono backend. The managed code is
  real IL; ilspycmd reads it directly.
- `PLAYER/GameAssembly.dll` plus `PLAYER/<Name>_Data/il2cpp_data/Metadata/global-metadata.dat`,
  and no `Managed/` folder: IL2CPP backend. The C# was compiled to C++ and then to native code;
  names live in the metadata file, logic lives in `GameAssembly.dll`.

Both players are Tier 1 when the owner built them. A player the owner did not build is Tier 2
(or Tier 3 if the purpose is defeating a protection); see `when-to-decompile.md`.

## Mono player

File: `PLAYER/<Name>_Data/Managed/Assembly-CSharp.dll`. Tool: ilspycmd. Platform: Windows
(verified); the commands are platform-neutral.

```bash
ilspycmd -l c PLAYER/FixtureProject_Data/Managed/Assembly-CSharp.dll
ilspycmd -t CombatMath PLAYER/FixtureProject_Data/Managed/Assembly-CSharp.dll
```

Output head of the listing on the fixture player:

```text
Class <Module>
Class CombatMath
Class DamageProbe
Class UnitySourceGeneratedAssemblyMonoScriptTypes_v1
Class <PrivateImplementationDetails>
```

Output of the one-type decompile:

```csharp
public static class CombatMath
{
    public static int ApplyDamage(int health, int rawDamage, float armorFraction)
    {
        int num = Mathf.RoundToInt((float)rawDamage * (1f - armorFraction));
        int num2 = health - num;
        if (num2 >= 0)
        {
            return num2;
        }
        return 0;
    }
}
```

The formula is intact. Local names are decompiler-invented (`num`, `num2`) because a player
ships no pdb, and the clamp comes back as `>= 0` with an early return rather than the source's
ternary. The UnityEngine reference assemblies sit in the same `Managed` folder; the fixture run
resolved them without `-r`. Add `-r PLAYER/FixtureProject_Data/Managed` if a type comes back
unresolved.

## IL2CPP player

Artifacts: `PLAYER/GameAssembly.dll` (10 MB for the one-script fixture) and
`PLAYER/<Name>_Data/il2cpp_data/Metadata/global-metadata.dat`. Two tools, in order.

### Step 1: Cpp2IL for names, signatures, and addresses

Cpp2IL is a single-file release. Download the asset for the platform from the release page into
its own empty folder outside the repository and run it by path. Platform: Windows (verified).

```bash
Cpp2IL-2022.1.0-pre-release.21-Windows.exe --list-output-formats
Cpp2IL-2022.1.0-pre-release.21-Windows.exe --game-path PLAYER --exe-name FixtureProject --output-as dummydll --output-to OUT_DIR
Cpp2IL-2022.1.0-pre-release.21-Windows.exe --game-path PLAYER --exe-name FixtureProject --output-as isil --output-to OUT_DIR_ISIL
```

Paths must be absolute. The run took 1.3 s on the fixture and logged
`Determined game's unity version to be 6000.0.64f1`, `Using actual IL2CPP Metadata version 31.1`,
and `Mapping pointers to Il2CppMethodDefinitions...Processed 16220 OK`.

Output formats in this release: `dummydll`, `dll_default`, `dll_empty`, `dll_throw_null`,
`dll_il_recovery`, `diffable-cs`, `isil`, `wasmmappings`, `wasm_name_section`. There is no
Ghidra script or symbol-map format.

What each gives:

- `dummydll` writes a flat folder of stub assemblies (`Assembly-CSharp.dll`, `mscorlib.dll`,
  `UnityEngine.*.dll`, `__Generated.dll`). ilspycmd reads them; every method body is a stub:

  ```csharp
  public static int ApplyDamage(int health, int rawDamage, float armorFraction)
  {
      return 0;
  }
  ```

  The stubs carry signatures and types only. The IL is `ldc.i4.0; ret`, and the RVA ilspycmd
  shows belongs to the stub, not to `GameAssembly.dll`. `dll_il_recovery` gave `throw null`
  for this method; no logic was recovered.
- `isil` writes one text file per type (`IsilDump/Assembly-CSharp/CombatMath.txt`) with the real
  x64 disassembly of each method, including absolute addresses in jump targets and data
  references (`jne short 000000018013B140h`, `[1806A8A20h]`). It has no explicit entry-address
  line; the function's address range is read off those targets.
- `diffable-cs` has signatures only, no addresses.

### Step 2: Ghidra on GameAssembly.dll, located by address

`GameAssembly.dll` has no symbols: method names live in `global-metadata.dat`, and nothing in
Cpp2IL's output carries them into Ghidra. Every function is `FUN_<address>`, so a name filter
finds nothing and the address from the `isil` dump is the bridge. Platform: Windows (verified).

```bash
python scripts/ghidra-decompile.py PLAYER/GameAssembly.dll --output OUT/gameassembly.c --project-dir SCRATCH/ghidra-projects --filter ApplyDamage
python scripts/ghidra-decompile.py PLAYER/GameAssembly.dll --output OUT/gameassembly-range.c --project-dir SCRATCH/ghidra-projects --filter FUN_18013b
```

Measured on the fixture: the first run (import plus analysis) took 224 s and reported
`functions=0 unnamed=0`; the second reused the project (`-process`, 5.1 s) and reported
`functions=13 unnamed=13 (no symbols: expect FUN_ names)`. Among the 13: `FUN_18013b100` with
signature `int (int,int,float)` is `ApplyDamage`; `FUN_18013b200`, void with no arguments, is
`DamageProbe.Start`.

Real decompiled lines from `FUN_18013b100`:

```c
param_3 = DAT_1806a8a20 - param_3;
...
if (param_3 * (float)param_2 < 0.0) {
  dVar1 = (double)FUN_18010ac80();
...
param_1 = param_1 - (int)local_28;
if (param_1 < 0) {
  param_1 = 0;
}
return param_1;
```

Reading it: `DAT_1806a8a20 - param_3` is `1f - armorFraction` (the constant sits in the data
section); `param_3 * (float)param_2` is `rawDamage * (1 - armor)`; the `FUN_18010ac80` family
is the inlined `Mathf.RoundToInt`; the final `if` is the `< 0 ? 0` clamp. The `0.25f` from the
call site is not in `ApplyDamage`: the compiler inlined the call into `DamageProbe.Start` and
folded the product into a data constant, so `FUN_18013b200` contains `100 - (int)local_res20`
with the literal `100` and a load from `DAT_1806a8a38`. The optimizer, not the reader, moved
the argument.

Il2CppDumper (winget `Perfare.Il2CppDumper`) emits `script.json` and a Ghidra script that apply
method names inside Ghidra. It was not exercised; when names in Ghidra matter more than a quick
address lookup, it is the tool to try.

## Burst

Not exercised. Burst-compiled jobs leave `Assembly-CSharp.dll` as ordinary IL (the job structs
and their `Execute` methods decompile with ilspycmd) while the compiled job bodies ship as native
code in `lib_burst_generated.dll` under the player's `<Name>_Data/Plugins/` folder. That native library is a Ghidra target like
any other, with no symbols and no metadata file to recover names from.

## Editor and Engine

- Managed `UnityEngine.*.dll` and `UnityEditor.*.dll`: read Unity's published C# reference
  source (UnityCsReference on GitHub) at the tag matching the editor version first. It is public
  under a reference-only license that permits reading it to understand your own project.
  Decompile the shipped dll only to confirm the binary matches the reference. Methods that bottom
  out in native code appear there as `extern`, and the reference source will not show further.
- Native `UnityPlayer.dll`, the editor executable, and the engine modules: Ghidra, and Tier 2.
  They are Unity's code, legitimately possessed through the license; write the justification and
  ask once.
- Unity's Mono runtime (`MonoBleedingEdge/`): the fork is public on GitHub; read it there.

## Unity-bundled monodis

- Windows editors: `Editor/Data/MonoBleedingEdge/bin/monodis` is a macOS Mach-O binary and does
  not run, directly or under `mono.exe` (`File does not contain a valid CIL image`).
  `lib/mono/4.5/ikdasm.exe` under the bundled `mono.exe` works, but `dotnet il dasm` covers the
  same need. Platform: Windows (verified).
- macOS and Linux editors: not checked. Treat monodis there as unverified.

## Traps

1. A relative `-outDir` passed to the editor is resolved against the project folder, not the
   shell's working directory. The fixture generator resolves `--out` to an absolute path first.
2. Cpp2IL needs absolute paths for `--game-path` and `--output-to`, and creates a `Plugins/`
   folder in the current directory. Run it from a scratch folder.
3. Cpp2IL `dummydll` stubs carry no address attributes. The address comes from the `isil` dump.
4. A Ghidra `--filter` by method name on `GameAssembly.dll` returns zero functions; filter on
   the `FUN_<address prefix>` instead, after the import has run once.
5. The IL2CPP import of a 10 MB `GameAssembly.dll` took 224 s; run it in the background. Re-runs
   against the kept project take seconds.
6. Inlining moves arguments: a constant you expect inside a method may sit in its caller, folded
   into a data constant.
7. The Mono player's `ilspycmd` output has decompiler-invented local names; a player ships no pdb.
