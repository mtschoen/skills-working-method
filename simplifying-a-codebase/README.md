# simplifying-a-codebase

Agent skill: how to run a simplification pass over a repository, from the audit lenses and lane
briefs through owner rulings, implementation lanes, removal gates and the audit of cleanup pull
requests, plus the measurement rules for a performance pass.

Origin: the MFTLib trio release-readiness work of October and November 2026 (MFTLib, file-wizard,
git-wizard), condensed from the audit waves of 2026-10-14, 2026-10-16, 2026-10-19 and 2026-10-26,
the deletion audit of crew cleanup pull requests, and the performance pass that followed. Core
theses: (1) delete redundant code, never merely unused code; (2) "no caller" is a fact for the
owner, not a verdict; (3) evidence is `path:line` plus a grep count, re-checked in the orchestrator
seat; (4) removals are gated by tests and CI exercises, not by prose; (5) compatibility is a
repository policy, read it before the first verdict; (6) performance claims come from a quiet
machine with interleaved runs and the same harness before and after.

## Status

Draft. One manual RED/GREEN run was recorded on 2026-11-05, and `evals/README.md` says why that
record is author narrative rather than verifiable evidence:

- RED baseline: two Sonnet subjects, no skill, on `evals/scenario.md` (eight simplification
  candidates with a release next week). Both kept the manual script and the cross-project member,
  but both reasoned from backward compatibility on the zero-caller public member and the dead
  option ("mark it obsolete, remove in the next breaking release"), deferred public-surface
  decisions because of the release date, scoped the analyzer suppression instead of tracing it to
  its cause, and neither reported the zero-caller member as a fact for the owner with the sample
  use classified.
- GREEN: see `evals/README.md` for the with-skill result on the same scenario, and for the
  retained-evidence gap that keeps this skill draft.

## Layout

- `SKILL.md`: the pass, the removal table, compatibility and deadlines, red flags, pull request
  shape.
- `references/audit-lane-brief.md`: shared preamble, reusable area briefs, verifier brief,
  synthesis rules.
- `references/removal-classification.md`: DEAD, SUPERSEDED, INTERNAL-NOISE, USEFUL-LOST, UNSURE,
  and the "no caller is a fact" procedure.
- `references/fix-lane-brief.md`: implementation lane contract, review-fix round, test deletion
  and seam removal rules.
- `references/performance-pass.md`: measurement rules and brief shapes.
- `evals/`: the scenario and the recorded baseline and with-skill results.
