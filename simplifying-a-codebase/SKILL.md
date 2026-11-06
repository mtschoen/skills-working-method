---
name: simplifying-a-codebase
description: "Use when a codebase needs a simplification pass: pre-release cleanup, dead or redundant code, duplicate or confusing APIs and concepts, over-abstraction, residue of past pivots, test bloat, a line-count alarm, or a performance pass before shipping; also when a lane or review is about to delete something because nothing calls it."
---

# Simplifying a Codebase

## When to use

Use when the question is "is this the simplest thing that does the job?" over a whole repository or
area, rather than one change. Triggers: "are we really done with release readiness?", "if we had
designed this from scratch, is this where we would have ended up?", a line count that alarms the
owner, a library that grew through pivots, "find dead code, stale docs, duplicate APIs that do the
same thing but different", a cleanup pull request that adds more than it removes, or a lane about
to recommend deleting a script, member or test because nothing calls it.

Not for: executing one agreed change across call sites (effective-refactor), coverage and lint
gates (maintaining-full-coverage), or catching shortcuts in your own draft (escalate-over-shortcut).

## Core principle

Delete only redundant code, never merely unused code. "No caller" is a fact to report with the
member's apparent purpose; the owner rules on intent. The lens is the owner's question, and "yes,
this is what from-scratch looks like" is a valid verdict. Do not manufacture findings.

## The pass

A pass is a wave: audit, rank, file, fix, land, re-audit. Judgment stays in the orchestrator seat;
reading and drafting go to lanes.

1. **Frame the lens in one owner question** and name what earlier waves already fixed, so lanes
   verify against the current tree instead of refiling. Example lenses: from-scratch design;
   consumer-specific features hiding in a library; two members for one job; parameters with one
   value at every call site; options no caller sets; names that do not say what the member does.
2. **Fan out read-only audit lanes by area**, one shared preamble plus one scoped brief each
   (template in [references/audit-lane-brief.md](references/audit-lane-brief.md)). Every usage
   claim carries `path:line`, the exact grep command and its count, or the label `unverified`.
   At most twelve to fifteen findings per lane, and a mandatory "Checked and fine" section so
   coverage is known. An empty findings section with a thorough checked-and-fine section is a
   good report.
3. **Rank by cross-lane convergence**, then re-grep every count in the orchestrator seat before
   quoting it anywhere. Lane counts drift from the tree within hours.
4. **Verify the strongest claims adversarially**: give one lane the top claims with the
   instruction to refute them with its own evidence. A verdict table with uniform wording is
   worthless; one refutation with evidence is worth ten confirmations.
5. **Tier the findings**: fix now; owner ruling needed (facts, never removal recommendations);
   defer.
6. **File each finding as an issue** with the filing-issues contract, adding one sentence on what
   the from-scratch design is. Rulings go in the issue body, never in comments. Label exactly one
   of agent-ready or needs-design; sequence a flood with a wait label rather than queueing forty
   at once.
7. **Bring decisions to the owner one per turn, with the inventory attached**: every instance of
   the same pattern across the surface, earlier rulings, outside guidance, and one proposed
   consistent rule. Record the ruling in the repository's decision log in the same change.
8. **Implement in lanes under a fixed contract**
   ([references/fix-lane-brief.md](references/fix-lane-brief.md)): fresh worktree, base commit
   verified as the first action, targeted tests while iterating, one pull request per finding.
9. **Gate removals mechanically, not by prose**: an approval test that pins the public surface,
   a test that every public member has a production or sample caller, a CI step that at least
   parses every maintained script. Never a regex, reflection or IL guard over source text.
10. **Audit the cleanup pull requests before merging them**, classifying every removed unit
    ([references/removal-classification.md](references/removal-classification.md)). The next
    wave names what this one fixed.

## Deciding a removal

| Observation | Verdict |
| --- | --- |
| Unused return payload or envelope from an internal member | Retain the call and its side effects; return void and remove the unused payload only after checking construction and return-expression evaluation for observable effects, preserving any such effects |
| Two helpers with identical bodies | Consolidate: delete the duplicate, keep the one every caller's project can reach (check the project reference direction), move its tests onto the survivor |
| Flag with the same value at every call site; option no caller sets | The value every caller passes is the live behavior: inline it, then delete the parameter and the alternative no call site can reach, subject to the compatibility policy |
| Public member with zero consumer callers; a sample prints it | A fact for the owner: classify the sample use by where the value goes, NATURAL (control flow, a computation or a persisted artifact consumes it) or GATE-ONLY (its only destination is a console write or a variable nothing reads); definitions and one example of each in [references/removal-classification.md](references/removal-classification.md); never delete on your own |
| Manual script, diagnostic or dev tool CI never runs | Keep it; add a CI exercise or a syntax parse so it stops looking dead |
| Analyzer or inspection says unused | A candidate list only: grep the whole solution including sibling projects and read one caller |
| Many warnings from one rule; one suppression silences them all | Trace to the production cause and fix it there; per-site suppression with a reason only for deliberate bad-code fixtures |
| Tests asserting the same thing with different inputs | Consolidate, keeping every distinct assertion as a row |
| Production seam that exists for one test | Drive the test another way first; what cannot be replaced stays and is documented |
| Consumer-shaped feature inside a library | Rebuild it in the consumer on a general primitive; measure the primitive before claiming a performance need |
| A dependency would replace hand-written code | The dependency counts toward complexity, a third-party one more so; the net test includes its weight |
| A concept that exists only to serve another retired concept | Delete the concept, not its patches |

## Compatibility and deadlines

Read the repository's compatibility policy before the first verdict. Where it says no backward
compatibility: delete in place, no obsolete attribute, no dual read paths, no "next breaking
release", and never ask whether to preserve compatibility. Where no policy exists, ask the owner
once as a policy question, not per item. A release date never defers a cleanup: everything that is
not a new feature lands before the release, and ship-or-defer is the owner's question to raise,
not yours.

## Red flags

| Rationalization | Reality |
| --- | --- |
| "Nothing calls it, delete it" | A fact, not a verdict. Find the intent: decision log, documented feature not yet wired, identical consumer code hoisted on purpose. Past passes overturned three of four such recommendations. |
| "CI never runs it" | Manual tools and diagnostics are kept and exercised, not culled. |
| "External consumers might depend on it" | Under a no-compatibility policy this reasoning is void; the question is whether a real use case exists. |
| "Mark it obsolete for now" | Preservation cruft. Delete in place or leave it; never both paths. |
| "The release is next week, defer the public-surface items" | Shape before ship. Cleanup is pre-release work unless it adds a feature. |
| "One suppression line fixes all 27" | It hides the next real hit. Trace to the cause. |
| "The analyzer says unused" | Cross-project false positives are routine. Grep and read a caller. |
| "Net-negative lines, so cut the test" | Net-negative is the expectation, not a rule; every distinct assertion survives. |
| "Net-negative lines, so skip the CI exercise" | A kept tool's parse step adds lines and is still the simplification: it turns "looks dead" into "demonstrated". |
| "A library would replace this file" | Count the dependency's weight before calling it simpler. |
| "The report needs findings" | "Checked and fine" is a result. |

## Pull request shape for a cleanup

The body starts with `## Problem` (what was observed, not the fix), then `## Change` by file, then
`## Consumer migration` by file when a public surface moves, and a net-effect line: test functions,
cases and lines removed, insertions and deletions. No narrative comments in code about what was
removed. Docs describe the current contract only, with no tombstone sentences about retired
designs. When a cleanup pull request adds more than it deletes, ask whether the simplification goal
was met before opening it.

## Performance pass

A performance pass is the same wave with measurement as the evidence: baseline on a quiet machine,
interleaved runs, the same harness before and after in every pull request body, and digging until
the ranked options are exhausted. Method and rules in
[references/performance-pass.md](references/performance-pass.md).

## Common mistakes

- Quoting a lane's count in a ruling without re-grepping it in the orchestrator seat.
- Writing "remove it" where the finding is a fact and the owner has not ruled.
- Posing an owner question without the inventory of every instance of the pattern.
- Keeping the finished plan, audit reports or lane briefs in the repository; delete them when the
  wave is done, git history is the archive.
- Running the full suite in every lane; targeted tests while iterating, full suite in CI.
