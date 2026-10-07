import json
from pathlib import Path

import pytest

from decompilers import ghidra


def test_build_command_import_form(tmp_path):
    command = ghidra.build_command(
        "/opt/ghidra/support/analyzeHeadless",
        tmp_path / "proj",
        "sample",
        Path("/bin/x.so"),
        tmp_path / "out.c",
        Path("/skill/scripts/ghidra_scripts"),
        reuse=False,
        name_filter=None,
        timeout_seconds=60,
    )
    assert command[:3] == [
        "/opt/ghidra/support/analyzeHeadless",
        str(tmp_path / "proj"),
        "sample",
    ]
    assert command[3:5] == ["-import", str(Path("/bin/x.so"))]
    assert "-overwrite" in command
    assert command[command.index("-postScript") + 1] == "DecompileAllToFile.java"
    assert command[command.index("-postScript") + 2 :] == [
        str(tmp_path / "out.c"),
        "-",
        "60",
    ]
    assert command[command.index("-scriptPath") + 1] == str(Path("/skill/scripts/ghidra_scripts"))


def test_build_command_reuse_form_uses_process(tmp_path):
    command = ghidra.build_command(
        "ah",
        tmp_path,
        "sample",
        Path("/bin/x.so"),
        tmp_path / "o.c",
        Path("/s"),
        reuse=True,
        name_filter="parse",
        timeout_seconds=30,
    )
    assert "-import" not in command
    assert command[command.index("-process") + 1] == "x.so"
    assert "-noanalysis" in command
    assert command[-2:] == ["parse", "30"]


def test_project_exists(tmp_path):
    assert not ghidra.project_exists(tmp_path, "sample")
    (tmp_path / "sample.gpr").write_text("")
    assert ghidra.project_exists(tmp_path, "sample")


def test_windows_launcher_quotes_and_redirects(tmp_path):
    text = ghidra.windows_launcher(
        ["C:\\g\\support\\analyzeHeadless.bat", "C:\\p d", "n", "-import", "C:\\b.dll"],
        tmp_path / "run.log",
    )
    assert text.startswith("@echo off")
    assert 'call "C:\\g\\support\\analyzeHeadless.bat" "C:\\p d" "n" -import "C:\\b.dll"' in text
    assert f'> "{tmp_path / "run.log"}" 2>&1' in text
    assert "exit /b %ERRORLEVEL%" in text


def test_summarize_output_counts_unnamed():
    text = (
        "// ==== FUN_00401000 @ 00401000\nvoid FUN_00401000(void) {}\n"
        "// ==== parse_value @ 00401020\nint parse_value(void) {}\n"
    )
    summary = ghidra.summarize_output(text)
    assert summary == ghidra.Summary(functions=2, unnamed=1)


def test_run_decompile_uses_runner_and_reports(tmp_path):
    calls = []
    output = tmp_path / "out.c"
    binary = tmp_path / "x"
    binary.write_bytes(b"abc")

    def runner(command):
        calls.append(command)
        output.write_text("// ==== main @ 1\nint main(void) {}\n")
        return 0, "DecompileAllToFile wrote 1 functions", ""

    report = ghidra.run_decompile(
        binary,
        output,
        project_dir=tmp_path / "proj",
        project_name="x",
        analyze_headless="ah",
        script_dir=Path("/s"),
        system=lambda: "Linux",
        runner=runner,
        digest=lambda path: "d1",
        clock=iter([10.0, 12.5]).__next__,
    )
    assert report.exit_code == 0
    assert report.seconds == 2.5
    assert report.summary.functions == 1
    assert calls[0][0] == "ah"


def test_run_decompile_on_windows_writes_and_runs_bat(tmp_path):
    written = {}
    calls = []
    binary = tmp_path / "b.dll"
    binary.write_bytes(b"abc")

    def write_text(path, text):
        written[path] = text

    def runner(command):
        calls.append(command)
        (tmp_path / "out.c").write_text("")
        return 0, "", ""

    ghidra.run_decompile(
        binary,
        tmp_path / "out.c",
        project_dir=tmp_path / "proj",
        project_name="b",
        analyze_headless="C:/g/support/analyzeHeadless.bat",
        script_dir=Path("C:/s"),
        system=lambda: "Windows",
        runner=runner,
        write_text=write_text,
        digest=lambda path: "d1",
        clock=iter([0.0, 1.0]).__next__,
    )
    bat_path = next(iter(written))
    assert str(bat_path).endswith(".bat")
    assert calls[0] == ["cmd", "/c", str(bat_path)]


def test_windows_launcher_quotes_every_non_flag_argument(tmp_path):
    text = ghidra.windows_launcher(["ah", "proj", "n", "-x", "vector<int>"], tmp_path / "r.log")
    assert 'call "ah" "proj" "n" -x "vector<int>" >' in text


def test_windows_launcher_doubles_percent(tmp_path):
    text = ghidra.windows_launcher(["ah", "100%"], tmp_path / "r.log")
    assert '"100%%"' in text


def test_windows_launcher_rejects_embedded_quote(tmp_path):
    with pytest.raises(ValueError):
        ghidra.windows_launcher(["ah", 'a"b'], tmp_path / "r.log")


def _binary(tmp_path, content=b"abc"):
    binary = tmp_path / "bin" / "GameAssembly.dll"
    binary.parent.mkdir(exist_ok=True)
    binary.write_bytes(content)
    return binary


def _run(tmp_path, binary, runner, digest=lambda path: "d1"):
    return ghidra.run_decompile(
        binary,
        tmp_path / "out.c",
        project_dir=tmp_path / "proj",
        project_name="GameAssembly",
        analyze_headless="ah",
        script_dir=Path("/s"),
        system=lambda: "Linux",
        runner=runner,
        digest=digest,
        clock=iter([0.0, 1.0]).__next__,
    )


def _write_project(tmp_path, binary, sha256):
    project = tmp_path / "proj"
    project.mkdir(exist_ok=True)
    (project / "GameAssembly.gpr").write_text("")
    sidecar = {"path": str(binary.resolve()), "size": binary.stat().st_size, "sha256": sha256}
    (project / "GameAssembly.source.json").write_text(json.dumps(sidecar))
    return project


def test_project_matches_when_sidecar_digest_equals(tmp_path):
    binary = _binary(tmp_path)
    project = _write_project(tmp_path, binary, "d1")
    assert ghidra.project_matches(project, "GameAssembly", binary, digest=lambda path: "d1")


def test_project_matches_false_on_digest_mismatch(tmp_path):
    binary = _binary(tmp_path)
    project = _write_project(tmp_path, binary, "d1")
    assert not ghidra.project_matches(project, "GameAssembly", binary, digest=lambda path: "d2")


def test_project_matches_false_without_sidecar_or_project(tmp_path):
    binary = _binary(tmp_path)
    project = _write_project(tmp_path, binary, "d1")
    (project / "GameAssembly.source.json").unlink()
    assert not ghidra.project_matches(project, "GameAssembly", binary, digest=lambda path: "d1")
    (project / "GameAssembly.gpr").unlink()
    assert not ghidra.project_matches(project, "GameAssembly", binary, digest=lambda path: "d1")


def test_run_decompile_reuses_matching_project(tmp_path):
    binary = _binary(tmp_path)
    _write_project(tmp_path, binary, "d1")
    report = _run(tmp_path, binary, lambda command: (0, "", ""))
    assert "-process" in report.command and "-import" not in report.command


def test_run_decompile_reimports_on_digest_mismatch(tmp_path):
    binary = _binary(tmp_path)
    _write_project(tmp_path, binary, "stale")
    report = _run(tmp_path, binary, lambda command: (0, "", ""))
    assert "-import" in report.command and "-overwrite" in report.command


def test_run_decompile_reimports_when_sidecar_missing(tmp_path):
    binary = _binary(tmp_path)
    project = _write_project(tmp_path, binary, "d1")
    (project / "GameAssembly.source.json").unlink()
    report = _run(tmp_path, binary, lambda command: (0, "", ""))
    assert "-import" in report.command


def test_sidecar_written_on_success_only(tmp_path):
    binary = _binary(tmp_path)
    sidecar = tmp_path / "proj" / "GameAssembly.source.json"
    _run(tmp_path, binary, lambda command: (1, "", ""))
    assert not sidecar.exists()
    _run(tmp_path, binary, lambda command: (0, "", ""))
    assert json.loads(sidecar.read_text(encoding="utf-8")) == {
        "path": str(binary.resolve()),
        "size": 3,
        "sha256": "d1",
    }


def test_run_decompile_ignores_stale_output_when_ghidra_fails(tmp_path):
    binary = _binary(tmp_path)
    (tmp_path / "out.c").write_text("// ==== old @ 1\nint old(void) {}\n")
    report = _run(tmp_path, binary, lambda command: (1, "", "boom"))
    assert report.summary == ghidra.Summary(0, 0)
    assert not (tmp_path / "out.c").exists()


def test_sha256_of_hashes_file_contents(tmp_path):
    path = tmp_path / "f"
    path.write_bytes(b"abc")
    assert ghidra.sha256_of(path) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
