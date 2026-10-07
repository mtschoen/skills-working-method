# using-a-decompiler

A skill that teaches agents to read a compiled artifact when no source is in hand: a .NET
assembly, a native executable or shared library, a Unity player, or an editor or engine binary.
It first decides whether decompiling is appropriate, then picks the tool the artifact calls for
(ilspycmd, Ghidra headless, the quick disassemblers, the Unity toolchain) and runs it narrowly.

See `SKILL.md` for the decision logic and `references/` for per-tool detail.

## The gate

Source comes first: the owner's repository, source-linked packages, a public repository, Unity's
published C# reference source, and source.dot.net are all checked before any tool runs. The skill
also separates static questions (what does this code do) from runtime questions (which input hits
which branch), which belong to `using-a-debugger`.

Three tiers decide what happens next. Tier 1 is the owner's own build and proceeds with no
justification. Tier 2 is third-party code the owner legitimately possesses: the agent writes a
four-line justification (target, possession, purpose, boundaries), asks one confirmation question,
and proceeds only on a yes. Tier 3 is defeating a protection mechanism or anything the owner does
not legitimately possess: the agent declines once, plainly, offers a permitted path, and keeps
helping with everything else. It is not an enforcer, so it never reports, logs, or flags the
request.

Tier 2 output stays in scratch, is cited by symbol and condition, and is never committed or pasted
wholesale into an issue, a PR, a note, or a message to the vendor.

## Prerequisites (external tools the installer does NOT install)

The skill installer ships only this skill's files (`SKILL.md`, `scripts/`, `references/`). The
decompilers are runtime prerequisites you install separately.
`scripts/setup-decompilers.py` installs what it can (the two .NET tools) and reports the rest as
manual steps; `references/tooling-setup.md` is the authoritative guide.

| Tool | Install | Notes |
|---|---|---|
| ilspycmd | `dotnet tool install --global ilspycmd` (done by the setup script) | .NET assemblies and Unity Mono players. Needs the .NET SDK. |
| dotnet-il | `dotnet tool install --global dotnet-il` (done by the setup script) | One method's IL. On Linux it needs `DOTNET_ROLL_FORWARD=Major` when the host lacks .NET 9. |
| Ghidra plus Java 21+ | Release zip from the NationalSecurityAgency/ghidra releases page; set `GHIDRA_INSTALL_DIR`; install a JDK 21 or newer | Native PE and ELF, and IL2CPP `GameAssembly`. Manual. |
| dumpbin or objdump | dumpbin: Visual Studio "Desktop development with C++" workload (Windows). objdump: binutils from the distro (Linux) | Quick native look. The script finds dumpbin through vswhere. |
| Cpp2IL | Single-file release downloaded onto `PATH` | Unity IL2CPP stubs and addresses. Manual; not exercised by the discovery runs. |

The scripts also need **Python 3** on PATH.

```bash
python scripts/setup-decompilers.py            # detect, then install what it can
python scripts/setup-decompilers.py --dry-run
python scripts/setup-decompilers.py --only ilspycmd,analyzeHeadless
```

On Linux, add the .NET tools directory to `PATH` after installing:
`export PATH="$PATH:$HOME/.dotnet/tools"`.

## Platform matrix

| Platform | Status |
|---|---|
| Windows | Verified 2026-10-06 |
| Linux (Arch) | Verified 2026-10-06 |
| macOS | Unverified |

ilspycmd is the one tool verified on both. The Ghidra headless wrapper was run on Windows only; the Linux host had no Ghidra and Java 17. See `references/tooling-setup.md` for
the per-tool table.

## Relation to using-a-debugger

`using-a-debugger` owns runtime questions: break, inspect, log. This skill owns static reading of
compiled artifacts. Each points at the other: a "decompile" request that is really a runtime
question goes to the debugger, and a debugging session that needs to know what a closed-source
dependency does reads it here first.
