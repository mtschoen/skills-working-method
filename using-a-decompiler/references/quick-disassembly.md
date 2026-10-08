# Quick disassembly (native binaries)

Covers one-shot export listing and disassembly with llvm-objdump, dumpbin, GNU objdump and gdb.
Verified on Windows (PE, a first-party C++ DLL with its pdb) and Linux (Arch, ELF, a small C program
built with and without symbols). macOS is unverified. Each command is labelled `Windows`, `Linux`
or `both`. Replace `PATH/TO/BIN` with the binary under study.

## Exports and imports

Exports appear under `Export Table:` (26 names with ordinals and RVAs on the Windows DLL).
Platform: Windows.

```bash
llvm-objdump -p PATH/TO/BIN
```

```powershell
dumpbin /EXPORTS PATH/TO/BIN
```

See "Finding dumpbin" below. The dumpbin output starts with `26 number of functions` and a table of
ordinal, hint, RVA and name. No imports command was run on either platform.

## One function

llvm-objdump, Windows (PE). It knows only the export table, not the pdb, so it works for exported
names only. Internal calls print as `<ExportName+0xNNNN>` offsets from the nearest export.

```bash
llvm-objdump -d --no-show-raw-insn --disassemble-symbols=NAME PATH/TO/BIN
```

llvm-objdump, Linux (ELF). Same command, run only on a stripped binary, where it prints
`failed to disassemble missing symbol NAME` as a warning. Platform: Linux.

GNU objdump on an unstripped ELF, with `.symtab` or debug info. Platform: Linux.

```bash
objdump -d --no-show-raw-insn --disassemble=NAME PATH/TO/BIN
```

On a stripped ELF the same command prints empty section headers and exits 0. Use address bounds
instead, found from the entry point or from call targets in another function. The report names
these two flags as the fix but did not run them. Platform: Linux.

```bash
objdump -d --no-show-raw-insn --start-address=0xSTART --stop-address=0xSTOP PATH/TO/BIN
```

gdb one-shot. Platform: Linux. It needs symbols. On a stripped binary it prints
`No symbol table is loaded.  Use the "file" command.`

```bash
gdb -batch -ex "set debuginfod enabled off" -ex "disassemble NAME" PATH/TO/BIN
```

## Whole-binary dumps

dumpbin uses the adjacent pdb and labels every function and call target (mangled C++ names).
It has no per-symbol switch, so dump everything and slice with sed or grep. Platform: Windows.
The dump for the test DLL was 44,101 lines.

```powershell
dumpbin /DISASM PATH/TO/BIN > dumpbin-disasm.txt
```

`/DISASM /RANGE:0xba00,0xba30` printed only the header and summary, no instructions.

## Finding dumpbin

dumpbin is not on PATH. Locate it with vswhere. Platform: Windows.

```powershell
& "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe" -all -products '*' -find 'VC/Tools/MSVC/*/bin/Hostx64/x64/dumpbin.exe'
```

Four copies were found on the test machine (several Visual Studio editions and MSVC versions). One was
used by full path. It ran from a plain shell with no vcvars environment.

## Which tool when

| Need | Windows (PE) | Linux (ELF) |
| --- | --- | --- |
| Exports | `llvm-objdump -p`, `dumpbin /EXPORTS` | not run |
| Real internal names | dumpbin dump, then slice | `objdump --disassemble=NAME` or `gdb`, unstripped only |
| One exported function | `llvm-objdump --disassemble-symbols` | `llvm-objdump --disassemble-symbols` (only the missing-symbol warning was seen) |
| Stripped binary | not run | address bounds on `objdump` (not run) |

## Traps

1. Windows: llvm-objdump `--disassemble-symbols` sees only export names (no pdb), and labels internal
   call targets as `<ExportName+0xNNNN>`. One such call was really `__CheckForDebuggerJustMyCode`.
   Use dumpbin or Ghidra when internal names matter.
2. Windows: dumpbin `/DISASM /RANGE:` prints no disassembly. Dump to a file and slice.
3. Windows: dumpbin is absent from PATH. Use vswhere, then call it by full path.
4. Windows: a Debug build adds `0xCC` stack-fill loops and `__CheckForDebuggerJustMyCode` calls.
   Expect that noise in the output.
5. Linux: GNU objdump `--disassemble=NAME` on a stripped binary prints only empty section headers and
   exits 0. Empty output means the symbol is not in the table, not that the function is empty.
6. Linux: llvm-objdump names the flag `--disassemble-symbols=`, GNU objdump names it
   `--disassemble=`. Do not mix them.
7. Linux: gdb batch mode asks `Enable debuginfod for this session? (y or [n])` unless
   `-ex "set debuginfod enabled off"` comes first.
8. Linux: gdb `disassemble NAME` needs a symbol table. It prints
   `No symbol table is loaded.  Use the "file" command.` on a stripped binary.
