# Ghidra headless decompile

Covers exporting every function of a native binary as decompiled C through Ghidra headless.
Verified on Windows only (Ghidra 11.4.2, a first-party C++ DLL with its pdb). Linux was not run:
the Linux host had no Ghidra and Java 17. macOS is unverified. Replace `PATH/TO/BIN` with the
binary under study and `GHIDRA_INSTALL_DIR` with the unpacked Ghidra release.

## The wrapper

Platform: both (the command construction is shared; only Windows was run).

```bash
python scripts/ghidra-decompile.py PATH/TO/BIN --output out.c
python scripts/ghidra-decompile.py PATH/TO/BIN --output out.c --filter ParseMFT
python scripts/ghidra-decompile.py PATH/TO/BIN --output out.c --timeout 60
```

- `--filter NAME` keeps only functions whose name contains `NAME`.
- `--timeout N` is the per-function decompile timeout in seconds (default 60).
- `--ghidra PATH` points at `analyzeHeadless` (or `analyzeHeadless.bat`) when
  `GHIDRA_INSTALL_DIR` is not set. `--project-dir` and `--project-name` move the project.
- The project defaults to a `ghidra-projects` folder under the system temp directory and is named
  after the binary. A second run of the same binary reuses it and skips analysis.

The script prints the Ghidra command it ran, then one summary line:

```text
exit=0 seconds=45.0 functions=1259 named=1259 unnamed=0
```

`unnamed` counts functions named `FUN_...` and `named` is the rest. The line ends with
`(no functions matched)` when nothing came out, or `(no symbols: every function is FUN_)` when
every function is unnamed; a mixed result carries no verdict, because a stripped binary can
still have named exports and import thunks.

## The command it generates

First run of a binary, platform Windows (the smoke run):

```text
GHIDRA_INSTALL_DIR/support/analyzeHeadless.bat PROJECT_DIR NAME -import PATH/TO/BIN -overwrite -scriptPath scripts/ghidra_scripts -postScript DecompileAllToFile.java out.c - 60
```

Rerun of a binary that already has a project, platform Windows (the smoke run, with a filter):

```text
GHIDRA_INSTALL_DIR/support/analyzeHeadless.bat PROJECT_DIR NAME -process BIN.dll -noanalysis -scriptPath scripts/ghidra_scripts -postScript DecompileAllToFile.java out.c ParseMFT 60
```

The three postScript arguments are the output file, the name filter, and the per-function
timeout. `-` in the filter slot means no filter. An empty argument would vanish in the Windows
`.bat` launcher and shift the timeout into the filter slot.

No `-processor` is passed. On the Windows DLL Ghidra auto-detected `Portable Executable (PE)` and
`x86:LE:64:default:windows`.

## What the postScript does

`scripts/ghidra_scripts/DecompileAllToFile.java` walks every function in the program, calls the
decompiler with the per-function timeout, and writes one block per function to the output file.
A function that fails gets a `// decompile failed: MESSAGE` line instead of code.

## Symbols

- A pdb beside the dll is picked up by the PDB analyzer with no flag. On the Windows DLL, 0 of
  1,259 functions were named `FUN_...`, and types such as the return type `MftParseResult *` came
  from the pdb as well.
- Parameters stay `param_N` and locals stay `local_NN` even with a pdb.
- With no symbols the functions are named `FUN_` plus the address. The wrapper reports this.
- DWARF on ELF was not exercised. Ghidra has a DWARF analyzer; whether parameter and local
  names come through it was not checked here.

## Reading the output

Every function starts with a header line, `// ==== NAME @ ADDRESS`:

```text
// ==== ParseMFTImpl @ 18000d0a0
```

```bash
grep -c "^// ==== " out.c
grep -n "^// ==== ParseMFT" out.c
grep -n "decompile failed" out.c
```

## Measured timings

Both numbers are Debug-build measurements on one Windows machine, not benchmarks.

| Run | Wall time | Functions |
| --- | --- | --- |
| Import and analysis, wrapper run (smoke) | 45.0 s | 1,259 |
| Import and analysis, first discovery run | about 23 s | 1,259 |
| `-process -noanalysis` with `--filter ParseMFT` | 8.6 s | 5 |

The full output for the 1,259 functions was 29,405 lines in the discovery run.

## Knobs

The wrapper exposes only the per-function timeout. The Windows report did not evidence `-max-cpu`,
the Java heap setting in `support/analyzeHeadless`, or `launch.properties`, so they are not
documented here.

## Traps

1. **Windows launcher.** Running `analyzeHeadless.bat` through `cmd /c "<long quoted string with
   redirects>"` from PowerShell failed with `> was unexpected at this time.` (exit 255, nothing
   ran). The wrapper writes a small `.bat` that `call`s the launcher and does the redirect inside
   it, then runs that. Platform: Windows.
2. **System libraries enter the project.** The import also loaded the System32 dependency dlls
   (kernel32, msvcp140d, ucrtbased, vcruntime140d) into the project as libraries. Keep the
   project in a scratch directory, never inside a repository.
3. **Java 21 or newer.** The setup script treats anything older as missing. The Linux host had
   Java 17, and its Arch `ghidra` package depends on `java-environment>=21`. The Windows smoke
   run used Java major 26.
4. **Debug builds are noisy.** Expect `__CheckForDebuggerJustMyCode` calls and stack-fill loops
   (a `for` loop writing `-0x33333334`) in the output.
5. **Harmless pdb warnings.** A few `PDB STRUCTURE reconstruction failed to align` warnings
   appeared in the log while the names still applied.
6. **Run it in the background.** Large binaries take longer than the 45 s measured here. Tee the
   output to a file and read it when the run ends.
7. **Bundled scripts do not do this.** None of the stock Ghidra export scripts writes every
   function's decompiled C to a file, which is why the postScript exists.
