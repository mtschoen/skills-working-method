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
ternary. The fixture run passed no `-r` and the decompile came back complete (`Mathf.RoundToInt`
resolved); the UnityEngine assemblies sit in the same `Managed` folder. If a type ever comes back
unresolved, `-r PLAYER/FixtureProject_Data/Managed` is the documented flag (not needed here).

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

The `isil` line is the `dummydll` command with the format and output folder swapped; the lane
ran it that way. Both runs used absolute paths (relative ones were not tried). The `dummydll`
run took 1.3 s on the fixture and logged
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
  references (`jne short 000000018013B140h`, `[1806A8A20h]`).
  Important: The pinned Cpp2IL ISIL exporter provides no instruction-address column or explicit
  entry-address line. Inferring an address prefix from local jump targets is only a candidate-search
  heuristic:
  1. A branchless method has no local jump targets at all.
  2. A tail jump or call targets another function entirely.
  3. Internal branches may cross prefix boundaries relative to the method entry.
  When usable local jump targets are absent or ambiguous, a verified entry mapping (such as
  Il2CppDumper or explicit metadata RVA lookup) is required.
- `diffable-cs` has signatures only, no addresses.

### Step 2: Ghidra on GameAssembly.dll, located by address

`GameAssembly.dll` has no symbols: method names live in `global-metadata.dat`, and nothing in
Cpp2IL's output carries them into Ghidra. Every function is `FUN_<address>`, so a name filter
finds nothing. Ghidra's `--filter` matches function entry names (`FUN_<entry_address>`), not
functions that merely contain an address.

When using candidate address prefixes from `isil` jump targets to filter Ghidra:

1. Treat prefix inference as a candidate-search heuristic, not a guaranteed entry mapping.
2. Require disassembly corroboration before identifying a candidate Ghidra function: compare the
   candidate's decompiled C and assembly against the `isil` instructions, constants (such as data
   offsets like `DAT_1806a8a20`), and parameter signatures.
3. If local jump targets are absent (e.g. branchless methods) or the prefix yields no matching
   functions, use a verified entry mapping (such as Il2CppDumper's generated Ghidra script) rather
   than guessing.

Platform: Windows (verified).

```bash
python scripts/ghidra-decompile.py PLAYER/GameAssembly.dll --output OUT/gameassembly.c --project-dir SCRATCH/ghidra-projects --filter ApplyDamage
python scripts/ghidra-decompile.py PLAYER/GameAssembly.dll --output OUT/gameassembly-range.c --project-dir SCRATCH/ghidra-projects --filter FUN_18013b
```

Measured on the fixture: the first run (import plus analysis) took 224 s and reported zero
functions (the wrapper now prints `functions=0 named=0 unnamed=0 (no functions matched)` for
that case); the second reused the project (`-process`, 5.1 s) and reported 13 functions, all
unnamed (`functions=13 named=0 unnamed=13 (no symbols: every function is FUN_)`). Among the 13: `FUN_18013b100` with
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

Il2CppDumper is the other recovery tool and, by its own documentation, emits a script that
applies method names inside Ghidra. It was not exercised here (its output names and the winget
package id in `tooling-setup.md` are unverified); when names in Ghidra matter more than a quick
address lookup, it is the tool to try.

## Burst

Not exercised. By Unity's documentation, Burst leaves the job structs in `Assembly-CSharp.dll`
as ordinary IL and ships the compiled job bodies as a native library (named
`lib_burst_generated` under the player's data folder). Expect the managed side to decompile with
ilspycmd and the native library to be a Ghidra target with no symbols and no metadata file to
recover names from. Verify the file name on a real Burst player before relying on it.

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

- Windows editors: in the Unity 2022.3 editor tree checked on 2026-10-06,
  `Editor/Data/MonoBleedingEdge/bin/monodis` is a macOS Mach-O binary and does not run, directly
  or under `mono.exe` (`File does not contain a valid CIL image`). `lib/mono/4.5/ikdasm.exe`
  under the bundled `mono.exe` works, but `dotnet il dasm` covers the same need. Other editor
  versions were not checked. Platform: Windows (verified on 2022.3).
- macOS and Linux editors: not checked. Treat monodis there as unverified.

## Traps

1. A relative `-outDir` passed to the editor is resolved against the project folder, not the
   shell's working directory. The fixture generator resolves `--out` to an absolute path first.
2. Cpp2IL was run with absolute `--game-path` and `--output-to` (relative paths were not tried),
   and it creates a `Plugins/` folder in the current directory. Run it from a scratch folder.
3. Cpp2IL `dummydll` stubs carry no address attributes.
4. Cpp2IL `isil` jump targets provide only candidate address prefixes (heuristic): branchless
   methods have no local targets and branches can cross prefix boundaries. Always corroborate
   Ghidra functions against the `isil` disassembly, and require a verified entry mapping when
   local targets are absent.
5. Ghidra's `--filter` filters function entry names (`FUN_<address>`), not arbitrary contained
   addresses. A filter by method name on `GameAssembly.dll` returns zero functions.
6. The IL2CPP import of a 10 MB `GameAssembly.dll` took 224 s; run it in the background. Re-runs
   against the kept project take seconds.
7. Inlining moves arguments: a constant you expect inside a method may sit in its caller, folded
   into a data constant.
8. The Mono player's `ilspycmd` output has decompiler-invented local names; a player ships no pdb.
