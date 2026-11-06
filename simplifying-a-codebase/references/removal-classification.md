# Classifying a removal

Use this before approving, merging or auditing any pull request that deletes code, scripts,
docs, samples, options or tests. The question is never "did this break compatibility"; it is
"did we lose a capability someone would still want".

## The five classes

For every deleted or substantially removed unit (file, script, public or internal member that
implemented a capability, CLI option or command, sample program feature, doc section that
explained how to do something, test that covered behavior no other test covers, CI step):

- **DEAD**: its subject no longer exists (the feature it served is gone) and nothing references
  it.
- **SUPERSEDED**: a replacement exists. Name the replacement (`file:line`) and confirm it covers
  the same capability, not a narrower one.
- **INTERNAL-NOISE**: a seam, rendezvous, delegate field, duplicate helper or test hook whose
  removal loses no capability.
- **USEFUL-LOST**: a capability a developer, consumer or agent would still want, now gone or only
  partially replaced. Remedy: restore it AND demonstrate it (a sample command, a doc section, a CI
  exercise or a test) so it stops looking dead.
- **UNSURE**: you cannot decide; say what evidence would decide it.

Be skeptical in both directions. "Nothing calls it" is not evidence of DEAD for developer tooling,
diagnostics, public library API that consumers or samples might use, or documentation. But do not
inflate: most test-seam removals are INTERNAL-NOISE.

## What is fine to delete under a no-compatibility policy

An obsolete overload, a transitional flag, a duplicated code path, a test-only hook in production
code that has a replacement, a renamed member. A deletion that contradicts a recorded ruling in the
repository's decision log is a finding.

## "No caller" is a fact

Before an owner question about a zero-caller member, establish intent:

1. Is anything misdocumented? A documented feature that is unreachable is a bug, not dead code.
2. Does a decision log entry already cover it?
3. Do the consumers do the same thing by hand? Identical consumer code hoisted into the library
   on purpose looks uncalled from inside the library.
4. Inventory every instance of the same pattern across the surface and propose one rule for all
   of them.

A sample or test call counts as a caller, but in two different ways, decided by where the returned
value goes:

- **NATURAL**: control flow, a further computation or a persisted artifact consumes the value.
  Example: a sample that branches on `set.Children(root).Any()`, or one that writes the child
  count into the README table it generates.
- **GATE-ONLY**: the value's only destination is a console write or a variable nothing reads.
  Example: `Console.WriteLine(set.Children(root).Count)` in a sample that does nothing else with
  it.

The two are exclusive, and only the destination decides: how meaningful the printed text looks
does not make a console write NATURAL. Either class is a fact for the owner, not a verdict.

## Static analysis is a candidate list

An "unused member" from a whole-solution inspection is where to start grepping, not where to stop.
Cross-project false positives are routine: grep the entire solution including sibling projects,
read one caller, then decide. A recommendation to delete a shared test fake's method needs a
package-wide grep of production callers of the faked constructor.

## Auditing a batch of cleanup pull requests

One read-only lane per batch, same contract as an audit lane. For each pull request: list every
removed unit with its class; for USEFUL-LOST name the remedy; flag any behavior change hiding in a
"cleanup" (a guard that made a failed command exit nonzero is behavior, not noise). Audit before
merging, including pull requests the reviewer already graded highest.
