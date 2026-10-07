# ilspycmd and IL disassembly (.NET managed)

Covers ilspycmd, `dotnet il dasm`, `dotnet-ildasm` and ikdasm for managed assemblies.
Verified on Windows (11, ilspycmd 11.1.0.9782, net10.0 target) and Linux (Arch, same ilspycmd,
net10.0 target). macOS is unverified. Each command is labelled `Windows`, `Linux` or `both`.
Replace `PATH/TO/X.dll` with the assembly under study.

## Install

```bash
dotnet tool install --global ilspycmd
```

Platform: both. Prints `Tool 'ilspycmd' (version '11.1.0.9782') was successfully installed.`

On Linux the tools directory is not on PATH after install (the installer says so). Platform: Linux.

```bash
export PATH="$PATH:$HOME/.dotnet/tools"
```

Check the install. Platform: Windows.

```powershell
ilspycmd --version
```

It prints `ilspycmd: 11.1.0.9782` and `ICSharpCode.Decompiler: 11.1.0.9782`.

## Narrow-first command ladder

Go from the smallest output to the largest. Do not start with a whole-assembly dump.

1. List entities. Letters are `c` (classes), `i` (interfaces), `s` (structs), `d` (delegates),
   `e` (enums). Platform: both.

   ```bash
   ilspycmd -l c PATH/TO/X.dll
   ```

2. One type to stdout. Platform: both.

   ```bash
   ilspycmd -t Namespace.TypeName PATH/TO/X.dll
   ```

3. One member to stdout, with a using header. Platform: Windows.

   ```powershell
   ilspycmd -m "M:MFTLib.FileUtilities.NativeGetVolumeHandle(System.String)" PATH/TO/X.dll
   ```

4. Whole assembly as a project directory. It prints nothing to stdout and finished in about 1.5 s
   on both machines. Platform: both.

   ```bash
   ilspycmd -p -o OUT_DIR PATH/TO/X.dll
   ```

Other flags the Windows report lists as useful. They were not run individually.

| Flag | Meaning |
| --- | --- |
| `-r REFDIR` | reference directory for resolving dependencies |
| `--list-resources` | list embedded resources |
| `--dump-table NAME` | dump a metadata table |
| `-genpdb` | generate a pdb |
| `-lv` | listed in the report without a description |

## Local variable names and the pdb

Local names come only from the pdb, and ilspycmd does not read it by default. The long form of
`-usepdb` is `--use-varnames-from-pdb`. Platform: both. The table was measured on
`MFTLib.FileUtilities` (Windows). Linux reproduced rows 1 and 3 on a small test assembly, where
generic `num` and `i` became the real source names with the pdb and the flag.

| Invocation | Local name for the CreateFile result |
| --- | --- |
| `ilspycmd -t T PATH/TO/X.dll` (pdb present, default) | `safeFileHandle` (pdb ignored) |
| `ilspycmd -t T -usepdb PATH/TO/X.dll` (pdb present) | `volumeHandle` (real source name) |
| `ilspycmd -t T NOPDB/X.dll` (dll copied alone) | `safeFileHandle`, same as default |
| `ilspycmd -t T -usepdb NOPDB/X.dll` | `safeFileHandle`, no error, exit 0 |

The pdb is found next to the dll. With no pdb, `-usepdb` is silently a no-op.

## IL output

`ilspycmd -il` dumps the whole assembly. It ignores `-t` and `-m` (the Windows run passed `-t` and
still got 55,662 lines for the test assembly), so do not try to narrow it. Redirect to a file and
slice. Platform: Windows (Linux ran the same form; the head of its output was inconclusive).

```bash
ilspycmd -il PATH/TO/X.dll > OUT_DIR/X.il
```

For one method, use `dotnet il dasm`. It wraps Microsoft ildasm 9.0.5 and takes slash options.

```powershell
dotnet tool install --global dotnet-il
```

Platform: both. Install prints `Tool 'dotnet-il' (version '1.0.0') was successfully installed.`

One method, Windows (slash options may follow the file name):

```powershell
dotnet il dasm PATH/TO/X.dll /ITEM="MFTLib.FileUtilities::NativeGetVolumeHandle"
```

Whole assembly to a file, Windows (0.24 s, 47,947 lines for MFTLib):

```powershell
dotnet il dasm PATH/TO/X.dll /OUT="OUT_DIR/dasm-out.il" /UTF8
```

One method, Linux. Options go before the file name. The tool targets .NET 9 and only .NET 8 and 10
are installed, so it needs `DOTNET_ROLL_FORWARD=Major`:

```bash
DOTNET_ROLL_FORWARD=Major dotnet il dasm -item=HelloDecompiler.DistinctCalculator::ComputeSumWithLoop PATH/TO/X.dll
```

The output is Debug-build IL: `nop`, `V_n` locals, no source names.

Other ildasm options seen in the usage text: `/NOIL`, `/BYTES`, `/TOKENS`, `/SOURCE`, `/LINENUM`,
`/VISIBILITY=PUB`, `/PUBONLY`, `/NOCA`. On Windows, `/VISIBILITY=PUB /NOCA` to stdout also worked.

Linux also had a `dotnet-ildasm` tool already installed (0.12.2). Its help works with the roll-forward
variable. Its options are `-o` (output file), `-i MyClass::Method` (one item), `-f` (overwrite).
Platform: Linux.

```bash
DOTNET_ROLL_FORWARD=Major dotnet-ildasm --help
```

## monodis and ikdasm

- monodis in the Windows Unity 2022.3 editor tree is a macOS Mach-O file. It does not run, directly
  or under `mono.exe`. Platform: Windows.
- Mono is not installed on the Linux machine, so monodis was not tried there. macOS is unverified.
- Unity editors on macOS and Linux ship monodis as a native binary under `MonoBleedingEdge/bin`,
  which would make it the no-install IL path there. Neither discovery run exercised it; treat it
  as unverified until one does.
- ikdasm (IKVM.Reflection ildasm) works on Windows through the editor's bundled `mono.exe`. It emitted
  valid ildasm-style output on a net10.0 assembly; only the first lines were inspected. It is
  redundant next to `dotnet il dasm`. Options: `-out=<file>`, `-assembly`, `-assemblyref`,
  `-moduleref`, `-exported`, `-customattr`. Platform: Windows.

```powershell
mono.exe PATH/TO/MonoBleedingEdge/lib/mono/4.5/ikdasm.exe PATH/TO/X.dll
```

## ReadyToRun versus Native AOT

Background, not measured by the discovery runs. A `PublishReadyToRun=true` image keeps the IL and
metadata and adds precompiled native code beside them, so ilspycmd decompiles it exactly like a
plain assembly. A Native AOT publish (`PublishAot=true`) strips the IL and ships a native
executable; there is nothing for ilspycmd to read, and it is a Ghidra target under
`references/ghidra-headless.md`. "It is native now" is only true for AOT.

## Traps

1. Windows: `ilspycmd -t T -il` ignores `-t` and `-m` and dumps the whole assembly. The first 20
   lines of the Linux `-il -t` run did not show whether `-t` was honored there, so assume the same.
2. Both: local names stay generic until `-usepdb` is passed, and the pdb must sit next to the dll.
   Without it, `-usepdb` does nothing and reports no error.
3. Both: `dotnet il dasm --help` is rejected with `INVALID COMMAND LINE OPTION: --help`, yet it prints
   the real usage. `-o file` also fails. Use the slash options.
4. Linux: `dotnet il dasm` with the file name first and `-item=` after it fails with
   `MULTIPLE INPUT FILES SPECIFIED`. Put options before the file name.
5. Linux: `dotnet il dasm` and `dotnet-ildasm` fail with a missing .NET 9 (or 3.0) framework message
   until `DOTNET_ROLL_FORWARD=Major` is set.
6. Linux: `ilspycmd` is `command not found` right after install until `$HOME/.dotnet/tools` is on PATH.
7. Windows: monodis and `bin/ikdasm` in the Unity editor tree are macOS files (the ikdasm script has a
   hard-coded `/Users/bokken` path). Run `lib/mono/4.5/ikdasm.exe` under `mono.exe` instead.
8. Windows PowerShell: `& "path/to/extensionless-file" args | Select-Object` throws
   `Cannot run a document in the middle of a pipeline` when the target is not an executable.
9. Decompiled locals (`num`, `i`, `safeFileHandle`) are decompiler inventions unless the pdb was used.
