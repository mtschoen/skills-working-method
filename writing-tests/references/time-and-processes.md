# Time and processes

Everything a test cannot control, ordered by how often it bites. The through-line is
the skill's core principle: **remove the dependency, do not enlarge the number.**

## The five time shapes

The first three touch the real clock. The fourth fakes the clock correctly and couples
to it anyway. The fifth does not assert on time at all, which is exactly why the guards
written for the first three walk past it.

### Shape 1: the stopwatch

```python
# WRONG
start = time.monotonic()
wait_with_kick(0.2)
assert time.monotonic() - start >= 0.18
```

The assertion is about the machine's scheduler, not about the code. It passes on an
idle laptop and fails in a loaded job.

```python
# RIGHT - assert the documented contract directly, and instantly
assert mock_sleep.call_args_list == [call(0.5), call(0.5)]
```

Mocking `sleep` and asserting on the call pattern is strictly stronger than the elapsed
measurement: it verifies "polls every 0.5 seconds", which is what the docstring
promises and what the stopwatch could only approximate.

### Shape 2: a tolerance on a clock-derived value

```python
# WRONG - and the subtle one. No sleep, no real timing intent.
mock_wait.assert_called_once_with(pytest.approx(5.0, abs=0.01))
```

This test asserts on the argument passed to a **mocked** function, so it looks
deterministic. It is not: the production code stamps `monotonic() + 5` in one place and
computes `deadline - monotonic()` in another, so the value is structurally "5.0 minus
however long the intervening work took". A real occurrence of this drifted from 10 ms
to 67 ms under load, failed in four separate jobs inside a 25-minute window, and
blocked every pull request that merely contained the file.

The author had already noticed the drift and answered it with a 10 ms tolerance. **A
tolerance is not a fix for a value you do not control.** Widening `abs=` only makes the
flake rarer. Inject the clock so the stamp and the read come from the same fake and the
value is exactly 5.0.

### Shape 3: the upper-bound stopwatch

```python
# WRONG - proving an early return by timing it
start = time.monotonic()
wait_with_kick(30)
assert time.monotonic() - start < 2.0
```

Assert that the early return happened (the state it produced, the call it skipped), not
how quickly.

### Shape 4: a fake clock driven by read count

No real time anywhere, and still wrong.

```python
# WRONG - the fake decides by counting how many times it was read
reads = {"count": 0}

def fake_clock():
    reads["count"] += 1
    return 1901.0 if reads["count"] <= 4 else 2000.0
```

```python
# RIGHT - the fake models time causally: sleeping is what advances it
state = {"waited": False}

def fake_clock():
    return 2000.0 if state["waited"] else 1901.0

def fake_sleep(_seconds):
    state["waited"] = True
```

`count <= 4` encodes an assumption about the implementation's internal clock-read
pattern. It is implementation coupling in a clock costume.

**Why it is worse than a flake.** When a lock in the code under test started reading
the clock one extra time, every ordinal downstream shifted. "Call 5 is the deadline
check" quietly became false, and the test kept passing while no longer exercising the
deadline-expired branch it was written for. No failure, no error, no signal. Only a
strict 100 percent coverage floor caught it, and the summary line still rounded to
100.00 percent. A state-driven fake is immune: it never asks *how many times*, only
*what has happened yet*.

This shape is the known detection gap. Telling a counter that feeds a fake clock apart
from a legitimate call-counted `side_effect` list is semantic, not syntactic, so it
stays a review-time concern.

### Shape 5: a literal kill bound on a real process

```python
# WRONG - all three variants, all invented by the test author
run_captured(command, timeout=10.0)
_run(command, timeout=15)
# ... and a 20-second bound around a test that waits out real 2-second expiries
```

Not an assertion, so no wall-clock assertion guard sees it. Under a loaded runner
(load average in the tens on a shared box is ordinary) a healthy run dies with a
process-timeout error, the job goes red for a reason unrelated to the change, and CI is
re-run in full.

The remedy is ordered; take the first step that applies. The full ordering with code is
in `SKILL.md` under "Pitfall 5 in full". In brief:

1. **Remove the spawn when process semantics are not the contract.** Expose pure logic
   through a callable production seam and test it directly. Keep a real-process test
   when exit behavior, output, signals, environment, encoding, or interpreter startup
   is the behavior under test; an in-process execution is not equivalent for those.
2. **If the subject genuinely is a script or an external binary**, tier the test by
   measured duration and reliability, and take the bound from one shared test-side
   helper. The author never picks a number.
3. **If the test must observe timeout handling**, fake the timeout's outcome (raise the
   timeout exception, or return the exit status a timed-out process returns) instead of
   waiting for a real expiry.

**Two manufacturing causes.** An API whose `timeout` parameter is *required* forces a
literal at every call site, which is how dozens of unrelated arbitrary bounds
accumulate; give the wrapper a default from the shared helper. And a global per-test cap
is itself a wall-clock bound, so size it as a hang detector (generous,
environment-overridable, never tuned to a test's typical duration), never as a
performance assertion.

## Per-language clock injection

| Language | Tool |
| --- | --- |
| Python | `time-machine` (patches at the C layer once; roughly 100x faster than scanning every module import, and the gap grows with project size; note it avoids mocking `monotonic` / `perf_counter` by default). `freezegun` / `pytest-freezer` also work (both freeze `monotonic` and `perf_counter` as well), but patch at the Python import layer. |
| JavaScript / TypeScript | `vi.useFakeTimers()` (vitest), `jest.useFakeTimers()` |
| .NET | `TimeProvider` plus `FakeTimeProvider`, first-party since .NET 8 |
| Java | Inject `java.time.Clock`; `Clock.fixed(...)` in tests |
| Go | Inject a clock interface, or `testing/synctest` |

Design principle: **do not call the clock, be given the clock.** Current time is a
dependency like any other.

For genuinely asynchronous waits, poll a condition with a timeout; never a fixed sleep.
Fixed sleeps are the "async wait" anti-pattern, the most-cited root cause in the
standard flaky-test taxonomy.

The one exception to all of the above: an explicitly marked benchmark, with a generous
tolerance, that is not part of the per-change gate.

## Real processes, sockets, devices, and homes

Same principle, different resource.

### Inject bytes at the chokepoint

When a test reaches for a privileged or live resource but the resource's only job is to
hand bytes to logic you want to cover, do not take the resource. Find the single wrapper
where operating-system bytes enter the unit under test and inject synthetic,
correctly-shaped buffers there.

A real case: a filesystem-journal parser's coverage depended on opening a live raw
volume handle, which needs administrator rights and an interactive elevation prompt, and
on parsing an entire drive. Every byte entered through one wrapper. Adding a
data-injection hook beside the failure-injection hook already there let the parsing logic
chew synthetic buffers built from the documented structure layout: coverage went from
80 percent to 100 percent line and branch, with no elevation, running in continuous
integration.

Keep at least one live test per distinct platform contract as ground truth that the
synthetic layout still matches reality. Put it in the tier chosen from its measured
duration and reliability. Coverage green on fakes is not the same as matching the real
system. The genuinely irreducible lines (the real syscall fall-through itself) belong
to those live tests and are not a coverage gap.

**The same rule covers ambient environment checks, not just byte-feeding resources.** A
production guard that consults real process identity (an elevation check, a "am I
interactive" check) lets tests fall through into paths that need a desktop; on a
headless runner that means an unbounded wait and a hung suite. Make the guard injectable
and pass a deterministic fake. Never let a test's behavior branch on the host's ambient
state.

### Verify the network is actually mocked

Patching one seam while the code calls another leaves real traffic, silently. In one
measured suite, roughly 60 patch decorators named `runner.post_to_discord` while the
live path ran `checkin -> notify -> post_to_discord`, a different seam. The test config
carried a real, resolvable hostname, so every affected test did real DNS, TCP, and TLS:
**29.5 seconds of a 61-second file, 48 percent of its wall clock**, verifying nothing.
User CPU barely moved between the two arms, confirming it was pure blocking wait.

It was also a latent outage amplifier: at a 5-second per-request timeout, an unreachable
host would have cost up to 820 seconds in that one file, against a job ceiling of 1800.

The durable fix is not more patches, it is a **fail-closed guard**: an autouse fixture
that makes any real socket connection raise. Then a missed seam is a loud error naming
the call site, not a slow green run.

### Never resolve a real home directory

Continuous integration is exactly where this is not caught, because its home directory
is disposable. The damage lands on a developer's machine, silently, and is noticed days
later.

A real case: a feature gained a *second* home-resolved configuration path. The existing
tests patched the first resolver but not the new one, so running the suite rewrote the
developer's live agent configuration to point at a temporary directory. It shipped green.

Rules:

- Patch **the resolver function**, not `expanduser` globally. Monkeypatching
  `Path.expanduser` or `Path.stat` wholesale breaks the test framework's own traceback
  machinery.
- Prefer an autouse fixture, so a test added later inherits the isolation instead of
  re-opening the hole.
- When a feature gains a *second* home-resolved path, grep for the tests patching the
  first and extend them. A partially patched test is more dangerous than an unpatched
  one, because it looks isolated.
- Verify by size and modification time on the real file before and after one suite run,
  not by reading it.
- Reviewing a diff: any new home resolution in production code is a prompt to ask "what
  patches this in tests?"

### Test doubles must refuse what they do not model

A double that returns a plausible-but-different answer for unmodeled input turns into an
unbounded reimplementation of the real system. A real case: an in-memory stand-in for a
version-control layer tried to reimplement the real tool's path-matching grammar, and two
separate pull requests each burned four to five review rounds chasing a fresh divergence
in the same surface, because "make the fake match a little better" has no finish line.

The fix was to narrow the contract, not deepen it: model only the ordinary cases that
real call sites actually pass, and raise a specific named error on everything else. That
deleted about 166 lines of translator, kept every real-backend assertion passing, and
gave reviewers a stable contract to check against.

When a double keeps taking findings of the shape "the fake disagrees with the real
system on input X", first check whether input class X is even reachable from a real
production call site. If it is not, make the double raise on it. If it is, the behavior
belongs in a real-backend contract test, not grafted onto the fake as one more case.
