# Tooling setup: detect, then install

Covers installing and detecting the decompilers and disassemblers this skill drives. Windows and
Linux (Arch) were verified by discovery runs on 2026-10-06. macOS is unverified throughout.

## One command

Platform: both.

```bash
python scripts/setup-decompilers.py
python scripts/setup-decompilers.py --dry-run
python scripts/setup-decompilers.py --only ilspycmd,analyzeHeadless
```

It detects each tool, installs what it can, and prints `present`, `installed`, `failed`, `manual`
or `dryrun` per tool, then a list of manual next steps. A dry run on Windows printed:

```text
  ilspycmd         present    ...
  dotnet-il        present    ...
  analyzeHeadless  present    ...
  java             present    ... (major 26)
  dumpbin          present    ...
```

## What installs unattended

Only the two .NET global tools, user scope, no privilege. Platform: both.

```bash
dotnet tool install --global ilspycmd
dotnet tool install --global dotnet-il
```

The install of ilspycmd 11.1.0.9782 took 1.1 s on Windows, and dotnet-il 1.0.0 took 4.9 s.
Both need the .NET SDK first. Ensure the tools directory is on `PATH` (see Traps).

## What is manual

| Tool | Next step |
| --- | --- |
| Ghidra | Download the release zip from the NationalSecurityAgency/ghidra releases page, unpack it, set `GHIDRA_INSTALL_DIR` to the unpacked folder |
| Java | Install a JDK 21 or newer and put `java` on `PATH` |
| dumpbin (Windows) | Install the Visual Studio "Desktop development with C++" workload; the script finds it through vswhere |
| objdump (Linux) | Install binutils from the distro package manager |
| llvm-objdump (macOS) | Install LLVM (`brew install llvm`) |
| Cpp2IL | Download the single-file release and drop it on `PATH`. Not exercised by the discovery runs |
| Il2CppDumper | Install from winget. Not exercised by the discovery runs |

Cpp2IL release tag `2022.1.0-pre-release.21`. Windows asset
`Cpp2IL-2022.1.0-pre-release.21-Windows.exe`, Linux asset `Cpp2IL-2022.1.0-pre-release.21-Linux`.
On Windows, winget has no Cpp2IL package and has Il2CppDumper as `Perfare.Il2CppDumper`
(6.7.46 when searched).

## Per-platform availability

| Tool | Windows (verified) | Linux, Arch (verified) | macOS (unverified) |
| --- | --- | --- | --- |
| ilspycmd | installs unattended | installs unattended | unverified |
| dotnet-il | installs unattended | installs unattended, needs roll-forward | unverified |
| Ghidra headless | manual, 11.4.2 ran | absent; `ghidra` 12.1.2-2 in the Arch extra repo | unverified |
| Java | JDK 21+ (major 26 present) | OpenJDK 17 present, too old | unverified |
| dumpbin | found through vswhere, no vcvars needed | not applicable | not applicable |
| llvm-objdump | present (LLVM 22.1.0) | present (LLVM 22.1.8) | unverified |
| GNU objdump | not checked | present (binutils 2.47) | unverified |
| gdb | not checked | present (17.2) | unverified |
| monodis | Mach-O file in the Unity tree, unusable | no Mono installed | unverified |
| radare2, rizin, retdec | rizin and Cutter in winget; no radare2 or retdec | radare2 6.2.0-1 and rizin 0.8.2-2 packaged; no retdec | unverified |

## Unity-bundled monodis

On Windows the editor's `MonoBleedingEdge/bin/monodis` is a macOS Mach-O binary, not a Windows
program. Running it directly, or as `mono.exe monodis`, fails with
`File does not contain a valid CIL image`. `lib/mono/4.5/ikdasm.exe` under the bundled `mono.exe`
works, but `dotnet il dasm` covers the same need. Where the macOS and Linux editors keep monodis
was not checked.

## Traps

1. **Tools directory not on PATH.** On Linux, `ilspycmd` and `dotnet-il` fail with
   `command not found` right after install. The installer says the tools directory is not on
   `PATH`. Platform: Linux.

   ```bash
   export PATH="$PATH:$HOME/.dotnet/tools"
   ```

2. **Runtime roll-forward.** `dotnet-il dasm` and `dotnet-ildasm` failed with
   `Framework: 'Microsoft.NETCore.App', version '9.0.0' (x64) not found`, because the host had
   .NET 8 and 10 only and global tools do not roll forward across majors. Platform: Linux.

   ```bash
   export DOTNET_ROLL_FORWARD=Major
   ```

3. **Java too old for Ghidra.** The Arch package depends on `java-environment>=21` and the host
   had OpenJDK 17.0.20.1. Install a newer JDK before installing Ghidra. Platform: Linux.
4. **dumpbin is not on PATH.** It runs by full path from a plain shell with no vcvars. Four
   copies existed on the Windows host, so the script's vswhere pattern picks among them.
   Platform: Windows.
5. **dotnet-il takes slash options.** It is Microsoft ildasm 9.0.5, so `--help` is rejected with
   `INVALID COMMAND LINE OPTION` and options go before the assembly path.
6. **PowerShell and non-executables.** `& "path\to\extensionless-file" args | Select-Object` throws
   `Cannot run a document in the middle of a pipeline` when the target is not a Windows
   executable. Platform: Windows.
