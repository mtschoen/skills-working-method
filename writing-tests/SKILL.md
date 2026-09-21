---
name: writing-tests
description: "Use when about to write, change, parametrize, or delete a test, fixture, or test double, including an integration test or one involving a real process, socket, external service, real home directory, heavy fixture setup, sleep, or timeout; when asserting on elapsed time, call counts, or clock-read order; when changing a flaky, intermittent, or transient test; when near-duplicate tests differ by one literal; or when deciding whether a test may be deleted under a coverage ratchet or test-removal gate. Do not use after measured test slowness is blocking the loop or for a suite-wide performance pass; fast-tests owns those."
---

# Writing Tests

## Overview

A test is a claim about behavior that a machine can re-check forever. Most bad tests
fail that definition in one of two ways: they check something other than the behavior
(a call count, an elapsed duration, a mock's own configuration), or they re-check it
unreliably because the test depends on something the test does not control.

**Core principle: remove the dependency, do not enlarge the number.**

A wider tolerance, a longer timeout, a retry decorator, a `sleep` bumped from 1 to 5:
these are the same move wearing four costumes. Each makes the failure rarer without
making the test deterministic, and each hides that the test is asserting on something
nobody owns. The fix is always to take the uncontrolled thing out of the test: inject
the clock, inject the bytes, run the subject in-process, fake the outcome you were
waiting for.

The second principle follows from the first: **a suite's cost is a design output, not
a fact of nature.** Test count is made monotonic by good gates (a coverage ratchet, a
removal gate, a regression test per fix all only add), so the suite grows without
anything pushing back. The counterweight is a deliberate lifecycle: a budget, a
census, and a sanctioned way to merge and delete.

## When to use

- Writing a test for new behavior, or a regression test for a fix you just made.
- Writing or extending a fixture, a test double, or a fake.
- Reaching for a real process, socket, device, clock, or home directory in a test.
- Reaching for a number: a timeout, a tolerance, a sleep, a retry count, a call count.
- Changing a test because it started failing "sometimes".
- Deciding whether a test may be merged into another or deleted.

## When NOT to use - the handoffs

| Situation | Skill that owns it |
| --- | --- |
| The inner loop is slow and you need to speed up setup, fixtures, parallelism, tiering | `fast-tests` |
| Coverage percentage, lint findings, the report file, whether you may declare done | `maintaining-full-coverage` |
| Whether to write the test before the code at all | `superpowers:test-driven-development` |
| Confirming the product works after a change | `smoke-test` |
| No honest test is reachable and you are tempted to fake one | `escalate-over-shortcut` |

This skill sits between them: `test-driven-development` says write the test first,
this skill says what makes it a good one, `fast-tests` says what to do when the loop
is slow anyway, and `maintaining-full-coverage` decides whether you are done.

## Before you write the test: four questions

Answer all four before typing. Each has a wrong default that costs later.

1. **What behavior?** Name the observable outcome in one sentence, without naming a
   function. "Invalid schema exits with status 2" is a behavior. "`validate` is called
   once" is a mechanism. If you can only phrase it as a mechanism, you are about to
   couple the test to implementation detail.
2. **At which seam?** Find the narrowest seam at which the behavior is observable and
   the uncontrolled world is excluded. Prefer the public entry point of the unit over
   its internals (one honest test through the front door covers many lines), and prefer
   an injected collaborator over the real resource behind it. The wrong default is to
   reach for the real thing because it is already there.
3. **In which tier?** Tier by measured duration and reliability, not by architectural
   label. A cheap, deterministic integration test belongs in the per-change gate. A
   slow or unreliable test belongs in a slower tier even if it is called a unit test.
   Real processes, networks, hardware, and clocks are risk signals to measure, not an
   automatic reason to schedule a test. `fast-tests` owns the tiering mechanics.
4. **Does a test already cover this?** Search for the behavior, not the function name.
   If a near-identical test exists, extend it or parametrize it. A new file with one
   more near-duplicate is the single largest source of suite growth.

## The pitfall catalogue

Every row says whether a machine can catch it. `references/machine-detection.md` has
the detector designs and how to land one; `references/pitfall-catalogue.md` has the
full shape-by-shape treatment with the incidents behind each.

| # | Shape | Remedy | Machine-detectable? |
| --- | --- | --- | --- |
| 1 | Stopwatch: sleep, then assert on measured elapsed time | Mock the clock, assert on the call pattern | Yes, AST: two clock reads subtracted inside an assertion |
| 2 | Tolerance on a clock-derived value (`approx(5.0, abs=0.01)`) | Inject the clock so the value is exact | Yes, AST: a clock-derived value inside a numeric tolerance |
| 3 | Upper-bound stopwatch (`elapsed < 2.0` proving an early return) | Assert the early return happened, not how fast | Yes, same detector as 1 |
| 4 | Fake clock driven by read count ("calls 1-4 then call 5") | Drive the fake from state; `sleep` advances it | No. Semantic, not syntactic. Review-time only |
| 5 | **A literal kill bound on a real process** (`timeout=10`) | Remove the spawn; see below | Yes, AST: a numeric literal `timeout=` in a test |
| 6 | Real privileged or live resource where a seam would do | Inject synthetic bytes at the I/O chokepoint | Partly: a fail-closed socket and process guard catches it at runtime |
| 7 | Test resolves a real home directory and rewrites live config | Autouse fixture patching the resolver, not `expanduser` | Yes, runtime: a guard fixture that fails on writes outside the temp root |
| 8 | Coupled to implementation detail (call counts, sync-vs-thread) | Assert the outcome, unless the call pattern is the contract | Weakly. `call_count` is greppable but often legitimate |
| 9 | Passes for the wrong reason: the mock fakes the verify | Mock only genuine external boundaries; verified fakes need a contract suite | Partly: a vacuous assertion (`assert True`) is trivially detectable |
| 10 | Patch applied at a seam the code no longer uses | Assert the double was actually exercised | Runtime: a double that raises on unmodeled input |
| 11 | Shared state and cross-worker races under parallel runners | Isolate per worker; never mutate global module state at import | Partly: module-level `sys.modules` mutation in a test file |
| 12 | Expensive setup repeated per test (schema build, app build) | Session-scoped template copied per test | Measurable: per-fixture and per-call cost census |
| 13 | Eager imports taxing collection in every worker | Defer the heavy import behind a module `__getattr__` | Measurable: import-time budget, and an absent-from-`sys.modules` test |
| 14 | "Intermittent" failure assumed random | Re-run the same input at least 10 times before believing it | No, but a retry marker added without a linked issue is detectable |

### Pitfall 5 in full: the literal kill bound

This is the newest and the least guarded, because it is not an assertion, so every
existing wall-clock guard walks straight past it. It looks responsible. A baseline
agent given a generator whose output must be executed wrote exactly this, and
justified the number as "an order-of-magnitude safety margin against scheduling
contention on a loaded runner":

```python
# WRONG - a real interpreter per test, bounded by a number the author invented
def _run_generated_script(schema_definition):
    source = build_migration_script(schema_definition)
    return subprocess.run(
        [sys.executable, "-c", source],
        capture_output=True,
        text=True,
        timeout=10,
    )
```

Under a loaded runner (load average in the tens is normal on a shared box) a healthy
run dies on that bound, the job goes red for a reason unrelated to the change, and the
whole suite is re-run. The margin argument is the trap: no margin is large enough,
because the bound is competing with an unbounded queue.

**The remedy is ordered. Take the first step that applies.**

1. **Ask why the test spawns at all.** If the behavior under test is pure logic written
   in the project's own language, expose that logic through a callable production seam
   and test the seam directly. Do not execute a generated script in-process as a
   subprocess substitute: `SystemExit`, uncaught exceptions, signals, standard streams,
   encoding, and interpreter startup can all behave differently. When any of those is
   the contract, retain a real-process test for that distinct contract.

   Consolidate only redundant launches. Keep one real-process test per distinct
   process-level contract, with separate cases where stdout, stderr, environment,
   signals, encoding, or exit behavior can vary independently.

2. **Only when the subject genuinely is a script or an external binary** is a real
   process legitimate. Tier it by measured duration and reliability: a cheap,
   deterministic process test can stay in the per-change gate. In every tier,
   **the author does not pick a number**. A bound that a healthy run can ever approach
   is a performance assertion in disguise.

   Concretely, the shared bound is one named constant in the suite's test-support
   module, read from an environment variable with a generous default, imported by every
   test that needs one. Not a fixture (the value is a constant, not per-test state), and
   not a different literal per call site. Size it at the order of a minute, not a few
   seconds: it exists to turn a true hang into a failure before a job's own ceiling
   kills the run uninformatively. The per-test cap a test-runner plugin provides is a
   backstop for the same purpose, sized the same way, never tuned to a test's typical
   duration.

3. **A test that must observe timeout handling fakes the timeout's outcome** instead
   of waiting for it. Raise the timeout exception, or return the exit status a timed-out
   process would return. Waiting out a real expiry buys no extra confidence and costs
   the expiry every run.

Two root causes worth naming, because they manufacture this pitfall at scale:

- **An API that makes `timeout` a required argument** forces every test author to
  invent a literal at every call site. Dozens of unrelated arbitrary small bounds
  accumulate, each individually defensible. Give the wrapper a default drawn from the
  shared helper so a test has to opt in to a number rather than opt out.
- **A global per-test cap** (the pytest-timeout shape) is itself a wall-clock bound.
  It is a hang detector, not a performance assertion, so size it that way: generous,
  environment-overridable, and never tuned to "how long this test usually takes".

This ties straight into the lifecycle section. Real spawns dominate the slow tail, so
deleting an unnecessary spawn is simultaneously the robustness fix and the largest
single wall-time win available.

## Full coverage with fewer, better tests

100 percent is reachable with a small suite. It is usually reached with a large one
because each uncovered line gets its own test instead of a wider path through the
front door.

- **Test through the public seam.** One test that drives a real path covers many lines
  honestly. Ten tests that each poke one internal cover the same lines and pin the
  internals in place, so the next refactor breaks ten tests that were never about the
  behavior.
- **Parametrize by default.** The consolidation trigger is mechanical: two or more
  tests whose bodies differ by one literal are one parametrized test.
- **Property-style where the invariant is cheap to state** (round-trips, idempotence,
  ordering, conservation). One property replaces a table of examples and finds the
  case you did not think of.
- **Coverage cannot see assertion strength.** In one unpublished 318-test-package
  anecdote, not a general benchmark:
  deleting one real test at a time changed line coverage by exactly 0.000 percent in
  10 of 12 sampled cases. A test asserting a precise value and a test asserting
  nothing cover identical lines. So "coverage did not drop" is never, on its own,
  evidence that no test value was lost.
- **The one-line tick test is the anti-pattern.** A test written only so a line turns
  green (and its degenerate form, a long narrative ending in a vacuous assertion) adds
  count, wall clock, and maintenance surface while asserting nothing. Delete it and
  re-verify: if coverage drops, its setup was accidentally covering something, so
  write a real assertion rather than restoring the no-op.

Details and worked cases: `references/coverage-without-bloat.md`.

## Suite lifecycle

Nothing else in the testing toolchain pushes back on growth. One real suite went from
about 5,500 to about 12,300 tests in six weeks with every gate green throughout.

- **Budget per tier and per test.** Fixed per-test overhead is real and measurable
  (about 3.3 ms per test in one profiled suite, so 12,000 tests cost roughly 40
  seconds before a single assertion runs). Write the budget down; an unwritten budget
  is never exceeded and never met.
- **Measure before optimizing.** `--durations`, a per-test cost census, and the
  setup/call/teardown phase split. In one profiled suite the cost was 93.6 percent
  inside test bodies and 3.4 percent in fixtures. Treat that as a reason to measure
  locally, not as a general fixture-cost ratio.
- **Attack the measured tail.** In that same suite the slowest 5 percent of tests were
  48 percent of wall clock; tests under 10 ms were 56 percent of the count and 6 percent
  of the time. The local profile, not those anecdotal ratios, decides the opportunity.
- **Track growth as a number.** Test count and suite wall clock, recorded each census,
  with the delta since last time. A ratchet that only goes up needs a number that
  someone looks at.
- **Deleting is sometimes right.** Legitimate cases: an exact duplicate; a case
  subsumed by a parametrized test that now includes it; a test asserting an
  implementation detail that no longer exists; a vacuous test. Safe removal under a
  coverage ratchet and a removal-acknowledgement gate means all three of: coverage
  verified still at the bar after removal (verified, not assumed), the removal
  acknowledged with a written reason, and, if the test guarded a fixed bug, the
  replacement that still guards it named explicitly.
- **Run a periodic census** as a maintenance task, not as a crisis response.

Full procedure, census contents, and the merge-versus-delete decision:
`references/suite-lifecycle.md`.

## Pre-commit checklist

Under a minute, on the tests in your diff.

1. Does every new test assert an **outcome**, not an incidental call count or an
   elapsed time? A call-pattern assertion is valid when that pattern is documented
   behavior, such as a polling interval or spawn-count contract.
2. Any numeric literal that is a **timeout, tolerance, sleep, or retry**? Justify it or
   remove the dependency that needs it.
3. Does any test start a **real process, socket, device, or clock**? If yes: is that
   the subject, or just the plumbing? Is its tier justified by measured duration and
   reliability?
4. Could any test write to a **real home directory or a live config**? Check the
   resolver, not the one filename you know about.
5. Is any fake driven by **how many times** it was called rather than by state?
6. For a bugfix: did you watch the regression test **fail on the broken code** and pass
   on the fix? State both.
7. Is any new test a **near-duplicate** of one already in the file? Parametrize instead.
8. Did the suite's **test count and wall clock** move more than you expected?

## Rationalization table

| Excuse | Reality |
| --- | --- |
| "10 seconds is a generous margin for a script that takes 50 ms" | No margin beats an unbounded queue. A loaded runner is not slow, it is unscheduled. Remove the process or use the shared hang-detection bound; tier the test from measurements. |
| "The tolerance just absorbs scheduling jitter" | It absorbs it until it does not. A tolerance on a value you do not control is the flake, deferred. |
| "The test needs a real process to prove the output actually runs" | Separate pure logic from process semantics. Test pure logic through a callable production seam, and keep a real-process test for each distinct exit, output, signal, environment, or encoding contract. |
| "I mocked the network, so the suite is offline" | Verify it. Patching one seam while the code calls another leaves real traffic: one suite made real TLS handshakes to a live host for 48 percent of a file's wall clock with mocks in place. |
| "It only fails sometimes, so it is flaky" | Run the same input at least 10 times before believing that. Failures that look random are routinely deterministic on input content, and "flaky" licenses a retry that hides a real bug. |
| "Coverage did not drop, so nothing was lost" | Measured: deleting a real test changed coverage by exactly 0.000 percent in 10 of 12 cases. Coverage is blind to assertion strength by construction. |
| "Asserting call_count is how I know it was used" | Assert what it produced unless the call pattern is itself documented behavior. Incidental call counts break when the code changes shape; contract-level polling or spawn counts are legitimate. |
| "Our fake clock never touches real time, so we are fine" | A fake that decides by read count encodes the implementation's call pattern. Add one clock read elsewhere and the test silently stops exercising its branch, still green. |
| "Adding a test is always safe" | Every test is permanent cost: wall clock, maintenance, and one more thing that breaks on the next refactor. A near-duplicate is a parametrize case, not a test. |
| "I will mark it slow and move on" | A marker with no measurement is exclusion with extra steps. Tier by measured duration and by what the test touches. |
| "We can fix the suite cost later, coverage matters more" | The gates make count monotonic. Nothing removes tests unless a person does. Later is when the number is twice as big. |

## Red flags - stop and reconsider

- You are choosing a number (timeout, tolerance, sleep, retry) and reasoning about how
  much margin is enough.
- You are widening an existing number to make a failure go away.
- You just wrote `time.sleep` in a test.
- You are about to spawn a process to execute code written in this project's language.
- A test double returns a plausible answer for input it does not actually model.
- You are asserting on an incidental `call_count` or on the ordinal of a clock read.
- You added a retry or a flaky marker before running the same input 10 times.
- You are writing a test whose only purpose is to turn one line green.
- You are deleting a test and the whole argument is "coverage did not drop".
- A new test file is near-identical to one that already exists.

## References

- `references/pitfall-catalogue.md` - every shape in full, with the incident behind it.
- `references/time-and-processes.md` - the five time shapes, real processes, and how to bound a genuine hang.
- `references/coverage-without-bloat.md` - reaching the bar with fewer, higher-value tests.
- `references/suite-lifecycle.md` - budget, census, consolidation, safe deletion.
- `references/machine-detection.md` - which pitfalls a guard can catch, detector designs, how to land one.

## Integration notes

**`fast-tests`** - adjacent, not overlapping. That skill fires on a slow loop and
speeds up setup. This one fires at the moment a test is written and decides what the
test depends on. They agree on the important thing: never buy speed by faking the
verify. When this skill says "remove the spawn", the payoff is measured with
`fast-tests` tooling.

**`maintaining-full-coverage`** - downstream gate. It decides whether the numbers let
you declare done. This skill decides whether the tests behind those numbers mean
anything. Its restructure-over-exclude rule is the same lever applied to coverage that
remove-the-dependency is applied to nondeterminism here.

**`superpowers:test-driven-development`** - upstream. It owns "test first" and the
red-green cycle. The bugfix corollary lives here: a regression test must be watched
failing on the broken code, not merely written against the fixed code.

**`escalate-over-shortcut`** - when no honest test is reachable. Widening a tolerance,
adding a retry, or marking a test skipped to get a green run is the shortcut it exists
to catch.

**Landing a guard** - a check that would have prevented a pitfall belongs on the main
branch first, via its own small change, so every in-flight branch inherits it on the
next rebase. Guards routinely flush latent violations the moment they land, which is
most of their value.
