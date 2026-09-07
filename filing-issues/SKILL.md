---
name: filing-issues
description: Use when about to open an issue, ticket, or follow-up on a forge (Gitea, GitHub, GitLab) for something observed during work - a failed job, a wrong review, a flaky gate, a loose end at session close, a "we should" noticed mid-task. Also use when triaging or rewriting an issue someone else filed. Fires before the create call, not after.
---

# filing-issues - tie the sighting to its mechanism

An issue is either a claim that a specific mechanism is wrong, or an
incident report: something happened, here is exactly where and when.
Both are valid. What makes a queue fill without draining is a third
thing: a sighting of an already-known mechanism filed as if it were
new, or an incident with no identifiers, so nobody can ever tie it to
anything. Every issue therefore says which of the two it is and carries
the identifiers that let the next reader connect it.

## Route before you write

Take the first branch whose predicate holds:

1. **The fix is smaller than the issue.** One file, mechanical, no
   design choice, under about five minutes. Fix it now in the current
   change (or a one-commit PR). Do not file. A formatting drift, a
   wrong argument order, a typo in a flag name: fixing costs less than
   the filing plus triage plus a crew round.
2. **The mechanism is known and already has an issue.** Search open
   issues for the mechanism's words (the component, the wrong
   behavior), not the sighting's words (the PR number). Found one: add
   a comment with the new evidence in the shape below. Do not file.
3. **Otherwise file.** Known mechanism with no issue: file a mechanism
   issue. Mechanism not known: file an incident report. Do not guess a
   mechanism to satisfy the template; an incident report with honest
   "unknown" is worth more than a confident wrong cause, because the
   evidence stays usable when the real cause turns up.

Search means running the query, not remembering. Gitea:
`GET /repos/{owner}/{repo}/issues?state=open&type=issues&q=<words>`. GitHub:
`GET /search/issues?q=repo:{owner}/{repo} is:issue is:open <words>`. GitLab:
`GET /projects/{id}/issues?state=opened&search=<words>`.

## The issue contract

**Title.** Mechanism issue: the component and the wrong behavior, true
of every sighting. Incident report: what happened, where, when.

**Body**, in this order:

- **Mechanism:** what component does what wrong, one to three
  sentences. Incident report: "Unknown", then the leading hypothesis
  if there is one, labeled as a hypothesis.
- **Evidence:** every sighting as a bullet with the identifiers that
  make it re-findable: PR, job id, sha, timestamp, file path, log line,
  host and load if timing is involved. Two sightings on different
  inputs beat one.
- **Detection:** how a recurrence would be caught automatically once
  fixed: the guard, test, status check, or log line that would go red.
  Incident report: what to capture next time it happens (the log, the
  process tree, the coverage diff) so the mechanism can be identified.
- **Done when:** the observable state that closes the issue. Mechanism
  issue: not "fix the reviewer" but "the review body's reviewed sha
  equals the PR head at post time, enforced by a test". Incident
  report: "mechanism identified and this issue linked or merged into
  its mechanism issue" is a complete answer.
- **Decision:** the one question a human must answer before work
  starts, or "None" when the next step is unambiguous. An issue with
  an unstated decision sits unanswered.
- **Related:** each existing issue number this touches and the
  relation in two words: "same class", "blocks", "superseded by",
  "possible cause", or "None".

**Labels:** whatever the repo's triage reads (agent-ready,
needs-design, needs-info), set to match the Decision line. An incident
report with no hypothesis usually wants the label that means "needs
investigation", not the one that means "ready to implement".

## Comment contract (branch 2)

"Another instance:" then the Evidence bullet for the new sighting, then
one line if it changes the Mechanism or Detection.

## Example: mechanism issue

Sighting: the reviewer graded PR 2517 round 4 on sha 6d43b389; head was
951cbfc6, pushed forty minutes earlier, with all three findings fixed.

> **Title:** reviewer grades the sha it was enqueued with, not the PR
> head at run time
>
> **Mechanism:** the review job resolves the head sha at enqueue and
> never re-reads it, so any push during the queue wait is invisible to
> the grade.
>
> **Evidence:**
>
> - PR 2517 round 4: reviewed 6d43b389, head 951cbfc6
> - PR 2513 round 3: reviewed 7379d4e7, head 8aa82c5c
>
> **Detection:** a test asserting the posted review's reviewed sha
> equals the PR head fetched immediately before posting.
>
> **Done when:** that test exists and passes; a push during queue wait
> produces a review of the new head or a requeue.
>
> **Decision:** re-review the new head, or requeue and lose the slot?
>
> **Related:** #2476 same class (job trusts state captured at start).

## Example: incident report

Sighting: a coverage gate read 99% against a 100% floor on one CI run
and 100% on a rerun of the same commit; nothing was inspected.

> **Title:** tools coverage 99% on main 7be46b8a at 03:12 UTC, 100% on
> rerun at 03:40, no code change
>
> **Mechanism:** Unknown. Hypothesis: a timing-dependent branch in the
> dashboard code is skipped under load (runner load 9.4 at 03:12, 4.1
> at 03:40).
>
> **Evidence:**
>
> - main 7be46b8a, run at 03:12 UTC on steamdeck: 99%, coverage report
>   not saved
> - main 7be46b8a, rerun at 03:40 UTC on steamdeck: 100%
>
> **Detection:** keep the coverage XML from every red run as an
> artifact so the missed line is readable without a repro.
>
> **Done when:** the missed line is identified and this issue is linked
> to or merged into its mechanism issue.
>
> **Decision:** None.
>
> **Related:** None.

## Common mistakes

- Filing an issue per sighting of a known mechanism. Same mechanism,
  one issue, N evidence bullets.
- Inventing a mechanism so the title sounds decisive. If you did not
  look, say Unknown.
- Incidents without identifiers. "CI was flaky last night" cannot be
  tied to anything; the sha, job, time, and host can.
- Filing what you could fix. Check branch 1 first; the queue is not a
  parking lot for ten-second fixes.
- Bodies that end at the symptom. Without Detection and Done-when the
  next person re-diagnoses from scratch.
- Leaving Decision implicit. That is how an issue reaches its third
  week with zero comments.
