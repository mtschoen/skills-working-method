"""Tests for research-first/hooks/prompt-reminder.sh.

The hook is run with bash, fed a UserPromptSubmit JSON payload on stdin.
Harness-generated prompts (task notifications, teammate messages) must get
an empty object; everything else must get the reminder.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

_HOOK_PATH = (
    Path(__file__).resolve().parent.parent
    / "research-first"
    / "hooks"
    / "prompt-reminder.sh"
)

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("jq") is None,
    reason="bash and jq are required to run the hook",
)


def _run_hook(stdin_text: str) -> dict:
    completed = subprocess.run(
        ["bash", str(_HOOK_PATH)],
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(completed.stdout)


def _run_with_prompt(prompt: str) -> dict:
    return _run_hook(json.dumps({"session_id": "abc", "prompt": prompt}))


def _assert_reminder(output: dict) -> None:
    assert "RUN a WebSearch" in output["hookSpecificOutput"]["additionalContext"]


@pytest.mark.parametrize(
    "prompt",
    [
        pytest.param("why is the build red", id="owner-prompt"),
        pytest.param(
            "please explain <task-notification> handling",
            id="mid-prompt-notification-text",
        ),
    ],
)
def test_owner_prompt_gets_reminder(prompt: str):
    _assert_reminder(_run_with_prompt(prompt))


@pytest.mark.parametrize(
    "prompt",
    [
        pytest.param(
            "<task-notification> <task-id>x</task-id> <summary>Monitor event: PR merged</summary>",
            id="task-notification",
        ),
        pytest.param(
            'Another Claude session sent a message: <teammate-message teammate_id="lane">done</teammate-message>',
            id="teammate-message",
        ),
        pytest.param(
            "  \n\t<task-notification> <task-id>x</task-id>",
            id="leading-whitespace",
        ),
    ],
)
def test_task_notification_is_skipped(prompt: str):
    output = _run_with_prompt(prompt)
    assert output == {}


@pytest.mark.parametrize(
    "stdin_text",
    [
        pytest.param(json.dumps({"session_id": "abc"}), id="missing-prompt-key"),
        pytest.param("this is not json", id="non-json"),
        pytest.param("", id="empty-stdin"),
        pytest.param(
            '{"prompt":"<task-notification>"} not-json',
            id="issue-84-partial-jq-task-notification",
        ),
        pytest.param(
            '{"prompt":"Another Claude session sent a message: done"} not-json',
            id="issue-84-partial-jq-teammate-message",
        ),
    ],
)
def test_non_json_stdin_gets_reminder(stdin_text: str):
    _assert_reminder(_run_hook(stdin_text))
