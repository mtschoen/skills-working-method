#!/usr/bin/env python3
"""Export every function of a binary as decompiled C through Ghidra headless.

    python scripts/ghidra-decompile.py BIN --output out.c [--filter NAME] [--timeout 60]
                                       [--project-dir DIR] [--project-name NAME] [--ghidra PATH]

The project lives in a scratch directory (never inside a repository: the import
pulls system libraries in as well) and is reused on the next run of the same
binary, so re-exports skip the analysis pass.
"""

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from decompilers.discovery import find_tool
from decompilers.ghidra import run_decompile

_GHIDRA_POINTER = (
    "analyzeHeadless not found: set GHIDRA_INSTALL_DIR to an unpacked Ghidra release "
    "(https://github.com/NationalSecurityAgency/ghidra/releases) or pass --ghidra"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export decompiled C for every function via Ghidra headless"
    )
    parser.add_argument("binary", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--project-dir", type=Path, default=Path(tempfile.gettempdir()) / "ghidra-projects"
    )
    parser.add_argument("--project-name", default=None)
    parser.add_argument(
        "--filter", dest="name_filter", default=None, help="only functions whose name contains this"
    )
    parser.add_argument(
        "--timeout",
        dest="timeout_seconds",
        type=int,
        default=60,
        help="per-function decompile timeout",
    )
    parser.add_argument("--ghidra", default=None, help="path to analyzeHeadless (or .bat)")
    arguments = parser.parse_args()

    analyze_headless = arguments.ghidra or find_tool("analyzeHeadless")
    if not analyze_headless:
        print(_GHIDRA_POINTER)
        return 2
    report = run_decompile(
        arguments.binary,
        arguments.output,
        project_dir=arguments.project_dir,
        project_name=arguments.project_name or arguments.binary.stem,
        analyze_headless=analyze_headless,
        script_dir=Path(__file__).resolve().parent / "ghidra_scripts",
        name_filter=arguments.name_filter,
        timeout_seconds=arguments.timeout_seconds,
    )
    functions = report.summary.functions
    unnamed = report.summary.unnamed
    note = ""
    if functions == 0:
        note = " (no functions matched)"
    elif unnamed == functions:
        note = " (no symbols: every function is FUN_)"
    print(" ".join(report.command))
    print(
        f"exit={report.exit_code} seconds={report.seconds:.1f} "
        f"functions={functions} named={functions - unnamed} unnamed={unnamed}{note}"
    )
    return 0 if report.exit_code == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
