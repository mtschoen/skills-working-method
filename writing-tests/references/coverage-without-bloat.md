# Full coverage without bloat

Reaching 100 percent is not the hard part. Reaching it with a suite that stays small,
fast, and meaningful is. The two are in tension only if each uncovered line is answered
with a new test function.

`maintaining-full-coverage` owns the gate, the escalation ladder, and the report. This
file owns the question it does not ask: **given that you must cover this line, what is
the cheapest honest test that does it?**

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

## Parametrize is not "collapse into one test"

The tempting next step is to fold N single-assertion tests into one test with N
assertions. **Do not.** It destroys fault isolation: the first failing assertion masks
the rest, so one regression hides the other N-1, and a failure report names the test
rather than the case.

When N tests each assert one attribute on the same expensively-constructed object, the
waste is the *construction*, not the test functions. Move construction into a shared
fixture at the right scope and keep the N thin assertions. Node identifiers are
unchanged, coverage is unchanged, and only the redundant rebuilding goes away.

| Situation | Move |
| --- | --- |
| N tests differ by one input literal | one parametrized test, N cases, explicit identifiers |
| N tests assert different attributes of the same object | one shared fixture, N thin tests |
| N tests assert the same thing through different entry points | keep one, delete the rest, note why |
| N tests are byte-identical | one test; the rest are pure duplication |

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

When a line genuinely resists an honest test, the answer is upstream of the test.
`maintaining-full-coverage` has the ladder: write the test, then restructure the
production code so the line is reachable honestly, then ask a human (the line may be
dead, and dead code is a bug, not an exception), and only then, with explicit approval,
an exclusion. "Write a tick test" is not a rung on that ladder.

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
