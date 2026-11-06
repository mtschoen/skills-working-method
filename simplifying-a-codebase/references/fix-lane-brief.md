# Implementation lane brief

One lane per already-verified finding. Writer lanes run on the Sonnet tier or an external harness
that can build the project (a sandboxed harness that cannot run the build is for read-only review
and drafting only). Each lane gets its own worktree in a sibling directory, never the primary
checkout.

## Preamble (template)

```markdown
You are implementing one small, already-verified fix for <project>. Your worktree (absolute path,
the ONLY directory you may modify) is named in your lane section below. FIRST ACTION: run
`git rev-parse --short HEAD` there and confirm it prints `<base sha>` and `git status --short` is
empty; if not, STOP and write the report with first line `BLOCKED: wrong base`. Never touch the
primary checkout, the consumer repositories, global settings, or any other worktree.

Rules that matter here: <the repository's compatibility policy, stated plainly>; full-word
identifiers; no narrative comments about what was removed; files under about 500 lines; <the
public-surface approval files, if any> must be updated in the same change if the surface moves;
every bug fix gets a regression test that fails before the fix and passes after (verify both
states, do not just assert it).

Before committing: the smoke test category must pass, plus every test class you touched. Do not
run the full suite; CI does. Run the repository's quality scanner on the staged diff after
`git add -A`; fix every error and fixable warning. Never edit the scanner's configuration. Never
commit logs, test result files or build output.

PR body MUST start with `Closes #<issue>` on its own line, then `## Problem` (two or three
sentences stating what was observed, not the fix), then `## Change` (what changed, by file), then,
if the public surface changed, `## Consumer migration` listing what each consumer must change by
file. Add one line with the net effect: test functions, cases and lines removed, insertions and
deletions. End the body with a line naming the harness and model that generated it.

After the pull request is open, STOP. Do not review, iterate or merge it; the reviewer owns it
from here.

## Your lane
<Issue link, the finding verbatim, the exact files, what done looks like, what is out of scope.>
```

## Review-fix round

When a reviewer's finding comes back, the follow-up lane brief quotes the finding verbatim as its
Problem, scopes the lane to that one finding, and requires a mutation check for any new test:
temporarily break the method the test guards, confirm the test fails, restore it, and record both
runs in the report.

## Test deletion rule

Consolidate duplicates and keep every distinct assertion. Merging tests that assert the same
round-trip with different inputs into one parametrized test with one row per original input is a
simplification; dropping a row to improve the line count is not. The pull request body states the
case count before and after.

## Seam removal

For each production member that exists for one test, drive the test another way first (an injected
clock, the public surface, a test-extension package that forwards to an internal member). Delete
the seam only once the test passes without it. Any seam without an equivalent stays and is listed
in the repository's test-isolation document with the reason.
