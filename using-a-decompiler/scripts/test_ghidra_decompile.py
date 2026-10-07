import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parent / "ghidra-decompile.py"
_SPEC = importlib.util.spec_from_file_location("ghidra_decompile", _MODULE_PATH)
ghidra_decompile = importlib.util.module_from_spec(_SPEC)
sys.modules["ghidra_decompile"] = ghidra_decompile
_SPEC.loader.exec_module(ghidra_decompile)

from decompilers.ghidra import RunReport, Summary  # noqa: E402


def test_main_reports_symbol_status(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(
        ghidra_decompile, "find_tool", lambda kind, **_: "/g/support/analyzeHeadless"
    )
    monkeypatch.setattr(
        ghidra_decompile, "run_decompile", lambda *a, **k: RunReport(["ah"], 0, 2.0, Summary(3, 3))
    )
    monkeypatch.setattr(
        sys, "argv", ["ghidra-decompile.py", str(tmp_path / "b"), "--output", str(tmp_path / "o.c")]
    )
    assert ghidra_decompile.main() == 0
    out = capsys.readouterr().out
    assert "functions=3 unnamed=3" in out and "no symbols" in out


def test_main_exit_two_without_ghidra(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(ghidra_decompile, "find_tool", lambda kind, **_: None)
    monkeypatch.setattr(
        sys, "argv", ["ghidra-decompile.py", str(tmp_path / "b"), "--output", str(tmp_path / "o.c")]
    )
    assert ghidra_decompile.main() == 2
    assert "GHIDRA_INSTALL_DIR" in capsys.readouterr().out


def test_main_passes_filter_and_timeout(monkeypatch, tmp_path):
    captured = {}

    def fake_run(binary, output, **kwargs):
        captured.update(kwargs)
        return RunReport([], 0, 0.1, Summary(1, 0))

    monkeypatch.setattr(ghidra_decompile, "find_tool", lambda kind, **_: "ah")
    monkeypatch.setattr(ghidra_decompile, "run_decompile", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ghidra-decompile.py",
            str(tmp_path / "b"),
            "--output",
            str(tmp_path / "o.c"),
            "--filter",
            "parse",
            "--timeout",
            "30",
        ],
    )
    assert ghidra_decompile.main() == 0
    assert captured["name_filter"] == "parse" and captured["timeout_seconds"] == 30
    assert captured["script_dir"].name == "ghidra_scripts"
