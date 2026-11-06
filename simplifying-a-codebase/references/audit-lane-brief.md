# Audit lane briefs

Each audit lane receives one shared preamble plus one scoped area brief. Lanes are read-only and
run on the cheapest tier that reads code well (Sonnet-tier subagents, external harnesses such as
codex or opencode); the orchestrator seat keeps synthesis and judgment. Ten to twelve lanes cover
a 120k-line repository in about twenty minutes.

## Shared preamble (template)

```markdown
# <Project> <release> simplification audit (read-only review lane)

You are one of several independent reviewers auditing <project> before <release or milestone>.
Repository (absolute path, READ ONLY): <path>
Do NOT modify, create or delete anything under that repository. Do not run git commands that
change state. Do not run builds or tests. You may run `git log`, `git grep`, `git blame`, `rg`,
`grep`, `find`, `wc` and read files.
If any file this brief names is missing, STOP and write a report whose first line is
`BLOCKED: <path>`.

## The owner's question
<One paragraph in the owner's words: what they saw, what pivots the code went through, what
earlier passes already landed (cite the git log range), and the lens for this wave.>

The question you must answer for YOUR area: <the lens, in one sentence>. Hunt specifically for:
- residue of earlier designs: concepts, names, seams, fields or flags that only make sense under
  the old design,
- over-abstraction: interfaces with one implementation, types that carry one value, indirection
  with one caller, factories that build one thing,
- duplicated or near-duplicated logic and helpers,
- state spread across several classes that a from-scratch design keeps together, or one class
  that owns several unrelated concerns,
- two names for one concept, or one name for two concepts, and naming that misleads,
- dead code, unreachable branches, test-only knobs in production code,
- consumer-specific features inside a library (product decisions belong in the consumers),
- public or internal members with no caller, two members for one job, parameters with one value
  at every call site, options that no caller sets, asymmetries between sibling members,
- quirks a new developer would trip over: surprising ordering requirements, implicit coupling,
  magic constants without a home,
- leaky layering between namespaces or components.
"Yes, this is what from-scratch would look like" is a perfectly valid verdict for any part of
your area. Do not manufacture findings. A bug is worth a line if you happen to see one, but
design debt and cruft are the target, not bugs.

## Evidence discipline
Every finding must cite `path:line` and, where the claim is about usage counts (single
implementation, single caller, unused member), the exact grep command and its count. Verify
before asserting; if you cannot verify, label the claim `unverified`.

Public-surface scope input: <link to the owner's ruling and its covered surface, or "none">.
Only exclude a surface from this wave when the cited ruling explicitly puts it out of scope;
otherwise audit its shape under the owner's question. Prior review alone is not an exclusion.

## Zero-caller public members
Caller-gate input: <actual test path and covered members, or "none">. Read the named test before
claiming gate coverage, and limit that claim to the members it actually checks. Without a verified
gate, audit callers directly; do not assume caller coverage or owner approval. In either case,
report zero-caller facts with the member's apparent purpose for an owner decision, not as proof
of dead code. For each member used only by samples or tests, read the
sample call and classify it by where the returned value goes: NATURAL when control flow, a further
computation or a persisted artifact consumes it (`if (set.Children(root).Any()) ...`, or a sample
that writes the count into the README table it generates); GATE-ONLY when its only destination is
a console write or a variable nothing reads (`Console.WriteLine(set.Children(root).Count)`). The
two are exclusive, and how meaningful the printed text looks is irrelevant: only whether anything
downstream reads the value decides. A member with no caller is a fact to report with its apparent
purpose, never by itself a removal recommendation; the owner rules, and past "remove it"
recommendations were overturned once intent was known (deliberately hoisted identical consumer
code; a product feature the consumers had not wired up yet).

## Report
Write your report (Markdown) to the absolute path given in your lane brief. Structure:
1. `## Verdict`: three sentences, how close to from-scratch this area is and the one thing you
   would change.
2. `## Findings`: at most 12, ranked by value. Each: `### N. <title>`; `Kind:` one of
   design-debt / pivot-residue / over-abstraction / duplication / naming / dead-code /
   consumer-feature / quirk; `Evidence:` path:line plus grep counts; `From scratch:` what the
   design would be instead; `Change size:` files touched and a rough line count; `Risk:` what
   could break.
3. `## Checked and fine`: the things you examined and judged sound, one line each, so the
   orchestrator knows your coverage.
4. `## Open questions`: anything you could not settle.
Keep the report under about 300 lines. Prefer fewer well-verified findings over many weak ones.
An empty Findings section with a thorough Checked-and-fine section is a good report.

## Earlier audits (for dedupe)
<Where the previous waves' reports or issues live; skim them so you do not refile a fixed item.>
```

## Area briefs worth reusing

**Pivot archaeology.** From `git log --format='%h %ad %s' --date=short` over the relevant history,
build the list of retired concepts, names and designs. Grep the entire tracked tree (code,
comments, XML docs, docs, scripts, workflows, tests) for each retired name and for wording that
only makes sense under the old design: "legacy", "compat", "obsolete", "for now", "temporary",
"workaround", "TODO", "FIXME", "HACK", "no longer", "previously", "used to", "formerly". Use
`git grep -n -i` so untracked build output is excluded. Classify every hit as stale comment, stale
doc, stale test name, live code still shaped by the old design, or acceptable. Then structural
residue: a member or parameter whose only remaining purpose is the old design (a flag with the same
value at every call site: grep the call sites and show the values). Finally count suppressions
(`#pragma warning disable`, `[ExcludeFromCodeCoverage]`, `[SuppressMessage]`, analyzer disable
comments) in production code and say what each hides.

**Tests.** Bucket test lines by the production area each file exercises and report lines per
bucket beside the production line count; which buckets are disproportionate? Find helpers
reimplemented in more than one test file (same shape, different name) and count them. Find tests
of retired behavior, and tests that assert the same thing twice through different public paths.
List production seams that exist only for tests and which could be removed by testing through the
public or test-extension surface instead. Give the ten biggest opportunities to reduce test lines
without reducing what the suite verifies, each with an estimated line reduction.

## Adversarial verifier brief

```markdown
<N> independent audit lanes reviewed the tree. Your job is to try to REFUTE each claim below by
reading the cited code yourself. For each, give a verdict of CONFIRMED, REFUTED or PARTLY (with
what is wrong), and your OWN evidence (path:line you read, grep command and count you ran). Do
not echo the auditor's citation as evidence; if your evidence is the same lines, say what you saw
there in your own words. A verdict table with uniform wording is worthless; one refutation with
evidence is worth more than ten confirmations.
For CONFIRMED add a one-line severity call: release-blocking (wrong behavior or consumer leak in
shipped code), should-fix (cleanup before release is cheap and safe), or defer.
```

## Synthesis in the orchestrator seat

- Group findings by mechanism across lanes; items reported independently by two or more lanes
  rank first.
- Re-grep every count before it enters an issue or a ruling; quote numbers from the tree, not from
  a report.
- Report the line composition when a total alarms the owner (library code, XML docs, blank,
  tests, scripts and CI, native, docs); it usually dissolves the alarm into specific buckets.
- Delete the lane briefs and reports from the repository when the wave is done; they are session
  scratch, not project files.
