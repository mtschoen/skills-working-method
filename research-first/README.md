# skills-research-first

"Search before you decide" - a skill plus a Claude Code-specific
`UserPromptSubmit` hook that nudges the agent to run a WebSearch (or
Read/Grep for codebase-only questions) before designing, choosing a tool,
writing custom code, refactoring, or debugging an unfamiliar error.

## What it is

- `SKILL.md` - the discipline the agent follows: which decisions trigger a
  search, what counts as a decision vs. user narration, and the one valid
  skip (already searched this session).
- `hooks/prompt-reminder.sh` - a `UserPromptSubmit` hook that injects the
  reminder as `additionalContext` on every owner-typed prompt (task
  notifications and teammate messages are skipped). Stateless by
  design; the agent self-polices the "already searched" skip.

## Install

`install-skills.{sh,bat}` (in the skills-dev umbrella) ships `SKILL.md`
plus the `hooks/` dir (declared in `.skillpack`) into
`~/.agents/skills/research-first/` (or wherever your agent harness reads
skills from).

The `hooks/prompt-reminder.sh` script is Claude Code-specific: it speaks
the `UserPromptSubmit` hook protocol, which is a Claude Code mechanism
with no equivalent in this repo for other harnesses. On Claude Code, the
hook is **not** auto-wired - like every skill hook, register it in the
agent's settings under `UserPromptSubmit` manually:

```json
{
  "type": "command",
  "command": "bash ~/.claude/skills/research-first/hooks/prompt-reminder.sh"
}
```

This replaces the older inline `echo '{...}'` UserPromptSubmit hook that
hard-coded the same reminder string in `settings.json`.

If this skill arrived as part of a skill pack, check whether the pack's
installer provides a hook offer flow - a command that checks
registration state and records the user's yes / no / later decision - and
route the suggestion through it instead of proposing
manual registration, so the user is asked at most once.
