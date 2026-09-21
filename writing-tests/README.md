# writing-tests

A skill that fires at the moment a test is written, changed, or deleted. It carries the
pitfall catalogue (the shapes that make a test nondeterministic, or make it pass for the
wrong reason), the case for reaching full coverage with fewer and better tests, and the
suite lifecycle that nothing else in the testing toolchain owns.

## What it does

Two principles run through it:

- **Remove the dependency, do not enlarge the number.** A wider tolerance, a longer
  timeout, a retry, and a bumped sleep are the same move. Each makes a failure rarer
  without making the test deterministic.
- **A suite's cost is a design output.** Coverage ratchets, removal gates, and a
  regression-test-per-fix rule all only add tests. Nothing removes one unless a person
  does, so growth needs a budget, a census, and a sanctioned way to merge and delete.

Every pitfall in the catalogue states whether a machine can catch it and with what kind
of check, because the durable version of a rule is a guard that runs whether or not
anyone read the skill.

## Boundaries

It is the middle of a four-skill lineage and deliberately does not absorb its neighbours:

| Question | Skill |
| --- | --- |
| Should the test come before the code? | `superpowers:test-driven-development` |
| What makes this a good test? | **`writing-tests`** |
| The loop is slow, now what? | `fast-tests` |
| May I declare this done? | `maintaining-full-coverage` |

Each fires at a different moment, so their trigger descriptions do not compete.

## Install

Via the skills-dev installer (clone [skills-dev](https://github.com/mtschoen/skills-dev)
first):

```bash
# Unix / macOS
./install-skills.sh -y writing-tests

# Windows
install-skills.bat -y writing-tests
```

The installer copies `SKILL.md` and `references/` and excludes development-only files
(this `README.md`, `LICENSE`).

## Layout

```text
writing-tests/
  SKILL.md                          principles, four questions, catalogue, checklist
  README.md                         this file
  references/
    time-and-processes.md           the five time shapes, real resources, seams
    pitfall-catalogue.md            the remaining shapes, each with its incident
    coverage-without-bloat.md       full coverage with fewer, higher-value tests
    suite-lifecycle.md              budget, census, consolidation, safe deletion
    machine-detection.md            which pitfalls a guard catches, and how to land one
```

## Related skills

- [`maintaining-full-coverage`](https://github.com/mtschoen/skills-maintaining-full-coverage) - downstream gate. Meaningful tests remain subject to the coverage and lint bar.
- [`smoke-test`](https://github.com/mtschoen/skills-smoke-test) - downstream layer. Test authoring does not replace product-level verification.
- [`escalate-over-shortcut`](https://github.com/mtschoen/skills-escalate-over-shortcut) - partner skill for when no honest test is reachable and a skip or weakened assertion is tempting.
- `superpowers:test-driven-development` - upstream. Writing-tests assumes the red-green sequence is already in progress.

## License

MIT - see `LICENSE`.
