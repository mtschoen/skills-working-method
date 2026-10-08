"""Drive Ghidra's analyzeHeadless to export every function's decompiled C.

Pure command construction plus an injectable runner. On Windows the command is
written to a .bat and run through cmd, because launching analyzeHeadless.bat
through a quoted cmd /c string from PowerShell breaks on the redirect.
"""

import hashlib
import json
import platform
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

Digest = Callable[[Path], str]
Runner = Callable[[list[str]], tuple[int, str, str]]
POST_SCRIPT = "DecompileAllToFile.java"
_UTF_8 = "utf-8"


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


def sha256_of(path: Path) -> str:
    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _sidecar_path(project_dir: Path, project_name: str) -> Path:
    return project_dir / f"{project_name}.source.json"


def _receipt_path(output: Path) -> Path:
    return Path(str(output) + ".receipt")


def project_matches(project_dir: Path, project_name: str, binary: Path, *, digest: Digest) -> bool:
    """True when the stored project was imported from exactly this binary's bytes and basename."""
    sidecar = _sidecar_path(project_dir, project_name)
    if not project_exists(project_dir, project_name) or not sidecar.exists():
        return False
    try:
        stored = json.loads(sidecar.read_text(encoding=_UTF_8))
        current = digest(binary)
    except (OSError, ValueError):
        return False
    if not isinstance(stored, dict):
        return False
    stored_name = stored.get("name") or Path(stored.get("path", "")).name
    return stored.get("sha256") == current and stored_name == binary.name


def _sidecar_text(binary: Path, digest: Digest) -> str:
    record = {
        "name": binary.name,
        "path": str(binary.resolve()),
        "size": binary.stat().st_size,
        "sha256": digest(binary),
    }
    return json.dumps(record, indent=2)


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
    if "\r" in argument or "\n" in argument:
        raise ValueError(f"argument cannot contain newlines: {argument!r}")
    if '"' in argument:
        raise ValueError(f"argument cannot contain a double quote: {argument!r}")
    return '"' + argument.replace("%", "%%") + '"'


def windows_launcher(command: list[str], log_path: Path) -> str:
    log_string = str(log_path)
    if "\r" in log_string or "\n" in log_string:
        raise ValueError(f"log_path cannot contain newlines: {log_string!r}")
    if '"' in log_string:
        raise ValueError(f"log_path cannot contain a double quote: {log_string!r}")
    quoted = " ".join(_quote(part) for part in command)
    escaped_log = log_string.replace("%", "%%")
    return f'@echo off\ncall {quoted} > "{escaped_log}" 2>&1\nexit /b %ERRORLEVEL%\n'


def summarize_output(text: str) -> Summary:
    headers = [line for line in text.splitlines() if line.startswith("// ==== ")]
    unnamed = sum(1 for line in headers if line[8:].startswith("FUN_"))
    return Summary(functions=len(headers), unnamed=unnamed)


def _default_runner(command: list[str]) -> tuple[int, str, str]:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return completed.returncode, completed.stdout, completed.stderr


def _paths_alias(first_path: Path, second_path: Path) -> bool:
    try:
        if first_path.resolve() == second_path.resolve():
            return True
    except (OSError, RuntimeError):
        pass
    try:
        if first_path.exists() and second_path.exists() and first_path.samefile(second_path):
            return True
    except (OSError, RuntimeError):
        pass
    return False


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
    digest: Digest = sha256_of,
    write_text=lambda path, text: Path(path).write_text(text, encoding=_UTF_8),
    clock=time.monotonic,
) -> RunReport:
    receipt_file = _receipt_path(output)
    sidecar_file = _sidecar_path(project_dir, project_name)
    launcher_file = project_dir / f"run-{project_name}.bat"
    log_file = project_dir / f"run-{project_name}.log"

    mutated_paths = [
        ("output", output),
        ("receipt", receipt_file),
        ("sidecar", sidecar_file),
        ("launcher", launcher_file),
        ("log", log_file),
    ]
    for role, target_path in mutated_paths:
        if _paths_alias(binary, target_path):
            raise ValueError(f"{role} path cannot be the same file as binary path: {target_path}")

    project_dir.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    reuse = project_matches(project_dir, project_name, binary, digest=digest)
    output.unlink(missing_ok=True)
    receipt_file.unlink(missing_ok=True)
    if not reuse:
        # An import overwrites the project, so the old provenance is void until it succeeds.
        sidecar_file.unlink(missing_ok=True)
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
        write_text(launcher_file, windows_launcher(command, log_file))
        code, _, _ = runner(["cmd", "/c", str(launcher_file)])
    else:
        code, _, _ = runner(command)
    seconds = clock() - started
    receipt_completed = (
        receipt_file.exists()
        and "DecompileAllToFile: completed"
        in receipt_file.read_text(encoding=_UTF_8, errors="replace")
    )
    if code != 0 or not receipt_completed:
        effective_code = code if code != 0 else 1
        output.unlink(missing_ok=True)
        text = ""
        summary = Summary(0, 0)
    else:
        effective_code = 0
        write_text(sidecar_file, _sidecar_text(binary, digest))
        text = output.read_text(encoding=_UTF_8, errors="replace") if output.exists() else ""
        summary = summarize_output(text)
    return RunReport(command, effective_code, seconds, summary)
