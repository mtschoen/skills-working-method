# Full coverage without bloat

Reaching 100 percent is not the hard part. Reaching it with a suite that stays small,
fast, and meaningful is. The two are in tension only if each uncovered line is answered
with a new test function.

`maintaining-full-coverage` owns the gate, the escalation ladder, and the report, and
sends you here for the rest: **given this uncovered line, what is the cheapest honest
way to deal with it, and once the bar is met, what can the new tests be folded into?**

The posture in one line: optimize for cost, hold coverage at 100 percent, report the
count. No cap on the count, because a cap produces omnibus tests.

## The authoring order

For any new or uncovered line, take the first step that applies.

1. **Should the line exist?** Delete it, and the tests that exist only for it, when
   only a test would reach it (verified internally unreachable; exclude supported
   external APIs/options, framework hooks, callbacks, and dynamic dispatch).
2. **Widen the nearest existing test**: one more assertion, or one more case.
3. **A new case** in a parametrized test.
4. **Only then a new test function.**

### Step 1: production code only tests reach

A 100 percent floor reports code no test reaches. It can never report code that *only*
tests reach, because those tests keep it green. So this check is yours to make, on
every uncovered line and on every line in your diff:

| Shape | Why it survives a coverage gate | Move |
| --- | --- | --- |
| An internal helper verified unreachable with no external callers, framework hooks, or dynamic dispatch | its own test covers it | delete the helper and the test |
| A handler for an error the guarded code cannot raise | a test mocks the error into existence | delete the handler and the mocking test |
| Two branches that do the same thing | one test each turns both green | collapse the conditional |
| A defensive check for a state the callers cannot produce | a test constructs the impossible state | delete the check, or move it to the boundary where the state can arrive |
| An internal parameter or option no production caller passes, not part of supported external API surface | a test passes it | delete the parameter |

The search outside the test tree identifies *candidates*, not confirmed dead code:
having no references in this repository does not establish that code is dead. A published
library function, exported module, or optional parameter may be used only by downstream
consumers. Framework hooks and callbacks can be invoked dynamically without direct static
references (for example, `BaseHTTPRequestHandler.handle_one_request` dispatching to a
subclass's `do_GET` method via `getattr`, or dynamic plugin and event dispatch).
Deleting external API surface or dynamic hooks alongside their tests leaves line coverage
unchanged at 100 percent, so coverage checks cannot detect the loss.

Therefore: across all deletion rules, treat absent local references as a candidate only.
Verify internal unreachability and strictly exclude supported external APIs and options,
framework lifecycle hooks, callbacks, and dynamic dispatch before deleting code or its tests.
When you cannot prove a state or entry point is unreachable, ask a human before you delete it.

Scope: the lines your change adds, the lines the gate shows uncovered, and the
functions you are changing. Test-only code you notice elsewhere is reported or filed,
not swept into an unrelated change.

### Steps 2 to 4: red-to-green without a new function

Test-driven development asks for a failing test before the production change. What has
to fail is an assertion under a test id you ran. Issue 412 says `normalize_path("logs/")`
must return `"logs"`:

```python
@pytest.mark.parametrize(
    ("raw_path", "expected"),
    [
        pytest.param("logs", "logs", id="plain"),
        pytest.param("logs//app", "logs/app", id="double-separator"),
        pytest.param("logs/", "logs", id="trailing-separator-issue-412"),
    ],
)
def test_normalize_path(raw_path, expected):
    assert normalize_path(raw_path) == expected
```

Run `test_normalize_path[trailing-separator-issue-412]`, watch it fail with the wrong
value, fix the code, watch it pass. That is the whole red-green cycle, with zero new
functions. The issue reference in the id is what makes the case a regression guard:
`grep issue-412` finds it, and anyone who later reshapes the test can name the case
that replaces it.

A new function is right when the act is new: a different entry point, a different
call, a different kind of outcome (a raise where the neighbors return). A different
input to the same call is a case.

## Cover through the public seam

A test that drives a real path from the module's front door covers many lines at once,
and covers them *because the behavior needed them*. A test that pokes one internal
covers one line and pins that internal in place.

The arithmetic matters at scale. Ten front-door tests can reach the same coverage as
sixty internal ones, at a sixth of the wall clock, a sixth of the maintenance surface,
and with the property that the next refactor breaks zero of them instead of sixty.

The failure mode to watch for is the coverage report used as a worklist read
line-by-line: "line 147 is red, write `test_line_147`". Read it as a *map* instead. A
cluster of red lines usually means one untested path, not eight untested lines.

A test that imports an underscore-prefixed name has left the seam. Either the caller's
test can reach the same lines with one more case, or nothing in production calls the
helper and step 1 applies.

## Assert on outcomes, build with builders

- **Outcome first.** Assert what the act produced: a return value, a raised error,
  state a reader of the system could observe. An assertion that a mock was called is
  acceptable only when the call *is* the observable contract: a message sent, a process
  spawned, a documented polling or cleanup contract (such as `resource.close.assert_called_once()`).
  A test whose only assertion is an incidental mock call passes for any implementation that
  makes the call, including a wrong one. Conversely, do not drop call-contract assertions
  merely because line coverage is held: a neighboring return-value assertion will still pass
  if `close()` is called twice or omitted, even while mutating the return line makes the survivor
  red. Retain observable call contracts unless a named surviving assertion guards the same contract.
- **Builders build state and never act.** Shared setup belongs in a builder or fixture
  that returns the state a test starts from. The call to the code under test stays in
  the test body. A fixture that performs the act hides the one line a reader needs, and
  makes every test that uses it the same test.
- **A real process only when the process is the subject.** Otherwise call the logic
  in-process through a production seam (`SKILL.md`, pitfall 5).

## Parametrize as the default shape

**The consolidation trigger is mechanical:** two or more tests whose bodies differ by
one literal are one parametrized test. No judgment required.

```python
# BEFORE - fourteen functions differing by two literals each
def test_parses_iso_date(): assert parse("2026-01-02") == date(2026, 1, 2)
def test_parses_slash_date(): assert parse("2026/01/02") == date(2026, 1, 2)
# ... twelve more

# AFTER - one function, fourteen cases, fourteen independent pass/fail signals
@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("2026-01-02", date(2026, 1, 2)),
        ("2026/01/02", date(2026, 1, 2)),
        # ...
    ],
    ids=["iso", "slash", ...],
)
def test_parses_supported_date_formats(raw_value, expected):
    assert parse(raw_value) == expected
```

Two properties to preserve when you do this:

- **Give explicit case identifiers.** They keep each case readable in a failure report
  and keep the node identifiers stable and mappable, which matters under a
  test-removal gate. Pytest makes colliding parameter identifiers unique by adding
  suffixes; it still runs every case, but the generated identifier set can change.
- **Keep the cases independent.** Parametrizing preserves one pass/fail signal per case.
  That is the whole point, and it is why parametrizing is not the same as merging.

## The unit is the act

What decides whether two tests are one test is the act: the call to the code under
test, with its input.

- **Same act, different input: cases.** One parametrized test, one id per input, one
  pass/fail signal per id.
- **Same act, same input, another fact about the outcome: one test.** N tests that
  each repeat the identical call to assert one more attribute of its result are one
  test with those assertions, or better, one comparison against the whole expected
  value so a failure shows every difference at once.
- **Different acts: different tests.** Never chain them. A test that acts, asserts,
  then acts again hides the second act behind the first failure and is two tests.

That boundary is what keeps consolidation from producing an omnibus test: several
inputs or several acts pushed through one body, where the first failure masks the rest
and the report names the test instead of the case.

| Situation | Move |
| --- | --- |
| N tests differ by one input literal | one parametrized test, N cases, explicit identifiers |
| N tests perform the same act and assert different facts about its outcome | one test, one act, those assertions (or one whole-value comparison) |
| N tests share expensive setup but perform different acts | one shared builder at the right scope, N tests |
| N tests assert the same thing through different entry points | keep the one at the behavior's seam, delete the rest, note why |
| N tests are byte-identical | one test; the rest are pure duplication |

## The consolidation pass

Run it when coverage reaches the bar, before declaring done, over the tests this change
added. `maintaining-full-coverage` makes it a step of the completion gate. It is the
refactor step of red-green-refactor applied to the tests.

**1. List what you added.** New test functions, new cases, new builders. For each new
function, ask which row it is:

| What you see | Move |
| --- | --- |
| Same path as a sibling or an existing test, different input | fold into cases; use the existing parametrized neighbor if there is one |
| Same act as an existing test, another fact about the outcome | add the assertion to that test |
| Asserts only that a mock was called for an incidental interaction | rewrite to assert the outcome; drop it if another test already does; retain observable call-contract assertions unless a named surviving assertion guards the same contract |
| Imports a private helper | move the check to the caller's seam, usually as a case |
| Reaches production code verified internally unreachable (candidate from absent local callers; exclude supported external APIs/options, framework hooks, callbacks, and dynamic dispatch) | delete the code and the test |
| None of the above | it stays; a new act earns a new function |

**2. Prove nothing was lost.** These are the safe-deletion checks from
`suite-lifecycle.md`, scoped to your change:

- Coverage of the touched modules, at three decimals, is the same before and after.
- For each distinct production line the folded cases guard, break that line and watch
  the matching case go red, by its id. Prefer breaking the production line to
  corrupting a case's literal: the first proves the case still guards the code, the
  second only proves the case can fail. Restore at once: the break is a probe, not a
  production change, so it needs no test of its own.
- A regression case still goes red against the original broken behavior.

**3. Record the delta** with the completion claim, in the message and the PR body:
net-new test functions, net-new cases, test-line delta, all measured against the
change's base (not against an intermediate state of your own work). A framework's test
total counts cases, so it cannot show this; the delta can. Fewer test lines with coverage
held is a good outcome. "Nothing to consolidate" is a valid result when every new
function is a new act; say it, so the reader knows the pass ran.

**Limits.** Each one marks where a consolidation has gone too far:

- One act per test id.
- A parametrize shares one assertion template. If the body branches on the case
  (`if expected is None: ... else: ...`), it is two tests wearing one name.
- Golden and contract values are never collapsed: documented API examples, boundary
  and encoding cases, anything where the specific literal is the point.
- Builders never act.
- A regression case keeps its issue reference through every reshaping.

Worked, for a change that added five separators to a date parser and wrote one test
function per separator beside an existing two-case parametrized test: the five
functions become five cases of the existing test (ids `dot`, `space`, `underscore`,
`pipe`, `comma`). Breaking the production line handling the pipe separator in the parser
turns exactly `test_parses_supported_date_formats[pipe]` red (proving the surviving case
guards the production logic, not merely that the case can fail). Coverage is unchanged.
Net-new test functions: 0. Net-new cases: 5.

## Property-style where the invariant is cheap to state

Some behaviors are a single sentence that covers an infinite table: a round-trip
(`decode(encode(x)) == x`), idempotence (`f(f(x)) == f(x)`), an ordering that must be
total, a quantity that must be conserved, a parser that must never raise on any input.

Where the invariant is that crisp, a property test replaces a table of examples and
finds the case nobody thought of. Where it is not, do not force it: a property whose
statement is longer than the examples it replaces is a worse test.

Keep generated-input property tests out of the per-change gate if they are slow, and
pin any counterexample they find as an explicit regression case with a fixed input.

## What coverage cannot tell you

This is the load-bearing limitation, and it is a property of the measurement, not a
weakness of any particular tool.

**Measured on a real 318-test package** (baseline 95.353 percent), deselecting one test
at a time, which is coverage-equivalent to deleting it:

| Outcome | Count |
| --- | --- |
| coverage changed by exactly 0.000 percent | **10 of 12** |
| measurable drop | 2 of 12 (0.186 and 0.279 points) |

A rule that auto-passed a deletion whenever coverage held would have waved through
roughly **83 percent of genuine test deletions**.

Why:

- **Line coverage saturates.** Most tests exercise lines their siblings already cover,
  so removing one is invisible. The bigger and healthier the suite, the truer this gets,
  which is backwards from what you want in a safety net.
- **Coverage is blind to assertion strength by construction.** A test asserting a
  precise value and a test asserting nothing cover identical lines. Weakening a test in
  place is not even a removal, so an inventory gate misses it too, but coverage cannot
  see it *in principle*.
- **Corollary:** a 100 percent floor does not mean deleting a test will be noticed. It
  means every line is touched at least once, by at least one test, asserting anything
  at all.

**What to do instead.** Track test count and test node identifiers as a signal
*independent* of coverage, and never make one gate conditional on the other. They catch
disjoint failure modes: a coverage drop means code paths lost their only exercise; a
removed node identifier means a specific behavior stopped being asserted. If the
inventory gate is noisy, fix its *diagnosis* (say which removal it found and why) rather
than adding an escape hatch keyed on coverage.

Use three-decimal precision when comparing coverage numbers. At default precision, even
the drops that do exist round away.

## The tick test, and its degenerate forms

The anti-pattern: a test written for no reason except that a line was red.

Symptoms:

- Its name references a line, a branch, or a function rather than a behavior.
- Its body calls one function and asserts the call did not raise.
- It asserts on a literal truth, or on a mock's own configuration.
- It would not fail if the function's body were replaced with a different correct
  implementation, or with a wrong one.

The test for whether a test earns its place: **name the bug it would catch.** If you
cannot, it is not covering behavior, it is covering lines.

When a line resists an honest test, the answer is upstream of the test. Start at step
1 of the authoring order: a line no behavior needs is deleted, not covered.
`maintaining-full-coverage` has the rest of the ladder: restructure the production code
so the line is reachable honestly, then ask a human, and only then, with explicit
approval, an exclusion. "Write a tick test" is not a rung on that ladder.

## Patch coverage versus total coverage

A useful split when a suite is large enough that measuring the whole thing on every
change is expensive:

- **The per-change gate** asks: is every line this change added or modified executed by
  a test, and did the total not go down? That is answerable from the diff, and it is
  the thing a change can fairly be held responsible for.
- **The absolute floor** (100 percent per package, integration tier included) is
  measured on a schedule. A regression there files an issue rather than blocking an
  unrelated change.

This keeps the bar without making every change pay for the whole suite. The bar itself
does not move.
