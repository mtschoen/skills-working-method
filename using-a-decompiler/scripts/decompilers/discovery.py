"""Locate the decompilers and disassemblers this skill drives.

Pure lookups with injectable collaborators so tests never touch PATH, the
environment, or the filesystem. Standard library only.
"""

import os
import platform
import re
import shutil
from collections.abc import Callable
from pathlib import Path

SUPPORTED_KINDS = (
    "ilspycmd",
    "dotnet",
    "dotnet-il",
    "analyzeHeadless",
    "java",
    "dumpbin",
    "objdump",
    "llvm-objdump",
    "cpp2il",
)

Runner = Callable[[list[str]], tuple[int, str, str]]

_VSWHERE_RELATIVE = Path("Microsoft Visual Studio") / "Installer" / "vswhere.exe"
_DUMPBIN_PATTERN = "VC/Tools/MSVC/*/bin/Hostx64/x64/dumpbin.exe"
_JAVA_VERSION = re.compile(r'version "(\d+)(?:\.(\d+))?')


def dotnet_tools_dir(environ) -> Path:
    base = (
        environ.get("DOTNET_CLI_HOME") or environ.get("HOME") or environ.get("USERPROFILE") or "~"
    )
    return Path(base).expanduser() / ".dotnet" / "tools"


def java_major_version(version_output: str) -> int | None:
    match = _JAVA_VERSION.search(version_output)
    if not match:
        return None
    major = int(match.group(1))
    if major == 1 and match.group(2):
        return int(match.group(2))
    return major


def ghidra_search_roots(environ, home: Path, system: str) -> list[Path]:
    roots: list[Path] = []
    configured = environ.get("GHIDRA_INSTALL_DIR")
    if configured:
        roots.append(Path(configured))
    roots.extend(sorted(home.glob("ghidra_*_PUBLIC"), reverse=True))
    if system.lower() != "windows":
        roots.extend(sorted(Path("/opt").glob("ghidra*"), reverse=True))
    return roots


def _analyze_headless_name(system: str) -> str:
    return "analyzeHeadless.bat" if system.lower() == "windows" else "analyzeHeadless"


def _find_analyze_headless(environ, system: str) -> str | None:
    home = Path(environ.get("HOME") or environ.get("USERPROFILE") or "~").expanduser()
    for root in ghidra_search_roots(environ, home, system):
        candidate = root / "support" / _analyze_headless_name(system)
        if candidate.exists():
            return str(candidate)
    return None


def _find_dumpbin(environ, runner: Runner | None) -> str | None:
    program_files = environ.get("ProgramFiles(x86)")
    if not program_files or runner is None:
        return None
    vswhere = Path(program_files) / _VSWHERE_RELATIVE
    code, out, _ = runner([str(vswhere), "-all", "-products", "*", "-find", _DUMPBIN_PATTERN])
    if code != 0:
        return None
    for line in out.splitlines():
        candidate = Path(line.strip())
        if candidate.exists():
            return str(candidate)
    return None


def find_tool(
    kind: str,
    *,
    which=shutil.which,
    environ=None,
    system=platform.system,
    runner: Runner | None = None,
) -> str | None:
    """Return the path of ``kind`` or None. Order: PATH, then the kind's platform roots."""
    if kind not in SUPPORTED_KINDS:
        raise ValueError(f"unsupported tool kind: {kind}")
    environ = os.environ if environ is None else environ
    current_system = system()
    on_path = which(kind)
    if on_path:
        return on_path
    if kind in ("ilspycmd", "dotnet-il", "cpp2il"):
        tools_dir = dotnet_tools_dir(environ)
        for name in (kind, f"{kind}.exe"):
            candidate = tools_dir / name
            if candidate.exists():
                return str(candidate)
        return None
    if kind == "analyzeHeadless":
        return _find_analyze_headless(environ, current_system)
    if kind == "dumpbin":
        if current_system.lower() != "windows":
            return None
        return _find_dumpbin(environ, runner)
    return None
