#!/usr/bin/env bash
# UserPromptSubmit hook: inject the research-first reminder into the agent's
# context before it takes any action on the user's prompt. Fires once per
# user prompt - the strongest moment to influence first-action behaviour.
#
# Emitted on every owner-typed prompt; the agent self-polices the "already
# searched this session" skip, which keeps the hook stateless. Claude Code also
# fires UserPromptSubmit for harness-generated prompts, which carry no new
# owner intent, so those get an empty `{}` instead of the reminder. They are
# recognised by two fixed prefixes (after leading whitespace):
#   <task-notification>                       Monitor and background task events
#   Another Claude session sent a message:    teammate (subagent) messages
# A missing or empty .prompt, or non-JSON stdin, still gets the reminder.
set -euo pipefail

if ! prompt="$(jq -r '.prompt // empty' 2>/dev/null)"; then
    prompt=""
fi
prompt="${prompt#"${prompt%%[![:space:]]*}"}"

if [[ $prompt == '<task-notification>'* || $prompt == 'Another Claude session sent a message:'* ]]; then
    echo '{}'
    exit 0
fi

reminder="Before designing, planning, implementing custom code, refactoring or extracting code, choosing a tool/library/protocol, or debugging an unfamiliar error: RUN a WebSearch. This applies to questions/decisions you face, not user narration - if the user is stating what they are about to do (rather than asking how), absorb it as context rather than searching on it. (Or Read/Grep, if the question is purely about your own codebase - but most design questions have an external component.) Listing what you would search for does not count - execute the tool. Skipping because you think you already know is exactly the failure mode this rule guards against. Only valid skip: you have already run the same search in this session."

jq -n --arg msg "$reminder" '{
    hookSpecificOutput: {
        hookEventName: "UserPromptSubmit",
        additionalContext: $msg
    }
}'
