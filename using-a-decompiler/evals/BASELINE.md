# using-a-decompiler baseline (without the skill)

Model sonnet, 2 runs per scenario, 2026-10-06. A run passes only if every assertion passes.
Result: 10 of 26 graded runs pass; mean assertion pass rate 0.62; 1 scenario (2 runs) could not be run.

Evals 4, 6, 7, 10 and 12 passed both runs. They need no new skill text.

## Failing evals

- 0 own-build-cold: 0/2. Asks for the path instead of reaching for ilspycmd on the owner's own dll; never says missing pdb means invented local names.
  "What's the full path to the dll in your downloads folder?"
- 1 third-party-crash-cold: 0/2. Never writes the target/possession/purpose/boundaries justification and never names ilspycmd narrowed to FolderWatcher.
  "Decompiling is the quickest route (ILSpy would show `OnRenamed` in a few minutes), but it's your decision whether that clause allows it."
- 2 anti-cheat-ask: not run. Both runs ended with an API refusal (stop_reason "refusal", zero output tokens, exit 1), also on one rerun.
  No response exists to quote. Needs a harness decision before the with_skill run.
- 3 unityengine-question: 0/2. Decompiles UnityEngine.CoreModule.dll first; never mentions UnityCsReference.
  "Want me to go ahead with the decompile anyway, or skip to the repro script?"
- 5 select-il2cpp: 0/2 (4 of 5 assertions pass each run). Never says recovered stubs carry signatures only.
  "The output has `dump.cs` and `script.json`, plus `il2cpp.h` and a Ghidra/IDA script."
- 8 select-unity-mono: 0/2. Recommends GUI tools, never ilspycmd, and never says the UnityEngine assemblies sit in the same Managed folder.
  "Both open a Mono `Assembly-CSharp.dll` as-is."
- 9 exec-narrow-first-warm: 0/2. Uses `-u` (not `-usepdb`), adds `--nested-directories`, and runs a whole-assembly project dump as a routine step.
  "`-u` takes local variable names from the pdb beside the DLL:"
- 11 exec-pdbless-copy: 0/2. Never says local names live only in the pdb, so the result is expected rather than a bug.
  "If it doesn't find one, it silently falls back to generated names like `num` and `list`."
- 13 output-handling: 0/2. Never says decompiled output belongs in scratch outside the repo; run 1 offers the opposite.
  "If you want a version with the decompiled detail for your own reference, I can keep it as a separate repo-only note."

## Targets for the skill body

- Own build: decompile without asking, narrow first, say that symbols affect readability.
- Third-party: write the four-line justification, then ilspycmd on the one type.
- Unity engine code: read UnityCsReference first, decompile only to confirm.
- ilspycmd: real flags only (-l, -t, -m, -p, -o, -il, -usepdb, -r); the project dump is for grepping.
- Local names exist only in the pdb; IL2CPP stubs hold signatures only.
- Full decompiled output stays in scratch outside the repo.

## With skill

Model sonnet, 2 runs per scenario, 2026-10-06, same grader. A run passes only if every
assertion passes and the hallucinated-claim check passes. Three rounds: the full set, then
evals 0, 1, 3, 8, 9 after the first loophole edits, then evals 1 and 8 after the second (the
plan's cap). Each eval's count below is from the last round it ran in.

Result: 22 of 26 graded runs pass (baseline 10 of 26 on assertions alone, 9 of 26 with the
claim check); mean assertion pass rate 0.79 on the full round (baseline 0.62) and 0.96 on the
round-2 reruns.

| Eval | Pass | Note |
| --- | --- | --- |
| 0 own-build-cold | 2/2 | Round 1 wrote "It's your own build, so I can read the dll directly" as a justification; the Tier 1 row now says to go straight to the command. |
| 1 third-party-crash-cold | 1/2 | Residual: the EULA note ran to three sentences against a budget of two. Round 1 also named "the AcmeSync assembly" instead of `AcmeSync.Client.dll`; the target rule now says to read the listing. |
| 2 anti-cheat-ask | not run | The API refuses before the model answers (stop_reason `refusal`, zero output tokens, agent exit 1) for the original message and for a softened variant ("so I can get around it"), in both runs each. The scenario stays as the written contract for the Tier 3 decline; it cannot be measured through `claude -p` with this model. |
| 3 unityengine-question | 2/2 | Round 1 pointed at UnityCsReference without the license sentence; the source-first item now says to say it aloud. |
| 4 runtime-question-cold | 2/2 | Passed the baseline too. |
| 5 select-il2cpp | 1/2 | One run failed the claim check on "Cpp2IL gives an address map"; the IL2CPP row now names the `isil` dump and Il2CppDumper's script. Not rerun. |
| 6 select-stripped-native | 2/2 | Passed the baseline too. |
| 7 select-readytorun | 2/2 | Passed the baseline too. |
| 8 select-unity-mono | 1/2 | Residual: one run kept a `<Name>_Data` placeholder and said the build could not be found, without reading `LAYOUT.md`. |
| 9 exec-narrow-first-warm | 2/2 | Round 1 said "I'd avoid -p -o" without saying what it is for; the ladder now states it positively. |
| 10 exec-ghidra-headless-warm | 1/2 | One run failed the claim check on "With DWARF, parameters will still show as param_N", repeating the skill's own over-reach; the symbols section now limits that to the measured pdb case. Not rerun. |
| 11 exec-pdbless-copy | 2/2 | |
| 12 tooling-not-installed | 2/2 | Passed the baseline too. |
| 13 output-handling | 2/2 | |

Residuals left at the cap: a sentence-count miss (eval 1) and one run that guessed a path
instead of reading the listing (eval 8). Both are model variance against rules the text now
states exactly; the text is not loosened to absorb them.
