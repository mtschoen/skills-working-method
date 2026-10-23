---
name: research-first
description: "Use when facing a decision before design, planning, custom code, refactoring, tool or protocol selection, or debugging an unfamiliar error. Requires a web search, or Read/Grep for codebase-only questions, before acting; user narration does not trigger it."
---

# research-first - search before you decide

## When to use

Use before designing, planning, writing custom code, refactoring/extracting code, choosing a
tool/library/protocol, or debugging an unfamiliar error. Steers toward running a WebSearch (or
Read/Grep for codebase-only questions) BEFORE acting on a decision, instead of inferring from
training data. Fires on decisions the agent faces, not on user narration of what they are about to
do.

Your training data is stale and lossy. For most design and tooling
decisions there is a maintained library, an official doc, or a recent
issue thread that beats inventing or guessing. This skill makes "look it
up first" the default reflex at the exact moments it matters.

## The rule

Before any of these, run a search **first** - execute the tool, don't
just narrate what you'd look for:

- **Designing or planning** an approach to a non-trivial problem.
- **Implementing custom code** for something a library likely already does.
- **Refactoring or extracting** code into a new shape/abstraction.
- **Choosing a tool, library, protocol, or format.**
- **Debugging an unfamiliar error** (a message/stack you don't already
  recognize from this session).

Default to **WebSearch** - most design questions have an external
component (a better library exists, an API changed, a known footgun).
Use **Read/Grep instead** only when the question is *purely* about this
codebase (e.g. "where is X defined here", "what does our wrapper do").
Most questions are a mix; when in doubt, do the web search too.

## What counts, what doesn't

- **A decision you face** -> search. "What's the right way to rate-limit
  this?" / "Is there a maintained client for this API?" / "Why does this
  error happen?" all trigger a search.
- **User narration** -> absorb as context, don't search. If the user is
  *stating what they are about to do* ("I'm going to add a cache here")
  rather than *asking how*, take it as a given and move on.
- **Listing search terms does not count.** "I would search for X" is the
  failure mode this guards against. Run the tool.
- **Already searched this session?** That's the one valid skip - don't
  re-run the *same* query you already ran this session. But the skip is
  **per-question, not per-session**: when you shift to a new topic or a new
  sub-decision, earlier searches on the prior topic do **not** discharge the
  obligation. Example (real): a search on "WGC behavior for minimized
  windows" does not cover the later, distinct decision "which event API
  detects a stalled capture" - that's a fresh design choice and owes its own
  search. Treat a topic/sub-decision shift as re-arming the rule, even mid-
  session, even right after a related search.

## Why this is a default-on nudge

"I already know this" is exactly the rationalization that produces
stale, reinvented, or subtly-wrong work. The cost of one redundant search
is a few seconds; the cost of a skipped one is building the wrong thing
on outdated assumptions. So the reminder fires on **every** owner-typed prompt
(harness-generated task notifications and teammate messages are skipped; see `hooks/prompt-reminder.sh`) and you self-police the "already searched"
skip - the hook stays deliberately simple rather than trying to detect
prior searches.

## Relation to running-spikes

This skill is *look it up* - a search or doc read, seconds, stateless. When the question is about observable behavior of an external system and a small experiment would settle it definitively, the `running-spikes` skill (if installed) is the escalation: *run it and observe*. Searching usually remains the cheaper opening move; spike when reading doesn't settle it or running is cheap.

## Examples

**Triggers a search:**
> User: "Let's add retry-with-backoff to the HTTP client."
> Agent: [WebSearch for the language's maintained retry/backoff libraries
> and current best practice] -> then proposes using one instead of
> hand-rolling.

**Does not trigger (narration):**
> User: "I'm about to bump us to the new SDK version, just FYI."
> Agent: absorbs as context, no search.

**Codebase-only (Read/Grep, not web):**
> User: "Why does our `retry()` give up after 3 tries?"
> Agent: Grep/Read the local `retry()` implementation.
