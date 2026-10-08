import importlib.util
import sys
from pathlib import Path
from typing import NamedTuple

_MODULE_PATH = Path(__file__).resolve().parent / "setup-decompilers.py"
_SPEC = importlib.util.spec_from_file_location("setup_decompilers", _MODULE_PATH)
setup_decompilers = importlib.util.module_from_spec(_SPEC)
sys.modules["setup_decompilers"] = setup_decompilers
_SPEC.loader.exec_module(setup_decompilers)


class _FakeResult(NamedTuple):
    kind: str
    status: str
    detail: str


def test_main_passes_only_and_dry_run(monkeypatch):
    captured = {}

    def fake_run(only, dry_run):
        captured["only"] = only
        captured["dry_run"] = dry_run
        return [_FakeResult("ilspycmd", "present", "/bin/ilspycmd")]

    monkeypatch.setattr(setup_decompilers, "run", fake_run)
    monkeypatch.setattr(
        sys, "argv", ["setup-decompilers.py", "--dry-run", "--only", "ilspycmd,java"]
    )
    assert setup_decompilers.main() == 0
    assert captured == {"only": ["ilspycmd", "java"], "dry_run": True}


def test_main_returns_one_on_failure(monkeypatch):
    monkeypatch.setattr(
        setup_decompilers,
        "run",
        lambda only, dry_run: [_FakeResult("dotnet-il", "failed", "NU1101")],
    )
    monkeypatch.setattr(sys, "argv", ["setup-decompilers.py"])
    assert setup_decompilers.main() == 1


def test_manual_results_do_not_fail(monkeypatch):
    monkeypatch.setattr(
        setup_decompilers,
        "run",
        lambda only, dry_run: [_FakeResult("analyzeHeadless", "manual", "set GHIDRA_INSTALL_DIR")],
    )
    monkeypatch.setattr(sys, "argv", ["setup-decompilers.py"])
    assert setup_decompilers.main() == 0


def test_every_result_is_printed_and_empty_only_items_dropped(monkeypatch, capsys):
    captured = {}

    def fake_run(only, dry_run):
        captured["only"] = only
        return [
            _FakeResult("ilspycmd", "present", "found-here"),
            _FakeResult("java", "present", "major 26"),
        ]

    monkeypatch.setattr(setup_decompilers, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["setup-decompilers.py", "--only", "ilspycmd,,java,"])
    assert setup_decompilers.main() == 0
    assert captured["only"] == ["ilspycmd", "java"]
    output = capsys.readouterr().out
    assert "found-here" in output
    assert "major 26" in output
