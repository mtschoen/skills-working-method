#!/usr/bin/env python3
"""Detect-then-install the decompilers this skill drives.

Idempotent and platform-gated. Installs only the user-scope .NET tools
(ilspycmd, dotnet-il); everything else is detected and reported with the
manual next step. See references/tooling-setup.md.

    python scripts/setup-decompilers.py            # detect everything, install what it can
    python scripts/setup-decompilers.py --dry-run
    python scripts/setup-decompilers.py --only ilspycmd,analyzeHeadless
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from decompilers.setup import run


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install the decompilers used by using-a-decompiler"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the actions without running them"
    )
    parser.add_argument(
        "--only", default=None, help="comma-separated subset of tool kinds to act on"
    )
    arguments = parser.parse_args()
    only = [kind for kind in arguments.only.split(",") if kind] if arguments.only else None
    print("Decompiler setup (detect, then install what is missing):")
    results = run(only=only, dry_run=arguments.dry_run)
    for result in results:
        print(f"  {result.kind:16} {result.status:10} {result.detail}")
    manual = [result for result in results if result.status == "manual"]
    failed = [result for result in results if result.status == "failed"]
    if manual:
        print("\nManual follow-up needed:")
        for result in manual:
            print(f"  {result.kind}: {result.detail}")
    if failed:
        print("\nFailed:")
        for result in failed:
            print(f"  {result.kind}: {result.detail}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
