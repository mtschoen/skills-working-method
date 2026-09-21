# Working method

Eight skills that change how an agent arrives at an answer, not what it does with
one.

The failure these address is upstream of any particular bug. An agent asked to
build something will, by default, start building it from what it already
believes: inferring an API from training data rather than reading the docs,
reasoning about a runtime's behaviour rather than observing it, agreeing with a
premise rather than testing it. The output looks confident and is often subtly
wrong, and the error is expensive precisely because it was introduced before
any code existed to review.

These skills intervene during the work rather than after it. Each replaces a
default reflex with a cheaper, more reliable one.

| Skill | The reflex it replaces |
| --- | --- |
| [`research-first`](research-first/) | Inferring an API or tool's behaviour from memory instead of checking |
| [`running-spikes`](running-spikes/) | Reasoning about what a system does instead of running it |
| [`pushback`](pushback/) | Accepting a premise because the user stated it |
| [`effective-refactor`](effective-refactor/) | Hand-editing the same change into many files |
| [`writing-tests`](writing-tests/) | Widening a tolerance or a timeout instead of removing what the test cannot control |
| [`fast-tests`](fast-tests/) | Tolerating a slow test loop, or faking the verify to speed it up |
| [`using-a-debugger`](using-a-debugger/) | Reading code to guess a runtime value |
| [`filing-issues`](filing-issues/) | Filing an issue per sighting, or filing what you could fix |

The common shape: **observe rather than infer**. A spike beats doc-divination,
a debugger beats reading, a search beats recall, and a real integration test
beats a mock that asserts the thing you wanted to be true.

`pushback` is the odd one out and the most important. The others correct the
agent against the world; `pushback` corrects the user against the codebase, in
the cases where the agent has context the user does not have in the moment.
Most invocations end in "no pushback needed", which is the point.

## Design notes

**Fires on decisions, not narration.** These trigger when the agent faces a
choice, not when the user describes one. An agent that lists what it would
search for has not searched.

**Cheap first.** Every one of these is chosen to cost less than the mistake it
prevents. A thirty-second spike is cheaper than a plausible wrong answer that
survives to review.

**Portable.** These name actions, not tools, so they work on a machine that has
none of the author's own tooling installed.

## Installing

These skills are distributed through the
[skills-dev](https://github.com/mtschoen/skills-dev) umbrella, which carries
the installer and can mirror them into Claude Code, Codex, opencode,
Antigravity, and Hermes. Each skill directory here is self-contained: `SKILL.md`
at its root plus optional `references/`, `scripts/`, and `assets/`.

## Related families

- [skills-completion-discipline](https://github.com/mtschoen/skills-completion-discipline) -
  the gates that decide when an agent may say "done".
- [skills-orchestration](https://github.com/mtschoen/skills-orchestration) -
  what changes when work outgrows one agent, one machine, or one budget.
