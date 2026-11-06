# Performance pass

Same wave shape as a simplification pass, with measurement as the only admissible evidence.

## Rules

1. **Measure first, then optimize, then re-measure with the same harness.** The pass opens with
   an attended stopwatch of real workflows and a baseline table of interleaved medians. Each
   optimization lands with before and after counts from the same harness in its pull request body.
2. **Timings only count from a quiet machine.** Lanes may run a benchmark to prove the command
   works, but label the numbers format-only; other lanes building in parallel contaminate
   timings. The orchestrator measures every lane's build in one quiet window afterwards and posts
   one combined table on the issue.
3. **A quiet window is discrete, announced and scheduled ahead**, with every elevated or attended
   step listed; release the machine between windows. Gate on a rolling-mean CPU load (for example
   thirty samples under fifteen percent) with no build or test process alive, not on a few
   consecutive quiet seconds. Shut down resident virtual machines before cold measurements.
4. **Interleave.** Round-robin the variants with a fresh state directory per run, discard a
   warm-up round, trim the top and bottom, report median, minimum and maximum, and rank only by
   non-overlapping ranges. Report every ratio with its run-to-run spread; call a gap real or absent
   only when it clears the spread.
5. **Priority order:** interactive responsiveness (no hang over 500 ms, at most one per five
   seconds), then wall time even at the cost of memory, then memory; never out-of-memory.
6. **A measurement pass's regressions are the work.** Profile with a real profiler (code-reading
   attributions are wrong often enough to be useless as evidence) and fix before release; never
   publish and defer.
7. **Keep digging** while ranked options remain untried. Do not offer to close the issue after a
   modest win; the pass ends when the options are exhausted or the owner closes it.
8. **Option lanes.** Split a slow phase into independent option lanes from one base commit, one
   pull request each with `Part of #<issue>` (never `Closes`), a `## Problem (measured)` section
   quoting the baseline numbers, `## Change`, `## Tests` listing the fail-before cases, and a
   `## Measurement` section that defers to the orchestrator's quiet-window table.
9. **Release baselines.** Commit hand-captured quiet-machine baselines under a dated, sha-named
   file and compare the release candidate against them with the project's compare command;
   never commit raw logs or captures.

## Measurement brief shape

```markdown
FIRST ACTION: run `git rev-parse HEAD` in the worktree and confirm it starts with <sha>, else STOP.
Generate ONE synthetic input and reuse it for every run so the input is identical.
ALTERNATE variants between runs (A, B, A, B, ...) so thermal and cache effects do not bias one
side. Verify each variant is what it claims to be (for a vectorized build, disassemble and count
the instructions). Report: a verdict in two sentences (gain in percent per scenario, and whether
it exceeds run-to-run noise, stated as the spread between min and median within a variant), then
the table. Time budget: about 40 minutes.
```
