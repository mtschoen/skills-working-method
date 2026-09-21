# Machine detection

A skill only fires if an agent reads it. The durable version of every rule in this
skill is a check that runs whether or not anyone remembered. This file says which
pitfalls can be caught mechanically, by what kind of check, and how to land one.

## The three kinds of check

They are not interchangeable, and picking the wrong kind is why guards get abandoned.

| Kind | Catches | Cost | Fails when |
| --- | --- | --- | --- |
| **Static** (syntax tree or text pattern, in a linter) | Shapes visible in the source: a timeout literal, a sleep, two clock reads subtracted, an assertion on a literal truth | Near zero, runs on every edit | The shape is semantic (is this counter a fake clock or a legitimate call-counted stub?) |
| **Runtime guard** (a fail-closed fixture) | What a test *does*: opening a socket, spawning a process, writing outside a temporary root | Small per-test cost, needs a suppression path | The behavior is legitimate for some tests, so it needs an explicit opt-in marker |
| **Measurement** (a census with a recorded threshold) | Costs and trends: per-test overhead, spawn counts, import time, suite growth | A scheduled run | Treated as a gate on every change instead of a tracked number |

Rule of thumb: **prefer a runtime guard over a static check whenever the pitfall is
about what a test touches**, because a runtime guard cannot be evaded by writing the
same call a different way, and its failure message names the exact call site.

## Detectability per pitfall

Keyed to the SKILL.md catalogue.

| # | Shape | Kind | Status |
| --- | --- | --- | --- |
| 1, 3 | Stopwatch assertions (two clock reads subtracted inside an assertion) | Static | Implementable today; a working syntax-tree check exists in at least one repository. Not in any general-purpose linter. |
| 2 | Clock-derived value inside a numeric tolerance | Static | Same check, same status |
| 4 | Fake clock driven by read count | None | Deliberately not enforced. Distinguishing it from a legitimate call-counted stub is semantic, not syntactic. Review-time only. |
| 5 | Numeric timeout literal on a real process call in a test | Static | **The clearest open gap.** No assertion is involved, so every existing clock check misses it. |
| 6 | Live resource where a seam would do | Runtime | A fail-closed socket and process guard is the right instrument |
| 7 | Test resolves a real home directory | Runtime | Autouse guard failing on any write outside the temporary root |
| 8 | Coupled to implementation detail | Weak static | An assertion on a call count is greppable but often legitimate. Advisory at best. |
| 9 | Vacuous assertion (asserting a literal truth) | Static | Trivial, language-agnostic, high precision |
| 10 | Test double silently answers unmodeled input | Runtime | The double raises; this is a design rule, not an external check |
| 11 | Module-level mutation of the module table in a test file | Static | Implementable; narrow and high precision |
| 12 | Expensive per-test setup | Measurement | Per-fixture and per-call cost census |
| 13 | Eager heavy import | Measurement | Import-time budget, plus a test asserting the submodule is absent after importing the package |
| 14 | Retry or flaky marker added without a linked issue | Static | Converts a silent retry into a tracked one |
| - | Suite growth and nondeterminism debt | Measurement | The periodic census; see `references/suite-lifecycle.md` |

## Writing a static check that survives

Four properties, learned the hard way:

1. **An inline suppression marker, from day one.** A check with no escape hatch gets
   deleted the first time it is wrong. Require the marker to sit on the offending line,
   so it is visible in review and greppable for an audit.
2. **Name the file, line, and the exact shape matched.** "Wall-clock assertion at
   `test_queue.py:88`: two `monotonic()` reads subtracted inside an assert" is
   actionable. "Wall-clock violation" is not, and a check whose diagnosis is poor gets
   an escape hatch bolted on instead of being fixed.
3. **Scan test files only** for test-specific rules. Production code legitimately
   subtracts clock reads and legitimately passes timeouts.
4. **Precision over recall.** One false positive costs more trust than three misses
   cost bugs. Start from the narrow, unambiguous shape and widen only on evidence.

## Landing a guard

A check that would have prevented a pitfall belongs **on the main branch first**, via
its own small change, before it goes anywhere near the branch where you found the
problem.

Adding it to your current branch is cheaper for you and worse for everyone: no other
in-flight branch gets the protection until your work merges, and any branch that
introduces the same pitfall in the meantime does so undetected. Landing it on main
first means every branch inherits it on the next rebase, at the cost of one small extra
change.

Do it when the check is small, has no schema or interface implications, and the win is
"every current and future branch benefits". If it is larger or needs design discussion,
surface it as a proposal instead of slipping it into a small change.

**Expect the guard to find existing violations the moment it lands, and treat that as
the payoff rather than as an obstacle.** One isolation guard, landed this way,
immediately caught two pre-existing tests that had been quietly writing to a live
database. The guard justified itself before it ever prevented anything.

Sequence: build the check in a separate worktree off main, red-prove it against a known
violation, fix whatever it finds in the same change, land it, then rebase the feature
branch onto the protected main.

## Where these checks belong

- **Project-specific invariants** (this package must not be in the module table after
  importing that one; this lane may spawn at most N processes) belong in the project's
  own repository checks. They encode facts about one codebase.
- **General shapes** (a stopwatch assertion, a timeout literal in a test, a vacuous
  assertion, a retry with no linked issue) belong in a general-purpose code-quality
  linter, because every project has them. [aislop](https://github.com/scanaislop/aislop)
  is one such tool, and clock-shape detectors have been proposed there; the timeout
  literal, the vacuous assertion, and the untracked retry marker are the natural
  additions beside them.
- **Runtime guards** belong in the project's shared test configuration as autouse
  fixtures, with a documented marker for the tests that legitimately opt out. Keep
  resource opt-outs decoupled from tier classification: the marker authorizes the
  resource use, but tiering remains governed by measured duration and reliability.
  A cheap, deterministic test with an opt-out marker belongs in the per-change gate,
  not automatically demoted to a slower tier.

## What a check can never do

Three of this skill's rules have no mechanical form, and pretending otherwise is worse
than admitting it:

- **A fake clock driven by read count** is syntactically identical to a legitimate
  call-counted stub.
- **Whether a mock fakes the verify** depends on whether the mocked boundary is one the
  project owns, which no pattern can determine.
- **Whether a test asserts the behavior or the mechanism** is the judgment the whole
  skill exists to teach.

These stay in review, in this skill, and in the pre-commit checklist. The correct split
is to automate every shape that *is* syntactic, precisely so that review attention is
spent on the three that are not.
