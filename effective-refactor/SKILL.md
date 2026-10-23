---
name: effective-refactor
description: "Use when changing code shape without changing behavior: renames, signature or data-shape changes, moves, extraction, removal, or repeated edits across call sites. Traverses the reference graph with semantic tools or compiler errors and recognizes when entanglement requires a migration plan."
---

# Effective Refactor

## When to use

Use when changing code shape without changing behavior - renaming or deleting symbols, changing
signatures, extracting methods or modules, moving code, or converting a data shape - especially when
the change must touch many call sites. Triggers: about to hand-edit the same change into several
files, a mass rename or API migration, "update all usages", removing a widely-used function or
config shape, a refactor that keeps breaking distant call sites, or deciding whether a change is too
entangled to be a refactor at all.

A refactor is a traversal of the code's reference graph, not a pile of text edits.
The graph is machine-readable - refactoring tools walk it, compilers and type
checkers enumerate it, test suites sample it - so never enumerate it by hand.
Reading every file to find call sites and editing them one by one works on a toy
codebase and silently stops working on a real one: it burns context, misses
dynamic or string-based references, and gives no signal when a site is missed.

Three strategies, in escalation order:

1. **Mechanical tool** - the operation is expressible as one tool invocation.
2. **Break and chase** - make the breaking change at the definition, let the
   error surface enumerate the work.
3. **Not a refactor** - the change is too entangled to break-and-fix in place;
   it becomes a migration plan.

## Scope probe (always, before choosing)

1. **Start from green.** Run the tests; record the baseline. Commit or stash so
   the working tree is clean - every strategy below depends on a known-good
   state to return to.
2. **Count, don't read.** `grep -rn '\bsymbol\b'` (or the language's reference
   finder) to count usages and files. Read the definition and two or three
   representative call sites only - the tool or error surface will find the
   rest. Reading the whole tree up front is the number-one scaling failure.
3. **Pick the strategy.** Purely mechanical (every site gets the same change)
   and a tool exists: Strategy 1. Selective or semantic (sites diverge, shape
   changes): Strategy 2. Suspected deep entanglement: run Strategy 2 as a
   read-only probe (below), then decide.

## Strategy 1: mechanical tools

If the whole operation is "rename this symbol", "extract this block", "move
this member", use a semantic tool - one invocation beats N hand edits, and the
tool sees scopes, shadowing, and imports that regex cannot. Never regex-replace
what a semantic tool can rename: substring collisions (`proc` inside
`batch_proc`), same-named locals, and occurrences in strings or comments all
corrupt silently.

Per-language tool table and invocation shapes: [references/mechanical-tools.md](references/mechanical-tools.md).

Verify a mechanical pass like any other change: review `git diff` (the tool's
idea of the operation may not be yours), run the tests, then commit that one
operation on its own.

If no tool covers the language or operation, fall through to Strategy 2 - it
needs no tooling beyond the compiler or type checker.

## Strategy 2: break and chase

For selective or semantic changes - a signature change, a data-shape
conversion, retiring a function, renaming only some usages - deliberately break
the definition first and let the language's error surface hand you the
complete, addressed to-do list.

1. **Break the core.** Delete or rename the most deeply-linked symbol, change
   the signature, remove the field. Break the definition, not the call sites.
2. **Run the error surface** (table in
   [references/break-and-chase.md](references/break-and-chase.md)): the
   compiler in C#/C++/Go/Rust/Java, `pyright`/`mypy --strict` in Python,
   `tsc --noEmit` in TypeScript, the test suite as the surface of last resort.
   Every error is one work item with a file and line attached.
3. **Fix sites off the list, re-run, repeat** until green. Do not also grep
   ahead - trust the list, it re-derives itself on every run.
4. **Divergent call sites** (some usages keep old behavior, some get new): give
   each behavior its own well-named symbol, delete the old one so every site
   goes red, then route each red site deliberately to one of the new symbols.
   The old name must not survive with mutated meaning.
5. **Final sweep for what the checker cannot see:** grep the old name expecting
   zero hits - strings, comments, docs, reflection, config, serialized keys.
6. **Checkpoint every green.** One refactor per commit. Never start the next
   refactor on top of a red tree.

**Precondition: a fast feedback loop.** Break-and-chase iterates
break-check-fix many times; it falls apart when each check costs minutes.
Narrow the loop first (package-local build, targeted test file) or use
Strategy 1.

**Escalation - Mikado.** If the first break produces an error wave too large to
work through, or fixing one site turns out to require a second refactor first:
record what the errors told you as a prerequisite graph, **revert to green**,
and do the leaf prerequisites first, each as its own small break-and-chase.
The revert is not wasted work - the error list was the deliverable. Details in
[references/break-and-chase.md](references/break-and-chase.md).

## Strategy 3: recognizing that it is not a refactor

Signals that break-and-fix-in-place is the wrong frame:

- The Mikado graph keeps growing - prerequisites have prerequisites.
- Behavior must change along the way, or consumers need different things from
  the replacement than from the original.
- The tree would stay red across sessions, or the change cannot ship as one
  reviewable unit.

Then stop refactoring and plan a migration: build the replacement alongside the
old code, route consumers over one by one (each hop is a small Strategy 1 or 2
change), and delete the old path last, when nothing references it. This is the
strangler-fig shape; sprout a new function or class next to the old one rather
than untangling the old one first.

The cheapest way to find out which frame you are in: **run the probe**. On a
scratch branch, delete the thing you want gone, run the error surface, harvest
the error list into the plan, and revert. Ten minutes of deliberate breakage
answers "what would this take?" more accurately than an afternoon of reading.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| Reading the whole tree to find call sites | Count with grep, then let the tool or error surface enumerate |
| Regex-replacing a rename | Semantic tool (Strategy 1); regex hits substrings, strings, shadowed names |
| Batching several refactors, testing once at the end | One refactor per green checkpoint; a red tree with 14 edits cannot be attributed |
| Fixing call sites before breaking the definition | Break the definition first; otherwise there is no list and no done-signal |
| Keeping the old symbol but changing its meaning | New names for new behavior; delete the old name so the checker routes every site |
| Trusting the checker for the last mile | Grep the old name at the end: strings, comments, config are invisible to it |
| Pushing through an ever-growing error wave | Mikado: record prerequisites, revert to green, do leaves first |
| Calling a rebuild a refactor | If behavior changes or consumers diverge, plan a strangler migration instead |

## Quick reference

| Situation | Move |
| --- | --- |
| Same change at every site, tool exists | One tool invocation, diff review, tests, commit |
| Signature or shape change | Break definition, chase the error surface to green |
| Only some usages change | New symbols for each behavior, delete old, route red sites |
| Wave too big or nested prerequisites | Mikado graph, revert, leaves first |
| "What would break if we removed X?" | Scratch-branch probe: break, harvest errors, revert |
| Behavior changes or consumers diverge | Not a refactor - strangler migration plan |
