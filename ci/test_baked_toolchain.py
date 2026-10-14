"""Tests for ci/baked-toolchain.sh."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_BASH_EXECUTABLE = shutil.which("bash") or "/bin/bash"
_SCRIPT_PATH = Path(__file__).resolve().parent / "baked-toolchain.sh"


def _run_baked_toolchain(
    arguments: list[str],
    *,
    output_file: Path,
    path_file: Path,
    image_environment_path: Path | None = None,
    extra_environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "GITHUB_OUTPUT": str(output_file),
        "GITHUB_PATH": str(path_file),
        "FLEET_IMAGE_ENV": (
            str(image_environment_path)
            if image_environment_path is not None
            else "/nonexistent"
        ),
    }
    if extra_environment:
        environment.update(extra_environment)
    return subprocess.run(
        [_BASH_EXECUTABLE, str(_SCRIPT_PATH), *arguments],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_no_arguments_exits_with_usage(tmp_path: Path) -> None:
    output_file = tmp_path / "output"
    path_file = tmp_path / "path"
    output_file.touch()
    path_file.touch()

    process_result = _run_baked_toolchain(
        [], output_file=output_file, path_file=path_file
    )

    assert process_result.returncode == 2
    assert "usage:" in process_result.stderr


def test_unknown_toolchain_exits_with_error(tmp_path: Path) -> None:
    output_file = tmp_path / "output"
    path_file = tmp_path / "path"
    output_file.touch()
    path_file.touch()

    process_result = _run_baked_toolchain(
        ["unsupported-tool"], output_file=output_file, path_file=path_file
    )

    assert process_result.returncode == 2
    assert "unknown toolchain: unsupported-tool" in process_result.stderr


@pytest.mark.parametrize(
    "tool_name",
    [
        "python",
        "node",
        "shellcheck",
    ],
)
def test_missing_image_environment_reports_false(
    tmp_path: Path, tool_name: str
) -> None:
    output_file = tmp_path / "output"
    path_file = tmp_path / "path"
    output_file.touch()
    path_file.touch()

    process_result = _run_baked_toolchain(
        [tool_name],
        output_file=output_file,
        path_file=path_file,
        image_environment_path=tmp_path / "nonexistent-image.env",
    )

    assert process_result.returncode == 0
    assert f"{tool_name}=false" in output_file.read_text(encoding="utf-8")
    assert path_file.read_text(encoding="utf-8") == ""


@pytest.fixture
def controlled_shellcheck_directory(tmp_path: Path) -> Path:
    bin_directory = tmp_path / "controlled-shellcheck-bin"
    bin_directory.mkdir(parents=True, exist_ok=True)
    shellcheck_executable = bin_directory / "shellcheck"
    shellcheck_executable.write_text(
        "#!/bin/sh\nprintf 'version: 0.10.0\\n'\n",
        encoding="utf-8",
    )
    shellcheck_executable.chmod(0o755)
    return bin_directory


@pytest.mark.parametrize(
    ("configured_major", "expected_state"),
    [
        pytest.param("0", "true", id="matching_major"),
        pytest.param("999", "false", id="mismatching_major"),
    ],
)
def test_shellcheck_configured_major_detection(
    tmp_path: Path,
    controlled_shellcheck_directory: Path,
    configured_major: str,
    expected_state: str,
) -> None:
    output_file = tmp_path / "output"
    path_file = tmp_path / "path"
    image_environment_file = tmp_path / "image.env"
    output_file.touch()
    path_file.touch()
    image_environment_file.write_text(
        f"SHELLCHECK_MAJOR={configured_major}\n",
        encoding="utf-8",
    )

    process_result = _run_baked_toolchain(
        ["shellcheck"],
        output_file=output_file,
        path_file=path_file,
        image_environment_path=image_environment_file,
        extra_environment={"PATH": str(controlled_shellcheck_directory)},
    )

    assert process_result.returncode == 0
    assert output_file.read_text(encoding="utf-8") == f"shellcheck={expected_state}\n"
    assert path_file.read_text(encoding="utf-8") == ""


def test_shellcheck_missing_binary_reports_false(tmp_path: Path) -> None:
    output_file = tmp_path / "output"
    path_file = tmp_path / "path"
    image_environment_file = tmp_path / "image.env"
    output_file.touch()
    path_file.touch()
    image_environment_file.write_text("SHELLCHECK_MAJOR=0\n", encoding="utf-8")

    empty_bin_directory = tmp_path / "empty-bin"
    empty_bin_directory.mkdir()

    process_result = _run_baked_toolchain(
        ["shellcheck"],
        output_file=output_file,
        path_file=path_file,
        image_environment_path=image_environment_file,
        extra_environment={"PATH": str(empty_bin_directory)},
    )

    assert process_result.returncode == 0
    assert output_file.read_text(encoding="utf-8") == "shellcheck=false\n"


def test_multiple_tools_in_single_invocation(
    tmp_path: Path,
    controlled_shellcheck_directory: Path,
) -> None:
    output_file = tmp_path / "output"
    path_file = tmp_path / "path"
    image_environment_file = tmp_path / "image.env"
    output_file.touch()
    path_file.touch()
    image_environment_file.write_text(
        "FLEET_PYTHON_VERSION=99.99\nSHELLCHECK_MAJOR=0\n",
        encoding="utf-8",
    )

    process_result = _run_baked_toolchain(
        ["python", "shellcheck"],
        output_file=output_file,
        path_file=path_file,
        image_environment_path=image_environment_file,
        extra_environment={"PATH": str(controlled_shellcheck_directory)},
    )

    assert process_result.returncode == 0
    assert output_file.read_text(encoding="utf-8") == "python=false\nshellcheck=true\n"
    assert process_result.stdout == "baked python: false\nbaked shellcheck: true\n"


def test_python_virtual_environment_creation(tmp_path: Path) -> None:
    output_file = tmp_path / "output"
    path_file = tmp_path / "path"
    image_environment_file = tmp_path / "image.env"
    output_file.touch()
    path_file.touch()

    fleet_root_directory = tmp_path / "fleet"
    python_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    python_bin_directory = fleet_root_directory / f"python-{python_version}" / "bin"
    python_bin_directory.mkdir(parents=True)
    (python_bin_directory / "python").symlink_to(sys.executable)

    runner_temporary_directory = tmp_path / "runner-temp"
    runner_temporary_directory.mkdir()

    image_environment_file.write_text(
        f"FLEET_PYTHON_VERSION={python_version}\nFLEET_ROOT={fleet_root_directory}\n",
        encoding="utf-8",
    )

    process_result = _run_baked_toolchain(
        ["python"],
        output_file=output_file,
        path_file=path_file,
        image_environment_path=image_environment_file,
        extra_environment={"RUNNER_TEMP": str(runner_temporary_directory)},
    )

    assert process_result.returncode == 0
    assert output_file.read_text(encoding="utf-8") == "python=true\n"
    expected_virtual_environment_bin_directory = (
        runner_temporary_directory / "baked-python" / "bin"
    )
    assert (
        path_file.read_text(encoding="utf-8")
        == f"{expected_virtual_environment_bin_directory}\n"
    )
    assert (expected_virtual_environment_bin_directory / "python").exists()
