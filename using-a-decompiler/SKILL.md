---
name: using-a-decompiler
description: "Use when the only way to answer a question about code is to read a compiled artifact: a .NET assembly, a native executable or shared library, a Unity player, or an editor or engine binary. Load BEFORE running ilspycmd, ildasm, monodis, Ghidra, objdump, dumpbin, or Cpp2IL, even for a one-line listing, and before answering a question that would require one of them. Triggers: no source for a dependency that crashes or misbehaves, a vendor claim to confirm, an interoperability question about a format or protocol, a question about what an installed program actually does, a request to peek inside a third-party or commercial binary, a Unity Mono or IL2CPP build to inspect, an obfuscated or stripped binary, or an agent about to guess what a binary does from its name."
---

# Using a Decompiler

A decompiler reads what a compiled artifact does when no source is in hand. The first step is
deciding whether that reading is yours to do; the second is picking the tool the artifact calls
for and running it narrowly.

## First: do you need to decompile at all?

Source beats decompiled output every time. Before any tool, check in this order:

1. The owner's own repository: other branches, tags, and the build's CI artifacts.
2. A source-linked or symbol-bearing package: NuGet with SourceLink, a `.snupkg`, a `.pdb` or
   DWARF beside the binary.
3. A public repository for the library: the vendor's GitHub, a mirror, the distro's source package.
4. UnityEngine or UnityEditor managed code: Unity's published C# reference source
   (UnityCsReference on GitHub) at the tag matching the editor version. Say the reason in one
   sentence when you point there: the managed source is public under a reference-only license
   that permits reading it to understand your own project. Native engine code is not there; it
   shows as an `extern`.
5. .NET runtime and base library code: source.dot.net.
6. Unity's Mono runtime: Unity's public mono fork on GitHub.

Then the runtime-versus-static test. "What does this code do" and "what shipped in this build"
are static questions: decompile. "Which input hits which branch", "what is null at the crash",
"why does this differ in play mode" are runtime questions: their home is `using-a-debugger`
(break, inspect, log), even when the user says "decompile". The owner's own source in hand plus a
runtime question means no decompiler at all.

## Three tiers

| Tier | Artifact | What the agent does |
| --- | --- | --- |
| 1 | The owner's own build: a dll they shipped, their Mono or IL2CPP player, their native library, any build whose source they wrote, even with the tag or the pdb lost | Proceed. No permission, no justification, no legal note, and no sentence explaining why it is allowed: go straight to the command. |
| 2 | Third-party code the owner legitimately possesses: an installed vendor client, a dependency with no source, an installer, a file format their tool must read, Unity's native player or editor binaries | Write the justification below, ask one confirmation question, proceed on a yes. |
| 3 | Defeating a protection mechanism (anti-cheat, license checks, DRM, tamper checks), lifting a competitor's proprietary algorithm, a leaked or pirated build, anything the owner does not legitimately possess | Decline once, plainly. See "Not an enforcer". |

Tier 2 justification, four lines, written before the first command. Read the directory listing
first so `Target` names the actual file (`AcmeSync.Client.dll`, not "the AcmeSync assembly"),
and name that same file in the command you propose:

```text
Target:      <file and version, e.g. AcmeSync.Client.dll 4.2.1>
Possession:  <how the owner has it, e.g. installed from the vendor installer on 2026-09-30>
Purpose:     <the one question, e.g. find what is null in FolderWatcher.OnRenamed to report the crash precisely>
Boundaries:  <no redistribution; output stays in scratch; nothing committed; stop when the question is answered>
```

Then exactly one question: "Proceed with this?" If the EULA carries a no-reverse-engineering
clause, say so in one sentence, two at most, as information for the owner's decision ("the EULA
forbids reverse engineering except where law permits; error correction and interoperability are
the carve-outs"); the legal detail stays in `references/when-to-decompile.md`, never in the reply,
and never as a refusal or a lecture. **The agent never starts a Tier 2 decompile on its own
initiative**: the owner's yes is the trigger, every time.

Tier 1 is not Tier 2 in disguise. A lost git tag, a reimaged CI machine, or a missing pdb does
not change whose code it is.

## Not an enforcer

At Tier 3, decline the decompile-and-patch step in one or two sentences, offer a permitted path
(the vendor's allow-list or support channel, a mode the protection permits, the other tool's
compatibility guidance), and carry on helping with everything else. No lecture, no speculation
about consequences, no reporting, logging, flagging, or filing of the request anywhere, and none
of that said aloud either: the decline itself never mentions reporting or logging. One decline is
the whole response to that request; the conversation continues.

## Output handling

Tier 2 output lives in scratch (the session scratchpad or a gitignored `workspace/`), never in
the repository, never pasted wholesale into an issue, a PR, a memory note, or a message to the
vendor. Cite by symbol and offset: the type, the method, the field, the condition. Quote the
minimum, a few lines at most, and say why the quote is minimal. A write-up names
`FolderWatcher.OnRenamed` and the unassigned field; it does not carry the method body. Such a
write-up, cited by symbol and condition, is not decompiled output and may be committed; the
decompiled output itself stays in scratch. Tier 1 output may be kept, but a whole-project
decompile of the owner's own dll is still scratch; the source is the record.

## Pick the tool by artifact

| Artifact | First tool | Second opinion | Quick look |
| --- | --- | --- | --- |
| .NET assembly (`.dll`, `.exe`; ReadyToRun included) | `ilspycmd` | `dotnet il dasm` for one method's IL | `ilspycmd -l c X.dll` |
| Native PE or ELF (`.dll`, `.so`, `.exe`; Native AOT) | Ghidra headless through `scripts/ghidra-decompile.py` | Ghidra GUI on one function | `llvm-objdump -p`, `dumpbin /EXPORTS`, `objdump -d --disassemble=NAME`, `gdb -batch` |
| Unity Mono player | `ilspycmd` on `*_Data/Managed/Assembly-CSharp.dll` | `dotnet il dasm` | `ilspycmd -l c` |
| Unity IL2CPP player | Cpp2IL on `GameAssembly.dll` plus `<Name>_Data/il2cpp_data/Metadata/global-metadata.dat`: `dummydll` stubs for signatures, the `isil` dump for addresses; then Ghidra on `GameAssembly.dll` filtered by `FUN_<address prefix>` | Il2CppDumper (its Ghidra script applies names; unverified) | `ilspycmd -t Type` on the recovered stubs (signatures only) |
| Unity Editor or Engine | UnityCsReference at the matching tag | `ilspycmd` on the managed dll, to confirm the binary matches | Ghidra on `UnityPlayer.dll` or the editor binary, Tier 2 |

ReadyToRun keeps the IL and metadata, so ilspycmd decompiles it normally; only Native AOT strips
the IL and needs a native decompiler. IL2CPP stubs from Cpp2IL carry signatures with empty
bodies: the shape of `Combat.ApplyDamage`, never its logic. The logic is in Ghidra's output for
`GameAssembly.dll`, where every function is `FUN_<address>`: nothing in Cpp2IL's output carries
names into Ghidra, so read the method's address range off the jump targets in its `isil` dump
and filter Ghidra on that prefix. Il2CppDumper's script can apply names (unverified). See
`references/unity.md`.

## Say what you will run, not what you have not seen

Describe the command and what it can show; never narrate output before the tool has produced
it. A crash log with method names but no offsets locates a method, not a line; a listing shows
which files exist, not what is inside them. Facts about the binary come from the run.

## Narrow first

- ilspycmd: `-l c` to list types, then `-t Namespace.Type` or
  `-m "M:Namespace.Type.Method(System.String)"`. `-p -o DIR` (the whole project) is the form for
  when the question needs a grep across the assembly; say that is what it is for, rather than
  only avoiding it. `-il` dumps everything and ignores `-t` and `-m`.
- Ghidra: import once into a scratch project (`--project-dir` outside the repository; the import
  pulls system libraries in), keep the project, and re-run scripts with `-process` (the wrapper
  does this when the project already exists). `--filter NAME` exports only matching functions.
  Ghidra ships no export-all script; this skill's `scripts/ghidra_scripts/DecompileAllToFile.java`
  is the postScript that writes every function's C to one file.
- Native quick look: one function with `objdump --disassemble=NAME`,
  `llvm-objdump --disassemble-symbols=NAME`, or `gdb -batch -ex "disassemble NAME"` before any
  whole-binary `dumpbin /DISASM` dump.
- Unity: one type out of `<Name>_Data/Managed/Assembly-CSharp.dll`. Read the player folder (or
  its listing file) and write the real folder name in the command; a `<Name>_Data` placeholder
  or a "probably" in the answer is a guess, not a path. Say why no `-r` is needed: the UnityEngine reference
  assemblies sit in that same `Managed` folder, so resolution works from there (add
  `-r <Managed dir>` only if references come back unresolved).

## Symbols decide readability

- A pdb beside the dll, or DWARF in the ELF, is the difference between source names and invented
  ones. Say which case you are in before quoting output.
- ilspycmd reads the pdb only with `-usepdb` (long form `--use-varnames-from-pdb`), and only when
  the pdb sits next to the dll. A dll copied alone makes `-usepdb` a silent no-op: locals come
  back as `num`, `list`, `safeFileHandle`. Local names live only in the pdb, not in assembly
  metadata, so this is expected, not a bug: copy the pdb next to the dll and rerun.
- Ghidra applies a pdb automatically: function names and types are real, parameters stay
  `param_N` and locals `local_NN` (measured on a Windows Debug DLL). DWARF on ELF was not
  measured; Ghidra has a DWARF analyzer, but whether parameter and local names come through was
  not checked, so say that rather than predicting the names.
- Stripped means `FUN_<address>` names and guessed types. Orient by strings and their
  cross-references (an `=` literal, an error message), by imports (`strchr`, `strlen`), and by the
  export table. A by-symbol filter such as `objdump --disassemble=NAME` prints nothing on a
  stripped binary and exits 0; that is "no symbol", not "empty function".

## Platform note

Windows and Linux were verified separately on 2026-10-06; macOS is unverified. ilspycmd,
`dotnet il dasm`, and llvm-objdump ran on both; ilspycmd is the primary tool:
`dotnet tool install --global ilspycmd`, then on Linux
`export PATH="$PATH:$HOME/.dotnet/tools"` before the command resolves. `dumpbin` is Windows-only
(located through `vswhere`); `gdb -batch` and GNU `objdump` are the Linux quick look; `monodis`
in the Windows Unity editor tree is a macOS Mach-O binary and does not run there; Ghidra 11.4+
needs Java 21 or newer everywhere, and on Windows the wrapper runs `analyzeHeadless.bat` through a
generated `.bat` because a quoted `cmd /c` string breaks on the redirect.
`scripts/setup-decompilers.py` detects every tool and installs the two .NET tools unattended.

## Rationalizations the baseline produced

| Excuse | Reality |
| --- | --- |
| "What's the full path to the dll?" (stalling on the owner's own build) | Tier 1 proceeds: name the `ilspycmd -t` command and the one type, and ask for the path in the same breath. |
| "ILSpy would show it in minutes, but it's your decision" (then no justification) | The four-line justification and the one question are the decision aid. Write them. |
| "Want me to decompile UnityEngine.CoreModule.dll anyway?" | UnityCsReference at the matching tag first; the dll only to confirm the binary matches. |
| "`-u` takes variable names from the pdb" | The flag is `-usepdb`. Real flags only: `-l`, `-t`, `-m`, `-p`, `-o`, `-il`, `-usepdb`, `-r`. |
| "I can keep the decompiled detail as a repo-only note" | Third-party decompiled output never enters the repository. Scratch, cited by symbol. |
| "Both GUI tools open Assembly-CSharp.dll as-is" | The command-line path is `ilspycmd -t Type Assembly-CSharp.dll`; a GUI is not an answer an agent can run. |

## References

- `references/when-to-decompile.md`: the tiers with worked examples, the justification filled in,
  output handling, the legal background.
- `references/ilspycmd-dotnet.md`: ilspycmd, `dotnet il dasm`, pdb handling, ReadyToRun versus
  Native AOT, ikdasm and monodis.
- `references/quick-disassembly.md`: llvm-objdump, dumpbin, GNU objdump, gdb batch.
- `references/ghidra-headless.md`: the wrapper, the raw analyzeHeadless forms, the postScript,
  symbols, knobs, traps.
- `references/tooling-setup.md`: what installs unattended, what is manual, the per-platform table.
- `references/unity.md`: Mono and IL2CPP players, Burst, Editor and Engine, monodis per platform.
- `scripts/setup-decompilers.py`: detect-then-install (`--dry-run`, `--only KIND,KIND`).
- `scripts/ghidra-decompile.py`: `BIN --output out.c [--filter NAME] [--timeout 60] [--project-dir DIR]`.
