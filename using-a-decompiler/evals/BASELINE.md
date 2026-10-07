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
