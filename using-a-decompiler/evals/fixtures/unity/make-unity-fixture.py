#!/usr/bin/env python3
"""Create a one-script Unity project and build it as a Mono and an IL2CPP Win64 player.

    python make-unity-fixture.py --editor PATH/TO/Unity.exe --out DIR [--backends mono,il2cpp]

Needs an editor with the Windows IL2CPP module installed. Nothing it builds is
committed; DIR is scratch.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

FIXTURE_ROOT = Path(__file__).resolve().parent
PROJECT_NAME = "FixtureProject"


def run_editor(editor: Path, arguments: list[str], log_path: Path) -> int:
    command = [str(editor), "-batchmode", "-quit", "-logFile", str(log_path), *arguments]
    print(" ".join(command))
    return subprocess.run(command, check=False).returncode


def create_project(editor: Path, project_dir: Path) -> int:
    code = run_editor(editor, ["-createProject", str(project_dir)], project_dir.parent / "create.log")
    if code != 0:
        return code
    for relative in ("Assets/Scripts/DamageProbe.cs", "Assets/Editor/FixtureBuild.cs"):
        destination = project_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIXTURE_ROOT / relative, destination)
    return 0


def build_player(editor: Path, project_dir: Path, backend: str, output_root: Path) -> int:
    player_dir = output_root / f"player-{backend}"
    code = run_editor(
        editor,
        ["-projectPath", str(project_dir), "-executeMethod", "FixtureBuild.Build",
         "-backend", backend, "-outDir", str(player_dir)],
        output_root / f"build-{backend}.log",
    )
    executable = player_dir / f"{PROJECT_NAME}.exe"
    if code != 0 or not executable.exists():
        print(f"{backend}: build failed (exit {code}); see {output_root / f'build-{backend}.log'}")
        return code or 1
    print(f"{backend}: {player_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Unity Mono and IL2CPP fixture players")
    parser.add_argument("--editor", type=Path, required=True, help="path to Unity.exe (needs the IL2CPP module)")
    parser.add_argument("--out", type=Path, required=True, help="scratch output directory")
    parser.add_argument("--backends", default="mono,il2cpp")
    arguments = parser.parse_args()

    arguments.out = arguments.out.resolve()
    arguments.out.mkdir(parents=True, exist_ok=True)
    project_dir = arguments.out / PROJECT_NAME
    if not project_dir.exists():
        code = create_project(arguments.editor, project_dir)
        if code != 0:
            print(f"createProject failed (exit {code}); see {arguments.out / 'create.log'}")
            return code
    worst = 0
    for backend in [name for name in arguments.backends.split(",") if name]:
        worst = max(worst, build_player(arguments.editor, project_dir, backend, arguments.out))
    return worst


if __name__ == "__main__":
    sys.exit(main())
