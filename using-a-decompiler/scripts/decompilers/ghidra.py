"""Drive Ghidra's analyzeHeadless to export every function's decompiled C.

Pure command construction plus an injectable runner. On Windows the command is
written to a .bat and run through cmd, because launching analyzeHeadless.bat
through a quoted cmd /c string from PowerShell breaks on the redirect.
"""

import platform
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

Runner = Callable[[list[str]], tuple[int, str, str]]
POST_SCRIPT = "DecompileAllToFile.java"


class Summary(NamedTuple):
    functions: int
    unnamed: int


class RunReport(NamedTuple):
    command: list[str]
    exit_code: int
    seconds: float
    summary: Summary


def project_exists(project_dir: Path, project_name: str) -> bool:
    return (project_dir / f"{project_name}.gpr").exists()


def build_command(
    analyze_headless: str,
    project_dir: Path,
    project_name: str,
    binary: Path,
    output: Path,
    script_dir: Path,
    *,
    reuse: bool,
    name_filter: str | None,
    timeout_seconds: int,
) -> list[str]:
    command = [analyze_headless, str(project_dir), project_name]
    if reuse:
        command += ["-process", binary.name, "-noanalysis"]
    else:
        command += ["-import", str(binary), "-overwrite"]
    # "-" is the no-filter sentinel: an empty argument would vanish in the Windows .bat launcher
    # and shift the timeout into the filter slot.
    command += [
        "-scriptPath",
        str(script_dir),
        "-postScript",
        POST_SCRIPT,
        str(output),
        name_filter or "-",
        str(timeout_seconds),
    ]
    return command


def _quote(argument: str) -> str:
    needs_quotes = " " in argument or chr(92) in argument or "/" in argument
    return f'"{argument}"' if needs_quotes and not argument.startswith("-") else argument


def windows_launcher(command: list[str], log_path: Path) -> str:
    quoted = " ".join(_quote(part) for part in command)
    return f'@echo off\ncall {quoted} > "{log_path}" 2>&1\nexit /b %ERRORLEVEL%\n'


def summarize_output(text: str) -> Summary:
    headers = [line for line in text.splitlines() if line.startswith("// ==== ")]
    unnamed = sum(1 for line in headers if line[8:].startswith("FUN_"))
    return Summary(functions=len(headers), unnamed=unnamed)


def _default_runner(command: list[str]) -> tuple[int, str, str]:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return completed.returncode, completed.stdout, completed.stderr


def run_decompile(
    binary: Path,
    output: Path,
    *,
    project_dir: Path,
    project_name: str,
    analyze_headless: str,
    script_dir: Path,
    name_filter: str | None = None,
    timeout_seconds: int = 60,
    system=platform.system,
    runner: Runner = _default_runner,
    write_text=lambda path, text: Path(path).write_text(text, encoding="utf-8"),
    clock=time.monotonic,
) -> RunReport:
    project_dir.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    reuse = project_exists(project_dir, project_name)
    command = build_command(
        analyze_headless,
        project_dir,
        project_name,
        binary,
        output,
        script_dir,
        reuse=reuse,
        name_filter=name_filter,
        timeout_seconds=timeout_seconds,
    )
    started = clock()
    if system().lower() == "windows":
        launcher = project_dir / f"run-{project_name}.bat"
        write_text(launcher, windows_launcher(command, project_dir / f"run-{project_name}.log"))
        code, _, _ = runner(["cmd", "/c", str(launcher)])
    else:
        code, _, _ = runner(command)
    seconds = clock() - started
    text = output.read_text(encoding="utf-8", errors="replace") if output.exists() else ""
    return RunReport(command, code, seconds, summarize_output(text))
