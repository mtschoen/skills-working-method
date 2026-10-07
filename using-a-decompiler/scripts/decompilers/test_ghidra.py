from pathlib import Path

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
    assert 'call "C:\\g\\support\\analyzeHeadless.bat" "C:\\p d" n -import "C:\\b.dll"' in text
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

    def runner(command):
        calls.append(command)
        output.write_text("// ==== main @ 1\nint main(void) {}\n")
        return 0, "DecompileAllToFile wrote 1 functions", ""

    report = ghidra.run_decompile(
        Path("/bin/x"),
        output,
        project_dir=tmp_path / "proj",
        project_name="x",
        analyze_headless="ah",
        script_dir=Path("/s"),
        system=lambda: "Linux",
        runner=runner,
        clock=iter([10.0, 12.5]).__next__,
    )
    assert report.exit_code == 0
    assert report.seconds == 2.5
    assert report.summary.functions == 1
    assert calls[0][0] == "ah"


def test_run_decompile_on_windows_writes_and_runs_bat(tmp_path):
    written = {}
    calls = []

    def write_text(path, text):
        written[path] = text

    def runner(command):
        calls.append(command)
        (tmp_path / "out.c").write_text("")
        return 0, "", ""

    ghidra.run_decompile(
        Path("C:/b.dll"),
        tmp_path / "out.c",
        project_dir=tmp_path / "proj",
        project_name="b",
        analyze_headless="C:/g/support/analyzeHeadless.bat",
        script_dir=Path("C:/s"),
        system=lambda: "Windows",
        runner=runner,
        write_text=write_text,
        clock=iter([0.0, 1.0]).__next__,
    )
    bat_path = next(iter(written))
    assert str(bat_path).endswith(".bat")
    assert calls[0] == ["cmd", "/c", str(bat_path)]
