---
name: running-spikes
description: "Use when extended reading or thinking could be replaced by a small experiment on observable behavior of an external system, library, framework, or runtime. Prefers running a scratch probe in any work phase, excluding this codebase, subjective design, and questions already spiked."
---

# Running Spikes

## When to use

Use when about to do extended Read/Grep/thinking on a question whose answer is observable behavior
of an external system, library, framework, or runtime - prefer learning from running code in a
scratch dir over inferring from docs. Suppressed when the question is about THIS codebase, is
subjective/design, or has already been spiked (check ~/.agents/memories/spike_*.md first). Fires
phase-agnostically - during brainstorming, plan-writing, AND mid-implementation.

## Why this skill exists

The agent's default is to read more, search more, think more - even when running code would resolve the question in five minutes. That habit costs sessions: long Read/Grep loops produce confidence-without-evidence, and architectural decisions get made on training-data hunches that fall over on first contact with the actual system.

**Failure mode this skill prevents:** spending 20 minutes "researching" what a 2-minute spike would conclusively answer, then making a decision on inferred behavior that turns out wrong.

**Failure mode this skill must NOT create:** the agent constantly spins up scratch projects to "be thorough," scattering artifacts, blowing the auth-prompt budget on package installs, avoiding the real codebase. The skill is tightly gated.

## The trigger moment

Fires when the agent catches itself reaching for one of these defaults:

- "Let me read more docs about how X behaves."
- "Let me grep across other projects for how this is usually done."
- "Let me think through whether Y will work."

...AND the question is about **observable behavior of an external system** (library, framework, runtime, host environment, third-party API) AND a small experiment could produce a definitive answer.

(Web-search is a natural fourth signal but is parked - the `research-first` skill's prompt-submit hook, if installed, already pushes the agent toward WebSearch on design / planning prompts; pairing the spike skill on that signal would over-fire. The three signals above carry the action-bias for now. Division of labor: research-first is *look it up*; this skill is *run it and observe*.)

## The four suppression gates

Before firing, silently answer. If any is "yes," don't spike - fall back to the original instinct.

1. **Is this about THIS codebase?** -> Read the code or write a test against it. Spike scope is for external/unknown systems.
2. **Is the answer subjective / a design opinion?** -> No experiment can resolve "which feels nicer." Reason it out.
3. **Have I (or have past sessions) already spiked this?** -> Check `~/.agents/memories/spike_registry.md` first, then glob `~/.agents/memories/spike_*.md`. If found, cite and skip.
4. **Did the user just say "just answer"?** -> Last-message override beats the skill.

Note: "authoritative docs exist" is deliberately NOT a suppression gate. Even when docs exist, prefer running code to reading. Reinforces the bias toward action.

## Tiering - small vs. medium+

The boundary is **"does it leave artifacts beyond a single scratch file?"**

**Small (announce-and-go):**

- Single-file scripts (`python -c`, `node -e`)
- REPL-style probes (`python -i`, `dotnet fsi`)
- `curl` against a known endpoint
- `<tool> --help` / version checks
- A single file in `.agents/spikes/<slug>/probe.py` (the dir itself is the only filesystem footprint)

Heads-up format - one line, then go:

> "Spiking on whether httpx follows redirects across schemes - single-file probe."

**Medium+ (ask first):**

- New project templates (`npm init`, `dotnet new`, `cargo new`, `uv init`)
- Package installs (`pip install`, `npm install`)
- Cloning third-party repos to inspect
- Anything creating `.venv/`, `node_modules/`, `target/`, etc.

Ask format:

> "I want to spike on X. Best path is `dotnet new console` in `.agents/spikes/x/` then add SomeThing. ~3 minutes, leaves a scratch dir. OK to proceed?"

## Scratch directory

**Location precedence:**

1. If cwd is a git repo -> `.agents/spikes/<slug>/` in repo root, gitignored. Skill adds `.agents/spikes/` to `.gitignore` if missing (one-line in-place change, bundled into the spike setup).
2. Otherwise -> `~/.agents/spikes/<slug>/`.

**Slug:** kebab-case, 2-4 words. `httpx-redirect-schemes`, `unity-batch-mode-exit-codes`. On collision (a slug already exists), append a date suffix (e.g., `-20260508`).

**Hygiene:** spike code is exempt from TDD, smoke-test, maintaining-full-coverage, and verification-before-completion (see "Exemptions" below). Happy path only. Sloppy is fine. The spike's only verification is "did the code run and produce the answer."

## Memory layer

### Per-topic note (always written)

`~/.agents/memories/spike_<slug>.md`:

```markdown
---
name: spike <topic>
description: <one-line answer>
type: spike
---

**Question:** <the concrete question this spike answered>

**Answer:** <one or two sentences, lead with the conclusion>

**Spiked:** YYYY-MM-DD on <machine>; scratch at `<path>` (may be deleted by now)

**Existence proofs:** <links to working code in this or other projects on this machine, e.g. `~/cant_stop_the_beat/server.py:42` - only fill in if you found one>

<free-form narrative: what you tried, what surprised you, gotchas, references to docs that turned out wrong>
```

The bar is low - it's a breadcrumb for future-you. Always written.

### Curated registry (sometimes)

`~/.agents/memories/spike_registry.md`:

```markdown
# Spike registry

Curated index of spikes whose answers are likely to recur. Per-topic notes live alongside as `spike_<slug>.md`; only the cross-context-useful ones get an entry here.

- 2026-05-07 - [httpx redirect schemes](spike_httpx-redirect-schemes.md) - httpx follows http->https but NOT https->http by default; needs custom transport
- 2026-05-03 - [unity batch-mode exit codes](spike_unity-batch-mode-exit-codes.md) - exit 1 on compile error, 2 on test failure, 3 on Editor crash; 0 only on full success
```

Newest at top. One line per registered spike: date - title (linked) - one-sentence TL;DR.

### The razor - register or not?

After the spike concludes, silently answer:

> "Would this spike's answer help me on a different project / different file / different task in the future?"

- **Yes** -> append a registry line. (Generally useful: library quirks, runtime behavior, host-environment facts, framework gotchas.)
- **No** -> leave as note-only. (Project-specific: how *this* particular service's auth flow works, what *this* schema looks like.)

Not gated on user approval. Cheap, append-only, easy to prune later.

## Pre-spike check

Before firing on a topic, in order:

1. Grep `~/.agents/memories/spike_registry.md` for keywords. Hit -> cite the line, follow the link to the per-topic note, skip the spike.
2. Glob `~/.agents/memories/spike_*.md`. Filename or content match -> read the note, skip.
3. Check earlier turns of this conversation for in-flight findings the user chose not to register.
4. No hit anywhere -> proceed.

## Promotion mechanic

When the spike yields keep-able code, present three options:

> "The hello-world is working and matches what your `<component>` needs. Three options:
>
> 1. **Promote** - move `.agents/spikes/<slug>/probe.py` into `<destination-path>` as the foundation. From there it re-engages TDD/smoke-test/coverage as normal production code.
> 2. **Keep iterating** - refine in scratch first.
> 3. **Leave as scratch** - I have what I need; the spike note is saved.
>
> Which?"

If promoted, the per-topic note gains a line: `**Promoted to:** <path>`.

Promotion crosses a hygiene boundary. Once code lands in the project tree, TDD / smoke-test / maintaining-full-coverage / verification-before-completion **re-engage**. Don't carry the "sloppy is fine" license into production code.

## Exemptions from adjacent skills (while in scratch)

Spike code is exempt from:

- `superpowers:test-driven-development` - no red-green-refactor; this isn't production.
- `smoke-test` - the spike *is* the smoke test for the question.
- `maintaining-full-coverage` - out of scope until promotion.
- `superpowers:verification-before-completion` - the spike's "completion" is "the answer," not "the code is shipped."

All re-engage on promotion.

## Examples

**Example A - small spike, announce-and-go (during design):**

> User: "I'm thinking about using `httpx` for the new client. Will it follow redirects across http->https and back?"
>
> Agent: "I could read docs but the cleanest way to know is to run it. Spiking on httpx redirect behavior - single-file probe at `.agents/spikes/httpx-redirect-schemes/probe.py`, ~30 seconds.
>
> [runs the probe, observes behavior]
>
> Result: with `follow_redirects=True`, httpx follows http->https but NOT https->http by default - security guardrail. To allow it, you build a custom transport. Note saved at `~/.agents/memories/spike_httpx-redirect-schemes.md` and registered (likely to recur). For your client: do you actually need https->http, or is the default safe?"

**Example B - medium+ spike, ask first (mid-implementation):**

> User: "Add a Cosmos DB persistence layer to the order service."
>
> Agent: "Before I wire this in - I want to confirm a few things about partition key constraints and the bulk-execution path before designing the data access layer. Quickest path is `dotnet new console` in `.agents/spikes/cosmos-bulk-partition/` and a 30-line probe against the local emulator. ~5 minutes, leaves a scratch dir. OK?"

**Example C - suppression: this codebase question (don't spike, read):**

> User: "Does our `sanitizeFilename` actually strip backslashes on Windows, or just forward slashes?"
>
> Agent: [grep + read `sanitizeFilename`, answer from the actual code - gate 1 fires, no spike]

**Example D - suppression: prior spike found (cite the registry):**

> User: "I'm wondering about httpx redirect behavior across schemes."
>
> Agent: "Already spiked this on 2026-05-07 - see `~/.agents/memories/spike_httpx-redirect-schemes.md`. TL;DR: `follow_redirects=True` follows http->https but not https->http by default; needs a custom transport for the latter. Working from that, do you want the default or the custom transport?"

**Example E - promotion offer:**

> Agent (after a spike that yielded a working `redirect_client.py`): "The hello-world is working and matches what your order service needs. Three options:
>
> 1. **Promote** - move `.agents/spikes/httpx-redirect-schemes/probe.py` into `src/clients/http_client.py` as the starting foundation. From there it re-engages TDD/smoke-test/coverage as normal production code.
> 2. **Keep iterating** - refine in scratch first.
> 3. **Leave as scratch** - I have what I need; the spike note is saved.
>
> Which?"

**Example F - no-spike override:**

> User: "Just answer from the docs - no scratch project right now."
>
> Agent: "Got it, no spike. From the httpx docs: ..." [answers in text - gate 4 fires]

## Pre-fire self-check

Before announcing a spike, silently answer:

- **Bucket:** is this an *observable behavior* question about an *external* system?
- **Gates:** did I check all four suppression gates? Specifically, did I grep `~/.agents/memories/spike_*.md` and `spike_registry.md`?
- **Tier:** small or medium+? Asking when I should ask, announcing-and-going when I should?
- **Frame:** can I state the spike's question in one concrete sentence? If not, scope is too vague - narrow it before starting.

If any check is "no," reset.

## Post-spike self-check

Before reporting back to the user:

- **Answered the question?** Did the spike actually produce evidence for the original question, or did I drift? If drifted, summarize what was learned but flag the original question is still open.
- **Wrote the note?** Per-topic file at `~/.agents/memories/spike_<slug>.md` with Question / Answer / Spiked / Existence-proofs.
- **Applied the razor?** If generally useful, appended a line to `spike_registry.md`.
- **Offered promotion if relevant?** If the spike code is keep-able and the user would plausibly want it in the project, offered the three-option gate.
- **Closed out scratch?** Either left it (default) or noted that it's deletable.

## Anti-patterns

- **Spiking on the user's codebase.** "Let me write a quick test to see how their `parseConfig` behaves" - that's READING with extra steps. Just read it.
- **Spiking to look thorough.** If reading the official docs answers it in one Fetch, do that. The skill's bias toward action is calibrated against a real read-loop, not against five-minute single-page lookups.
- **Skipping the prior-spike check.** Cross-session memory only works if every spike checks `~/.agents/memories/` first. Re-deriving an answer that's already on disk is wasted session.
- **Skipping the per-topic note.** Without the note, the next session re-spikes. The note is the value; the scratch code is incidental.
- **Carrying "sloppy is fine" into promoted code.** Once promotion happens, full discipline re-engages.
- **Manufacturing "general usefulness" to register every spike.** The registry's value is its curation. If everything is generally useful, nothing is.
- **Auto-promoting without the gate.** The user picks promotion, not the agent.
- **Spiking on a subjective question.** "Should we use axios or fetch" doesn't have an experiment-resolvable answer about the fundamental choice - though "does fetch handle X edge case" might. Frame tightly or don't spike.
