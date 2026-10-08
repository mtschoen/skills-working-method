import grade
import pytest
import run


@pytest.mark.parametrize(
    "build_command",
    [
        pytest.param(run.agent_command, id="agent"),
        pytest.param(grade.grader_command, id="grader"),
    ],
)
def test_launch_command_excludes_inherited_mcp_tools(build_command):
    command = build_command(None)
    assert "--strict-mcp-config" in command
    assert "--mcp-config" not in command
    assert command[command.index("--disallowedTools") + 1] == "mcp__*"
    assert command[command.index("--tools") + 1] == "Read,Grep,Glob"


@pytest.mark.parametrize(
    "build_command",
    [
        pytest.param(run.agent_command, id="agent"),
        pytest.param(grade.grader_command, id="grader"),
    ],
)
def test_launch_command_appends_requested_model(build_command):
    assert "--model" not in build_command(None)
    assert build_command("sonnet")[-2:] == ["--model", "sonnet"]
