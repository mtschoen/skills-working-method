# fast-tests

A skill that steers agents toward fast integration-test loops without compromising the integration-tests-first philosophy. Speed up SETUP, not the test - and never replace integration tests with unit-level mocks that pretend to verify behavior.

## What it does

`fast-tests` fires when an agent observes slow test runs in a session (multi-minute wall clock or repeated re-runs blocking iteration). Authoring integration tests or tests involving sleeps, timeouts, external services, or fixture-heavy setup belongs to `writing-tests`; `fast-tests` picks up if measurement shows that the resulting loop is slow. It walks the agent through a profile-first decision tree, names the right lever per bottleneck shape, and explicitly rejects the "make this faster by mocking my own boundaries" anti-pattern.

## Install

Via the skills-dev installer (clone [skills-dev](https://github.com/mtschoen/skills-dev) first):

```bash
# Unix / macOS
./install-skills.sh -y fast-tests

# Windows
install-skills.bat -y fast-tests
```

Installs to `~/.agents/skills/fast-tests/` (or wherever your agent harness reads skills from). The installer copies `SKILL.md` + `references/` and excludes development-only files (this `README.md`, `LICENSE`, `evals/`, `workspace/`). The agent loads `SKILL.md` from the install location; this README is for human readers browsing the repo.

## Layout

```text
fast-tests/
  SKILL.md                          principles, decision tree, rationalization table
  README.md                         this file
  references/
    profiling.md                    where the time goes
    parallelism.md                  pytest-xdist, gradle parallel, xUnit collections
    shared-fixtures.md              amortize expensive setup
    persistent-environments.md      long-lived emulators, browsers, daemons
    pre-warming.md                  cache priming
    process-cleanup.md              snapshot-then-kill-tree + ppid tracking
    tiering.md                      wall-clock-based tagging
    pitfalls.md                     cross-cutting anti-patterns
  evals/                            pushback-style eval harness (dev-only)
  workspace/                        eval scratch + canned mock_repo (dev-only)
```

Each reference holds Python / JVM / .NET sub-sections. Agents navigate by topic (e.g., "I need to parallelize") and find the language section that matches their project.

## Related skills

- [`maintaining-full-coverage`](https://github.com/mtschoen/skills-maintaining-full-coverage) - orthogonal axis. Speed never licenses skipping tests.
- `writing-tests` - upstream. It owns test authoring; fast-tests starts after measured slowness blocks the loop.
- [`smoke-test`](https://github.com/mtschoen/skills-smoke-test) - orthogonal layer. Outer-loop verify vs. inner-loop wall clock.
- [`escalate-over-shortcut`](https://github.com/mtschoen/skills-escalate-over-shortcut) - partner skill for when no fast-tests lever fits and the temptation is to ship a hack.
- `superpowers:test-driven-development` - upstream. Fast-tests assumes tests exist.

## License

MIT - see `LICENSE`.
