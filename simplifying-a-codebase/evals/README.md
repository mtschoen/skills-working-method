# Evals

`scenario.md` is the seeded scenario used for the initial RED/GREEN run on 2026-11-05: eight
simplification candidates in a C# library repository with a no-compatibility policy and a release
the following week. Item 9 (an always-true constant flag), the explicit side-effect facts in item 3,
and the absent owner-ruling/caller-gate context were added after that run and have not been
exercised. Expected verdicts are listed at the end of the scenario.

## Evidence status: author-recorded, not verifiable

That run was manual and single-shot. What survives is the author's combined narrative in the two
sections below; the four subject transcripts, run references, exact supplied prompts and per-item
scores were not retained, and there is no harness that could re-run them. The results therefore
cannot be checked, reproduced or audited: they are provenance for the skill text, not evidence
that the skill works. Treat it as draft and unvalidated until a graded harness retains
per-subject output.

`scenario.md` is both task and answer key, and its "Expected with the skill" section has to be
withheld from a subject. Nothing retained shows whether it was withheld on 2026-11-05, so the
blind-task premise is unestablished as well.

## Baseline without the skill (RED, author-recorded)

Two Sonnet-tier subjects, no skill, same scenario. Both kept the manual script (item 1) and the
cross-project member (item 7) and deleted the discarded envelope (item 3). Both failed the
compatibility items: the zero-caller public member (item 2) was kept on "external consumers might
exist" with a deprecation deferred to after the release, and the dead option (item 4) was marked
obsolete for removal "in the next breaking release". Both scoped the analyzer suppression (item 6)
instead of tracing it to the production cause, and both explicitly left "risky public-surface
decisions" out because the release was near. Neither reported item 2 as a fact for the owner or
classified the sample use.

## With the skill (GREEN, author-recorded)

Two Sonnet-tier subjects, same scenario, skill read first. The author recorded verdicts matching
the expected set on all eight items, as one combined summary with no per-subject or per-item
scores: item 1 KEEP with a parser-based CI exercise; item 2 OWNER, stating zero consumer
callers as a fact, classifying the sample call GATE-ONLY and listing the facts for the owner; item 4
DELETE in place with no obsolete attribute and no deferral; item 6 CHANGE by tracing MSTEST0084 to
the class-level attribute; item 8 CHANGE with the case count stated before and after. One subject
also proposed re-grepping the counts in its own seat before quoting them, as the skill asks.

## Not yet covered

- A graded harness on a real fixture repository (the scenario is prose-only, so the evidence
  discipline of `path:line` plus grep count is asserted, not exercised), with retained
  per-subject output, the supplied prompt and the per-item score for each run.
- Item 9, and the NATURAL versus GATE-ONLY boundary examples that came with it: added 2026-11-05
  after the recorded run, never put to a subject.
- Item 3's side-effecting producer and the absent owner-ruling/caller-gate context for item 2:
  added during review after the recorded run, never put to a subject.
- The wave orchestration itself (lane fan-out, convergence ranking, adversarial verification) and
  the performance pass; both are documented from practice and untested as skill text.
