---
name: writing-tests
description: "Use when about to write, change, parametrize, or delete a test, fixture, or test double, including an integration test or one involving a real process, socket, external service, real home directory, heavy fixture setup, sleep, or timeout; when asserting on elapsed time, call counts, or clock-read order; when changing a flaky, intermittent, or transient test; when near-duplicate tests differ by one literal; when coverage has just reached the bar and the tests the change added have not been consolidated; or when deciding whether a test may be merged or deleted under a coverage ratchet or test-removal gate. Do not use after measured test slowness is blocking the loop or for a suite-wide performance pass; fast-tests owns those."
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
a fact of nature.** Optimize for cost, hold coverage at 100 percent, report the count.
Good gates (a coverage ratchet, a removal gate, a regression guard per fix) only ever
ask for more, so the suite grows unless every change pushes back: an authoring order
that reaches for an existing test before a new one, a consolidation pass before
declaring done, and a periodic census.

## When to use

- Covering new behavior, or guarding a fix you are about to make.
- Coverage just reached the bar and you are about to declare done.
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
| Whether a failing test comes before the code at all | `superpowers:test-driven-development` |
| Confirming the product works after a change | `smoke-test` |
| No honest test is reachable and you are tempted to fake one | `escalate-over-shortcut` |

This skill sits between them: `test-driven-development` says the failing test comes
first, this skill says what shape it takes and where it goes, `fast-tests` says what to
do when the loop is slow anyway, and `maintaining-full-coverage` decides whether you
are done and sends you back here to consolidate before you say so.

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
   reach for the real thing because it is already there. An underscore-prefixed import
   in a test is a prompt to test through the caller, or to question whether the helper
   should exist.
3. **In which tier?** Tier by measured duration and reliability, not by architectural
   label. A cheap, deterministic integration test belongs in the per-change gate. A
   slow or unreliable test belongs in a slower tier even if it is called a unit test.
   Real processes, networks, hardware, and clocks are risk signals to measure, not an
   automatic reason to schedule a test. `fast-tests` owns the tiering mechanics.
4. **Which existing test is nearest?** Search for the behavior, not the function name,
   then follow the authoring order below: an assertion or a case added to that test
   comes before a new function. A new function with one more near-duplicate body is the
   single largest source of suite growth.

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

## Full coverage at the lowest honest cost

100 percent is reachable with a small suite. It is usually reached with a large one
because each uncovered line gets its own test function instead of a wider path through
the front door. There is no cap on test count, because a cap produces omnibus tests.
The pressure comes from the order in which you reach for things, and from a pass over
your own tests before you stop.

### The authoring order

For any new or uncovered line, take the first step that applies.

1. **Should the line exist?** If only a test would reach it (an internal helper verified
   unreachable and not an external API, framework hook, callback, or dynamic dispatch;
   a handler for an error the guarded code cannot raise; a branch that does what the other
   branch does), delete it and the tests that exist only for it. Absent local references
   are a candidate only: always exclude supported public API surface and dynamic hooks.
   A 100 percent floor can never flag this code: the tests that reach it keep it green.
2. **Widen the nearest existing test.** The test that already performs this act at the
   behavior's seam takes one more assertion, or its parametrize takes one more case.
3. **A new case** in a parametrized test, when the path is the same and the input
   differs.
4. **Only then a new test function**, when the act itself is new.

### Red-to-green is a failing assertion

`superpowers:test-driven-development` requires a failing test before production code.
What has to fail is an assertion, under a test id you ran and watched go red for the
right reason. A new parametrize case does that: add the case, run its id, watch it
fail, make the change, watch it pass. So does a new assertion in an existing test.
Neither needs a new function, and both satisfy the iron law in full.

**A regression guard is by default a case whose id carries the issue reference**
(`id="trailing-separator-issue-412"`). The provenance stays greppable, and a later
consolidation can name the guard's replacement.

### The shape of each test

- **Test at the behavior's seam.** One test that drives a real path covers many lines
  honestly. Ten tests that each poke one internal cover the same lines and pin the
  internals in place.
- **Assert on outcomes.** An assertion that a mock was called is acceptable only when
  the call is the observable contract (a message sent, a process spawned, a documented
  polling or cleanup contract like an exactly-once close).
- **Setup lives in shared builders that build state and never act.** The act stays in
  the test body, where a reader can see it.
- **A real process only when the process is the subject** (pitfall 5).
- **Parametrize by default.** Tests whose bodies differ by a literal are one
  parametrized test with explicit case ids.
- **Property-style where the invariant is cheap to state** (round-trips, idempotence,
  ordering, conservation).
- **The one-line tick test is the anti-pattern.** A test written only so a line turns
  green asserts nothing. Go back to step 1 of the authoring order for that line.

### The consolidation pass

When coverage reaches the bar, and before declaring done, go back over the tests this
change added. `maintaining-full-coverage` requires this as a step of its completion
gate. Finding nothing to consolidate is a normal result; say so.

| What you see in your new tests | Move |
| --- | --- |
| Same path, different input | cases of one parametrized test, in the existing neighbor if there is one |
| Same act as an existing test, another fact about the outcome | add the assertion to that test |
| Asserts only that a mock was called for an incidental interaction | rewrite to assert the outcome, or drop it; retain observable call-contract assertions (cleanup, messaging, protocol) unless a named surviving assertion guards the same contract |
| Imports a private helper | move the check to the caller's seam |
| Reaches production code verified internally unreachable (candidate from absent local callers; exclude supported external APIs/options, framework hooks, callbacks, and dynamic dispatch) | delete the code and the test |

Then prove nothing was lost, using the safe-deletion checks in
`references/suite-lifecycle.md`: coverage of the touched modules is unchanged at three
decimals, breaking the guarded line turns the surviving case red, and any observable
call contract (such as exactly-once cleanup) is preserved under a named surviving assertion.

Limits, so consolidation does not become the next problem:

- One act per test id. A test that acts, asserts, then acts again is two tests.
- A parametrize shares one assertion template. A body that branches on the case is two
  tests.
- Golden and contract values are never collapsed: there the specific literals are the
  point.
- Builders never act.
- A regression case keeps its issue reference.

Report the result with the completion claim: net-new test functions, net-new cases,
and the test-line delta. Fewer test lines with coverage held is a good outcome, and a
reviewer should read it as one.

Worked cases and the full pass: `references/coverage-without-bloat.md`.

## Suite lifecycle

The per-change order and pass above keep a change from adding more than it needs. The
census catches what accumulated anyway. One real suite went from about 5,500 to about
12,300 tests in six weeks with every gate green throughout.

- **Prune by cost.** Cost concentrates in the slow tail: in one profiled suite the
  slowest 5 percent of tests were 48 percent of wall clock. Executed item count still
  matters through per-item runner overhead (about 3.3 ms per test item there, so 12,000
  executed items cost roughly 40 seconds before assertions run), while function count
  affects collection time and maintenance surface. Folding functions into parametrized
  cases reduces maintenance surface and module collection overhead, but preserves
  per-item execution overhead unless repeated acts, setups, or spawns are actually
  reduced.
- **Measure before optimizing.** `--durations`, a per-test cost census, and the
  setup/call/teardown phase split. The local profile, not another suite's ratios,
  decides the opportunity.
- **Budget per tier, written down.** An unwritten budget is never exceeded and never
  met.
- **Track growth as a number.** Test count and suite wall clock, recorded each census,
  with the delta since last time.
- **Deleting is sometimes right.** An exact duplicate; a case subsumed by a
  parametrized test that now includes it; a test of an implementation detail or of
  production code that no longer exists; a vacuous test. "Coverage did not drop" is
  never the whole argument: coverage cannot see assertion strength, and deleting a real
  test changed line coverage by exactly 0.000 percent in 10 of 12 sampled cases in one
  package. A guard for a fixed bug may be reshaped, never dropped: its named replacement
  must still go red against the original broken behavior.
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
6. For a bugfix: did you watch the regression guard (by default a case with the issue
   reference in its id) **fail on the broken code** and pass on the fix? State both.
7. Did every new test function survive the **authoring order**? If an existing test
   performs the same act, or differs by a literal, it is an assertion or a case there.
8. Does any production line in the diff exist **only because a test reaches it**?
   Verify internal unreachability (excluding supported external APIs, framework hooks,
   callbacks, and dynamic dispatch) before deleting it.
9. Have you run the **consolidation pass** and noted net-new test functions, net-new
   cases, and the test-line delta?

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
| "TDD says every fix and every function needs its own test" | It says a failing test comes first. A new case that goes red before the change is a failing test, and a function reached through its caller's test is tested. |
| "The helper is uncovered, so I will import it and test it directly" | Cover it through the caller. If no caller reaches it and it is not an external API, framework hook, callback, or dynamic dispatch, the helper is the candidate to delete. |
| "Both branches need a test, the coverage tool says so" | If the branches do the same thing, or one defends against something that cannot happen, delete the branch. |
| "Coverage is at 100 and everything is green, so I am done" | The bar is met; the cost is not yet settled. Run the consolidation pass over what you added. |
| "Consolidating might lose something, safer to leave five tests" | The pass ends with a proof: coverage unchanged, and the surviving case goes red when the guarded line breaks. Five near-identical functions are the unsafe state. |
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
- You are writing a new test function while an existing test performs the same act.
- A test imports an underscore-prefixed name from production code.
- You are mocking a collaborator to raise an error it cannot raise in production.
- A fixture or builder calls the function under test.
- You are deleting a test and the whole argument is "coverage did not drop".
- A new test file is near-identical to one that already exists.
- You are about to say done and have not looked back over the tests you added.

## References

- `references/pitfall-catalogue.md` - every shape in full, with the incident behind it.
- `references/time-and-processes.md` - the five time shapes, real processes, and how to bound a genuine hang.
- `references/coverage-without-bloat.md` - the authoring order, red-to-green without a new function, and the consolidation pass, worked.
- `references/suite-lifecycle.md` - budget, census, consolidation, safe deletion.
- `references/machine-detection.md` - which pitfalls a guard can catch, detector designs, how to land one.

## Integration notes

**`fast-tests`** - adjacent, not overlapping. That skill fires on a slow loop and
speeds up setup. This one fires at the moment a test is written and decides what the
test depends on. They agree on the important thing: never buy speed by faking the
verify. When its profile shows redundant tests, it hands the folding and deleting to
the procedure here. When this skill says "remove the spawn", the payoff is measured
with `fast-tests` tooling.

**`maintaining-full-coverage`** - downstream gate, and the link runs both ways. It
decides whether the numbers let you declare done; this skill decides how a line gets
covered and how the tests behind the numbers are consolidated. Its gate sends you here
for both. Its restructure-over-exclude rule is the same lever applied to coverage that
remove-the-dependency is applied to nondeterminism here.

**`superpowers:test-driven-development`** - upstream. It owns "test first" and the
red-green cycle, and nothing here relaxes it. Read its rules by what they protect:

- "No production code without a failing test first": the failing test may be a new
  case or a new assertion in an existing test, watched red and then green.
- "Every new function/method has a test": a test reaches it through its caller's seam
  and fails when the function is wrong.
- "'and' in the name? Split it": one behavior per test id. Cases split by id, and one
  act can carry several assertions about its outcome.
- "Never fix bugs without a test": the issue-tagged case is that test, and it must be
  watched failing on the broken code, not merely written against the fixed code.
- Its refactor step covers test code too: the consolidation pass is that step.

**`escalate-over-shortcut`** - when no honest test is reachable. Widening a tolerance,
adding a retry, or marking a test skipped to get a green run is the shortcut it exists
to catch.

**Landing a guard** - a check that would have prevented a pitfall belongs on the main
branch first, via its own small change, so every in-flight branch inherits it on the
next rebase. Guards routinely flush latent violations the moment they land, which is
most of their value.
