# Suite lifecycle

The part nothing else in the testing toolchain covers. Coverage gates, removal gates,
and a regression-test-per-fix rule all push the test count in one direction. None of
them ever removes a test. A suite under good gates is **monotonic by design**, and the
only counterweight is a deliberate lifecycle.

## Why this is not hypothetical

One real suite, under exactly those three gates, all green throughout:

- **5,477 to 12,340 tests in six weeks**, 46 percent of it in the last two weeks.
- Per-test throughput actually *improved* over the same period. Job wall clock still
  went flat-to-up, because count outran throughput.
- Test density, about 11 tests per 100 lines of production code, was normal for the
  repository the whole time. Nothing looked wrong at any single moment.

That last point is the trap. There is no instant at which a growing suite looks
unhealthy. Only the trend does, and only if someone records it.

## Where the time actually goes

The following unpublished numbers are observations from one 10,820-test suite and one
1,003-test cost-profiled sample. They are an anecdote that shows why a local profile
matters, not a benchmark to generalize to another repository:

| Observation | Number |
| --- | --- |
| Slowest 5 percent of tests | **48 percent of wall clock** |
| Tests under 10 ms | 56 percent of the count, **6 percent of the time** |
| Fixed overhead per test | about **3.3 ms** |
| Phase split | setup 4.9 percent, **call 93.6 percent**, teardown 1.5 percent |
| Total fixture setup | 3.4 percent of the run |
| Collection of the full suite | 30.5 seconds, before any test runs |
| Processes: share of tests that spawn at all | 19.5 percent, averaging 8.6 spawns each |

Four conclusions for that measured suite:

1. **Pruning cheap tests had little payoff there.** Deleting every test under 10 ms
   would remove more than half the suite and 6 percent of the time. The tail held nearly
   all of that suite's opportunity.
2. **Fixtures were not the main cost there.** 93.6 percent of the cost was inside test
   bodies. Narrowing a set of autouse fixtures that summed to 3.3 ms per test would have
   been churn for under 1 percent.
3. **Fixed overhead was a real budget line there.** At 3.3 ms per test, 12,000 tests
   cost about 40 seconds before a single assertion runs, plus 30 seconds of collection.
4. **Processes were concentrated there.** In the sample, two files held 97.7 percent
   of all spawns, so those files were the useful target.

## The budget

Write it down. An unwritten budget is never exceeded and never met.

Per tier:

- **Fast tier** (the per-change gate): a wall-clock number the whole tier must stay
  under. Membership follows measured duration and reliability, so cheap deterministic
  tests stay here even when they cross a process or network boundary.
- **Slower tiers**: tests whose measured duration or reliability would block the inner
  loop. Their budget may be a longer latency target or a schedule, depending on the
  project. Architecture alone does not assign a test to this tier.

Per test: a soft ceiling for the fast tier (a few hundred milliseconds is a reasonable
starting point) enforced by measurement, not by category label. A 20 ms integration-style
test belongs in the fast tier; a 2-second unit test that spawns a process does not.
`fast-tests` owns tiering mechanics in depth.

## Measure before optimizing

Always, in this order:

1. **Durations.** The framework's slowest-N report. Two minutes of work, and it changes
   which lever you reach for.
2. **Phase split.** Setup versus call versus teardown, so you know whether you are
   fixing fixtures or bodies.
3. **A census of the specific resource you suspect**: process spawns with call-site
   attribution, connection counts, expensive-constructor call counts, import time.
4. **Only then** a profiler, on the narrowed target.

Two cautions from real profiling runs:

- **Load poisons wall clock.** A profile taken on a box at load average 60 inflates
  I/O-waiting work by roughly five to seven times. Lead with processor time and with
  deterministic counts (number of spawns, number of connections, number of constructor
  calls); use wall clock only for same-load A/B comparisons.
- **Instrumentation can lie about attribution.** In one run, a session-scoped fixture
  that globally patched process creation caused 99.3 percent of all spawns to be blamed
  on that one wrapper line, making per-site attribution unusable for the whole suite.
  Sanity-check that a census's top entry is a real call site before acting on it.

## Attack the tail

Measure the slow tail before choosing a lever. Common causes include:

- **Real process spawns.** Removing an unnecessary spawn is both a robustness fix (no
  invented timeout or kill under load) and often a wall-time win. See the ordered remedy
  in `SKILL.md`.
- **Real network waits.** Blocking wait, not computation: in one measured A/B, removing
  real outbound requests cut 29.5 seconds from a 61-second file while user processor
  time barely moved.
- **Expensive per-test construction** that should be a session-scoped template copied
  per test.
- **Eager imports** paid by every parallel worker at startup.

## Consolidation triggers

Mechanical, so they do not need a judgment call:

| Trigger | Move |
| --- | --- |
| Two or more tests differing by one literal | one parametrized test with explicit case identifiers |
| N tests each rebuilding the same expensive object | one shared fixture at the right scope, N thin tests |
| Several tests redundantly launch a process for the same contract | one real-process test for that contract; pure logic through a callable production seam |
| The same setup block copy-pasted across files | one shared fixture, or a template built once and copied |
| A test whose name references a line or branch number | rewrite as a behavior test, or delete it |

`references/coverage-without-bloat.md` has the worked before-and-after, including why
parametrizing is not the same as merging N assertions into one test.

## Deleting a test: when it is right, and how to do it safely

### When deletion is legitimate

- An exact duplicate of another test.
- A case subsumed by a parametrized test that now includes it.
- A test asserting an implementation detail that no longer exists.
- A vacuous test (asserts a literal truth, or exercises code without an assertion
  when completing without error is not the intended contract). Do not confuse this
  with tests where not raising is itself the observable contract, such as accepting
  valid input or preventing a regression.
- A test whose subject was deleted.

### When deletion is wrong

- The test traces to a bug-fix commit and is the regression guard for that bug, unless
  a named replacement still guards it.
- The literals are a golden or contract set where the specific values matter (documented
  API examples, boundary and encoding cases) rather than being "some value".
- Collapsing it into a sibling would lose fault isolation, so a failure would no longer
  say which case regressed.
- The only argument for removing it is that coverage did not drop. Measured, that is
  true for most genuine deletions and therefore proves nothing.

### The safe procedure under a coverage ratchet and a removal gate

1. **Provenance first.** Check the history of each candidate. Anything tracing to a
   bug fix is a regression guard and is governed by the rule above.
2. **Do the change.**
3. **Diff the node identifiers**, collect-only before and after. Every identifier that
   disappeared must be either on an explicit rename map (parametrizing is a rename, not
   a removal) or in the acknowledged-removal list with a reason. Watch for identifier
   deduplication changing the set silently.
4. **Diff coverage at three-decimal precision**, before and after. It must still be at
   the bar. Verified, not assumed, and remember it is a necessary check, not a
   sufficient one.
5. **Prove fault isolation survived.** Break each consolidated case one at a time
   (corrupt one parametrized literal, one attribute) and confirm the specific case fails.
   This is the check that separates a real consolidation from a coverage-preserving loss
   of signal.
6. **For any regression-guard test being reshaped**, re-verify it still goes red against
   the original broken behavior.
7. **Record the acknowledgement** with the old-to-new identifier mapping and a one-line
   reason.

## The periodic census

Run it on a schedule, as maintenance, not as a response to a crisis. Record:

| Field | Why |
| --- | --- |
| Test count, per tier | the monotonic number; the whole point |
| Delta since last census | the trend, which is the only thing that looks wrong |
| Suite wall clock, per tier | what a person actually waits for |
| Share of time in the slowest 5 percent | tells you whether the tail is still the tail |
| Slowest 20 tests, by name | the actual worklist |
| Process spawn count, with call-site attribution | the most attackable cost, and a robustness signal |
| Count of tests carrying a timeout, sleep, retry, or flaky marker | the nondeterminism debt |
| Density: tests per 100 lines of production code | context for whether growth tracks the code |

Two numbers deserve special attention because nothing else reports them: the **growth
delta** and the **nondeterminism debt count**. Both only move if someone looks.

A census is also the natural moment to ask the question a per-change gate can never ask:
is this suite still testing the product, or is it testing itself? A production module
that has grown far beyond what its behavior needs will be mirrored by a test suite that
has grown with it. Consolidating the production code is sometimes the real test-suite
fix.
