"""Detect-then-install the decompilers this skill drives.

Only the .NET global tools (ilspycmd, dotnet-il) install unattended; they are
user-scope and need no privilege. Everything else is detected and, when missing,
reported as ``manual`` with the exact next step. Standard library only.
"""

import os
import platform
import subprocess
from collections.abc import Callable
from typing import NamedTuple

from decompilers import discovery

Runner = Callable[[list[str]], tuple[int, str, str]]

_TARGETS_BY_SYSTEM = {
    "linux": ("ilspycmd", "dotnet-il", "analyzeHeadless", "java", "objdump"),
    "darwin": ("ilspycmd", "dotnet-il", "analyzeHeadless", "java", "llvm-objdump"),
    "windows": ("ilspycmd", "dotnet-il", "analyzeHeadless", "java", "dumpbin"),
}
_DOTNET_TOOLS = ("ilspycmd", "dotnet-il")
_JAVA_MINIMUM_MAJOR = 21
_MANUAL_POINTERS = {
    "analyzeHeadless": (
        "Ghidra not found: download the release zip from "
        "https://github.com/NationalSecurityAgency/ghidra/releases, unpack it, and set "
        "GHIDRA_INSTALL_DIR to the unpacked folder"
    ),
    "java": (
        "Java 21 or newer not found (Ghidra 11.4+ requires it): "
        "install a JDK 21+ and put java on PATH"
    ),
    "dumpbin": (
        "dumpbin not found: install the Visual Studio 'Desktop development with C++' workload; "
        "the script locates it through vswhere"
    ),
    "objdump": "objdump not found: install binutils from the distro package manager",
    "llvm-objdump": (
        "llvm-objdump not found: install the LLVM package (brew install llvm, or the LLVM "
        "installer on Windows)"
    ),
}


class Result(NamedTuple):
    kind: str
    status: str  # present | installed | failed | manual | dryrun
    detail: str


def platform_targets(system: str) -> tuple[str, ...]:
    return _TARGETS_BY_SYSTEM.get(system.lower(), ())


def _default_runner(command: list[str]) -> tuple[int, str, str]:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return completed.returncode, completed.stdout, completed.stderr


def _check_java(path: str, runner: Runner) -> Result:
    code, out, err = runner([path, "-version"])
    major = discovery.java_major_version(out + err)
    if code == 0 and major is not None and major >= _JAVA_MINIMUM_MAJOR:
        return Result("java", "present", f"{path} (major {major})")
    return Result("java", "manual", _MANUAL_POINTERS["java"])


def _install_dotnet_tool(kind: str, dotnet: str, runner: Runner, environ) -> Result:
    code, out, err = runner([dotnet, "tool", "install", "--global", kind])
    if code != 0:
        return Result(kind, "failed", (err or out).strip())
    tools_dir = discovery.dotnet_tools_dir(environ)
    return Result(
        kind,
        "installed",
        (
            f"{out.strip()} Ensure {tools_dir} is on PATH. "
            "On Linux set DOTNET_ROLL_FORWARD=Major if the tool reports a missing runtime."
        ),
    )


def run(
    only=None,
    dry_run=False,
    *,
    system=platform.system,
    find=discovery.find_tool,
    runner: Runner = _default_runner,
    environ=None,
) -> list[Result]:
    environ = os.environ if environ is None else environ
    current_system = system()
    kinds = [k for k in platform_targets(current_system) if only is None or k in only]
    results: list[Result] = []
    for kind in kinds:
        found = find(kind, environ=environ, system=lambda: current_system, runner=runner)
        if found and kind == "java":
            results.append(_check_java(found, runner))
            continue
        if found:
            results.append(Result(kind, "present", found))
            continue
        if kind in _DOTNET_TOOLS:
            dotnet = find("dotnet", environ=environ, system=lambda: current_system, runner=runner)
            if not dotnet:
                results.append(
                    Result(
                        kind,
                        "manual",
                        f"{kind} needs the .NET SDK: install the .NET SDK first, then rerun",
                    )
                )
            elif dry_run:
                results.append(
                    Result(kind, "dryrun", f"would run: {dotnet} tool install --global {kind}")
                )
            else:
                results.append(_install_dotnet_tool(kind, dotnet, runner, environ))
            continue
        results.append(Result(kind, "manual", _MANUAL_POINTERS[kind]))
    return results
