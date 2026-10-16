"""Tests for post-coverage-status.py.

The module file uses a hyphenated name (matching the other CI/entry-point
scripts in this repository), so it cannot be imported with a plain `import`
statement. Load it by path instead, the same way it runs in CI.
"""

import importlib.util
import json
import sys
from pathlib import Path
from xml.etree import ElementTree

import pytest

_MODULE_PATH = Path(__file__).resolve().parent / "post-coverage-status.py"
_SPEC = importlib.util.spec_from_file_location("post_coverage_status", _MODULE_PATH)
post_coverage_status = importlib.util.module_from_spec(_SPEC)
sys.modules["post_coverage_status"] = post_coverage_status
_SPEC.loader.exec_module(post_coverage_status)


def _write_coverage_json(path: Path, percent: float) -> None:
    path.write_text(json.dumps({"totals": {"percent_covered": percent}}))


def _write_cobertura(path: Path, lines: dict[str, int], filename: str = "a.py") -> None:
    root = ElementTree.Element("coverage")
    package = ElementTree.SubElement(root, "packages")
    class_node = ElementTree.SubElement(package, "class", {"filename": filename})
    lines_node = ElementTree.SubElement(class_node, "lines")
    for number, hits in lines.items():
        ElementTree.SubElement(
            lines_node, "line", {"number": number, "hits": str(hits)}
        )
    ElementTree.ElementTree(root).write(path)


def test_percent_from_coverage_json_reads_totals(tmp_path):
    coverage_json = tmp_path / "coverage.json"
    _write_coverage_json(coverage_json, 87.5)
    assert post_coverage_status._percent_from_coverage_json(str(coverage_json)) == 87.5


def test_percent_from_cobertura_merges_across_files(tmp_path):
    _write_cobertura(tmp_path / "one.xml", {"1": 1, "2": 0, "3": 0}, filename="a.py")
    _write_cobertura(tmp_path / "two.xml", {"1": 0, "2": 0, "3": 1}, filename="a.py")

    percent = post_coverage_status._percent_from_cobertura([str(tmp_path / "*.xml")])

    # line 1 covered by one.xml, line 3 covered by two.xml, line 2 covered by neither.
    assert percent == pytest.approx(200.0 / 3.0)


def test_percent_from_cobertura_no_files_matched_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        post_coverage_status._percent_from_cobertura([str(tmp_path / "nothing-*.xml")])


def test_percent_from_cobertura_no_lines_raises(tmp_path):
    empty = tmp_path / "empty.xml"
    root = ElementTree.Element("coverage")
    ElementTree.SubElement(root, "packages")
    ElementTree.ElementTree(root).write(empty)

    with pytest.raises(ValueError, match="no source lines"):
        post_coverage_status._percent_from_cobertura([str(empty)])


def test_post_skips_without_ci_env(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    def _fail_if_called(*_args, **_kwargs):
        raise AssertionError("urlopen must not be called outside CI")

    monkeypatch.setattr(post_coverage_status.urllib.request, "urlopen", _fail_if_called)

    post_coverage_status._post("pr-crew/coverage", "success", "90.0% line coverage")

    assert "skipping post (not in CI)" in capsys.readouterr().out


def test_post_sends_expected_request(monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "deadbeef")
    monkeypatch.setenv("GITHUB_TOKEN", "sekret")
    monkeypatch.setenv("GITHUB_REPOSITORY", "schoen/skills-working-method")
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://gitea.example")
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    monkeypatch.delenv("GITHUB_API_URL", raising=False)

    captured = {}

    def _fake_urlopen(request):
        captured["request"] = request

        class _Response:
            def read(self):
                return b""

        return _Response()

    monkeypatch.setattr(post_coverage_status.urllib.request, "urlopen", _fake_urlopen)

    post_coverage_status._post("pr-crew/coverage", "success", "90.0% line coverage")

    request = captured["request"]
    assert request.full_url == (
        "https://gitea.example/api/v1/repos/schoen/skills-working-method/statuses/deadbeef"
    )
    assert request.get_header("Authorization") == "token sekret"
    body = json.loads(request.data)
    assert body == {
        "context": "pr-crew/coverage",
        "state": "success",
        "description": "90.0% line coverage",
        "target_url": "https://gitea.example/schoen/skills-working-method/actions/runs/123",
    }


def test_post_uses_github_api_url_when_set(monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "deadbeef")
    monkeypatch.setenv("GITHUB_TOKEN", "sekret")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_API_URL", "https://api.github.com")
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)

    captured = {}

    def _fake_urlopen(request):
        captured["request"] = request

        class _Response:
            def read(self):
                return b""

        return _Response()

    monkeypatch.setattr(post_coverage_status.urllib.request, "urlopen", _fake_urlopen)

    post_coverage_status._post(
        "pr-crew/coverage", "error", "coverage measurement failed"
    )

    assert (
        captured["request"].full_url
        == "https://api.github.com/repos/owner/repo/statuses/deadbeef"
    )


def test_main_success_path_posts_success(tmp_path, monkeypatch, capsys):
    coverage_json = tmp_path / "coverage.json"
    _write_coverage_json(coverage_json, 91.2345)

    posted = {}

    def _fake_post(context, state, description):
        posted["context"] = context
        posted["state"] = state
        posted["description"] = description

    monkeypatch.setattr(post_coverage_status, "_post", _fake_post)

    rc = post_coverage_status.main(["prog", "--coverage-json", str(coverage_json)])

    assert rc == 0
    assert posted == {
        "context": "pr-crew/coverage",
        "state": "success",
        "description": "91.23% line coverage",
    }
    assert (
        "posted pr-crew/coverage success: 91.23% line coverage"
        in capsys.readouterr().out
    )


def test_main_measurement_failure_posts_error(tmp_path, monkeypatch, capsys):
    missing = tmp_path / "does-not-exist.json"

    posted = {}

    def _fake_post(context, state, description):
        posted["context"] = context
        posted["state"] = state
        posted["description"] = description

    monkeypatch.setattr(post_coverage_status, "_post", _fake_post)

    rc = post_coverage_status.main(["prog", "--coverage-json", str(missing)])

    assert rc == 0
    assert posted["state"] == "error"
    assert "coverage measurement failed" in capsys.readouterr().err


def test_main_cobertura_argument_merges_and_posts(tmp_path, monkeypatch):
    _write_cobertura(tmp_path / "report.xml", {"1": 1, "2": 1}, filename="a.py")

    posted = {}
    monkeypatch.setattr(
        post_coverage_status,
        "_post",
        lambda context, state, description: posted.update(
            context=context, state=state, description=description
        ),
    )

    rc = post_coverage_status.main(
        ["prog", "--cobertura", str(tmp_path / "*.xml"), "--context", "custom/context"]
    )

    assert rc == 0
    assert posted["context"] == "custom/context"
    assert posted["state"] == "success"
    assert posted["description"] == "100.0% line coverage"
