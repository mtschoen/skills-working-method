# Pitfall catalogue

The shapes that are not about time or live resources. For those two families see
`references/time-and-processes.md`, which carries shapes 1 through 7 of the SKILL.md
table in full.

Each entry: the shape, what it cost somewhere real, the remedy, and whether a machine
can catch it. Detector designs are in `references/machine-detection.md`.

## Coupled to implementation detail

**Shape.** The test asserts on *how* the code worked rather than *what* it did: a call
count, a synchronous-versus-threaded execution order, a clock-read ordinal, a fixture
that pins an internal field.

**What it cost.** Three tests in one session, all green beforehand, all coupled:

| Coupled to | Broke when | How it surfaced |
| --- | --- | --- |
| `reader.call_count == 2`, implying a synchronous refetch | the refetch moved to a background thread | deterministic failure; the thread was never scheduled before the assert |
| a fixture with a fixed timestamp and no injected collaborator | the code under test gained the ability to fetch | the suite started making **real requests to live providers** on every run |
| a fake clock selecting by read ordinal | an extra clock read was added elsewhere | test kept passing while silently ceasing to exercise its branch |

The third is the dangerous one: it did not fail. Coverage still *displayed* 100.00
percent; only a strict 100 percent floor caught the single missed line. A test that
stops testing anything while staying green is worse than one that breaks, because
nothing tells you.

The second is the expensive one: it turned a unit suite into a live-traffic generator
against an endpoint that was already rate limiting.

**Remedy.** Assert on the observable outcome, not on the number of calls that produced
it, unless the call pattern *is* the contract (a documented poll interval, an
idempotence guarantee, a "called at most once" requirement). Any test that constructs a
cache or database fixture must inject its collaborator: if it *can* reach the network
when the implementation changes, eventually it will. When a change makes a test fail,
decide whether it was testing behavior or mechanism before "fixing" it; loosening the
assertion is usually the wrong move, and the fix is to re-anchor on behavior.

**Detectable?** Weakly. `call_count` assertions are greppable but frequently legitimate,
so a detector is advisory at best. Review-time concern.

## Passes for the wrong reason

**Shape A: the mock fakes the verify.** The test mocks a boundary the project owns (its
own service layer, its own repository, its own module interface), so the assertion is
satisfied by the mock's configuration rather than by the product working. This is
`fast-tests` Principle 6 territory; the one sanctioned exception is a **verified fake**
of an owned seam, and the load-bearing part is a contract suite that runs the same
parametrized tests against both the real implementation and the fake. Without the
contract suite the fake is just a mock that fakes the verify.

**Shape B: the patch lands on a seam the code no longer uses.** Covered under "verify
the network is actually mocked" in `references/time-and-processes.md`. The general form
is broader than networking: any patch target named by string can go stale while the
test keeps passing.

**Shape C: the vacuous test.** A long exploratory block ending in an assertion that
cannot fail. A real case: an implementer committed two test methods of 72 and 77 lines,
each a stream-of-consciousness narrative about which paths could not be reached
headless, each ending in `Assert.True(true, "<excuse comment>")`. Both compiled, both
passed, both contributed a green tick and asserted nothing. The working test was the
sibling method right after them. Deleting both held coverage at 100 percent, proving
they contributed nothing.

**Remedy.** For A: mock only genuine external boundaries, or build the contract suite.
For B: make the double raise on unmodeled input and assert it was actually exercised, so
a stale patch target is loud. For C: delete and re-verify. If coverage *drops* on
deletion, the no-op was accidentally covering something through its setup, so write a
real assertion rather than restoring the no-op. Coverage is no defense here: a test
ending in a vacuous assertion does not advance coverage at all.

**Detectable?** Partly. Shape C is trivially detectable by pattern (an assertion on a
literal truth, in any language). Shapes A and B are semantic.

**A note on delegated work.** When an implementing agent's completion message mentions
"iterative exploration", "long commentary block", "a wart", or "a reviewer will likely
flag this", that is the agent telling you it knowingly left debugging-as-test in the
diff. Bounce it for cleanup before spending a review round.

## Shared state and cross-worker races

**Shape.** Tests pass serially and fail, or lose coverage, under a parallel runner;
or a test's outcome depends on which tests ran before it in the same worker.

**What it cost.** A 100 percent line-coverage gate began failing intermittently, each
run reporting a different small set of uncovered lines, always in the same one module.
The tests exercising those lines passed every time, and a serial run reported a clean
100 percent. Cause: a package `__init__.py` eagerly imported a heavy submodule, pulling
it into the module table during parallel-worker bootstrap, *ahead of* the coverage tool's
own startup in that worker. Coverage then cached a do-not-trace decision for the file.
The module still ran; coverage simply was not watching it in that worker. Sibling modules
in the same directory, imported later, traced fine, which is what made it look impossible.

**Remedy.** Defer the import (resolve those names through a module-level attribute hook,
keeping a type-checking-only import so static analysis still resolves them), and pin the
invariant with a test asserting the submodule is absent from the module table after
importing the package. Red-prove that test by restoring the eager import.

Do **not** fix it by lowering the gate, adding a coverage pragma, excluding the file, or
dropping parallelism. The lines were genuinely covered; the measurement is what broke.

Related shapes in the same family: raw assignment into the module table leaking across a
whole session; a global environment variable set by one test and observed by another
that expected its absence; a singleton or in-process cache surviving between tests.

**Diagnostic order that actually worked.** Establish the baseline flake rate before
theorizing (run the gate five or more times on the commit *before* the suspect change;
one or two green runs prove nothing about a flake that is already green four runs in
five). Then inspect the measurement tool's own state rather than the test.

**Detectable?** Partly. A module-level mutation of the module table inside a test file is
a syntactic pattern. The eager-facade shape is best pinned by a project-specific
invariant test rather than a general detector.

## Expensive setup repeated per test

**Shape.** Every test rebuilds something that could be built once and copied, or built
once per session.

**What it cost.** In one profiled suite, measured rather than guessed:

| Cost center | Measured | Fix |
| --- | --- | --- |
| Full schema initialization per test (28 tables, 61 indexes, 73 migrations) | 725 calls across 1,003 tests, about 13.9 ms of processor time each | session-scoped migrated template, copied per test |
| A journal-mode pragma on every connection | 0.778 ms versus 0.049 ms for a bare connect, **15.9x**, about 11.7 connects per test | cache the decision per path, issue the pragma once per process |
| Full application construction per test | 139 calls in one file, 11.55 s of that file's 21.48 s, **53.8 percent** | module-scoped application and client fixture; keep per-test builds only for boot-behavior tests |

The pattern to copy was already in the same suite: a session-scoped repository template
built once (55.84 ms, 9 process spawns) and copied per test at 5.30 ms.

**A measured non-cost worth knowing.** The same profile found 13 autouse fixtures and 14
function-scoped fixtures per test, and the total was 3.3 ms per test, 3.4 percent of the
run. Narrowing them would have been churn for under 1 percent. Fixture *count* is not the
signal; fixture *cost* is, and only a measurement tells them apart.

**Remedy.** Build once, copy per test. Prefer copying a materialized template over
re-running the build, because a copy is cheap and a build is not. Keep the per-test build
for the handful of tests whose subject *is* the build.

**Detectable?** Measurable, not lintable. A per-fixture and per-call cost census is the
instrument; see `references/suite-lifecycle.md`.

## Eager imports taxing collection

**Shape.** A heavy dependency is pulled in at import time by a module that most tests do
not need, so every parallel worker pays it at startup and collection.

**What it cost.** Collection of one 10,820-test suite took 30.5 seconds. Importing the
command-line module cost 967 ms, of which 344 ms was a web framework pulled in
transitively by a module that had nothing to do with the web surface. Only the web
package needed it.

**Remedy.** Defer the import behind a module-level attribute hook. Measure with the
interpreter's import-time flag before and after.

**Detectable?** Measurable. An import-time budget is a viable gate.

## "Intermittent" failures that are deterministic on content

**Shape.** A failure that surfaces "sometimes" against varied inputs is framed as
transient, which licenses a retry that papers over a real bug.

**What it cost.** A review pipeline's error rate was written off as transient after a
single re-run passed. Pushed to run the same input twelve times, it failed eight of
twelve, 67 percent. Not random at all: deterministic on whether the model's response
prose happened to contain triple backticks, which it often did because the change under
review was *about* backtick handling. Once identified as content-conditioned, the bug was
a 30-line parser fix away.

**Remedy.** Whenever you are about to describe a failure as intermittent, transient, or
flaky, run it at least 10 times against the same input first. Above roughly a 5 percent
rate, treat it as deterministic-on-content until proven otherwise. If it truly is
transient (1 in 100), a retry may be right, but the data should justify that conclusion
rather than your prior.

**Detectable?** The re-run discipline is a process rule, not a pattern. But a retry or
flaky marker added without a linked issue reference *is* detectable, and that check
converts the silent retry into a tracked one.

## Tolerances papering over nondeterminism

**Shape.** A tolerance, a retry, a widened bound, or a sleep, added because a value the
test does not control moved.

This is the core principle restated as a pitfall, and it is worth keeping in the
catalogue because it is the shape every other entry degrades into when the remedy feels
expensive. The tell is that you are reasoning about *how much margin is enough*. That
question has no correct answer, because the quantity on the other side is unbounded.
Remove the dependency instead.

**Detectable?** Partly, per family: clock-derived tolerances and process timeout
literals are syntactic; a sleep in a test is syntactic; a retry decorator is syntactic.
A tolerance on a genuinely floating-point computation is legitimate and must not be
flagged.
