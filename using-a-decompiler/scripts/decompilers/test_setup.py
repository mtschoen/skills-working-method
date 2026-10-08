from decompilers import setup


def _find_none(kind, **_):
    return None


def _find_all(kind, **_):
    return f"/bin/{kind}"


def test_platform_targets():
    assert setup.platform_targets("Linux") == (
        "ilspycmd",
        "dotnet-il",
        "analyzeHeadless",
        "java",
        "objdump",
    )
    assert setup.platform_targets("Windows") == (
        "ilspycmd",
        "dotnet-il",
        "analyzeHeadless",
        "java",
        "dumpbin",
    )
    assert setup.platform_targets("Darwin") == (
        "ilspycmd",
        "dotnet-il",
        "analyzeHeadless",
        "java",
        "llvm-objdump",
    )
    assert setup.platform_targets("Plan9") == ()


def test_present_tools_are_reported_and_not_installed():
    calls = []

    def runner(command):
        calls.append(command)
        return 0, 'openjdk version "21.0.2" 2024-01-16', ""

    results = setup.run(system=lambda: "Linux", find=_find_all, runner=runner, environ={})
    assert all(result.status == "present" for result in results)
    assert not [c for c in calls if "install" in c]


def test_missing_dotnet_tool_is_installed_via_dotnet(tmp_path):
    calls = []

    def find(kind, **_):
        return "/usr/bin/dotnet" if kind == "dotnet" else None

    def runner(command):
        calls.append(command)
        return 0, "Tool 'ilspycmd' was successfully installed.", ""

    results = setup.run(
        only=["ilspycmd"],
        system=lambda: "Linux",
        find=find,
        runner=runner,
        environ={"HOME": str(tmp_path)},
    )
    assert results[0].status == "installed"
    assert calls == [["/usr/bin/dotnet", "tool", "install", "--global", "ilspycmd"]]
    assert f"Ensure {tmp_path / '.dotnet' / 'tools'} is on PATH." in results[0].detail
    assert "DOTNET_ROLL_FORWARD=Major" in results[0].detail


def test_missing_dotnet_sdk_is_manual():
    results = setup.run(
        only=["ilspycmd"],
        system=lambda: "Linux",
        find=_find_none,
        runner=lambda c: (1, "", ""),
        environ={},
    )
    assert results[0].status == "manual"
    assert "SDK" in results[0].detail


def test_failed_install_carries_stderr():
    def find(kind, **_):
        return "/usr/bin/dotnet" if kind == "dotnet" else None

    results = setup.run(
        only=["dotnet-il"],
        system=lambda: "Linux",
        find=find,
        runner=lambda c: (1, "", "NU1101: Unable to find package"),
        environ={},
    )
    assert results[0].status == "failed"
    assert "NU1101" in results[0].detail


def test_old_java_is_manual():
    results = setup.run(
        only=["java"],
        system=lambda: "Linux",
        find=_find_all,
        runner=lambda c: (0, 'openjdk version "17.0.20.1" 2026-01-20', ""),
        environ={},
    )
    assert results[0].status == "manual"
    assert "21" in results[0].detail


def test_dry_run_reports_without_running():
    calls = []

    def find(kind, **_):
        return "/usr/bin/dotnet" if kind == "dotnet" else None

    results = setup.run(
        only=["ilspycmd"],
        dry_run=True,
        system=lambda: "Linux",
        find=find,
        runner=lambda c: calls.append(c) or (0, "", ""),
        environ={},
    )
    assert results[0].status == "dryrun"
    assert calls == []


def test_ghidra_missing_pointer():
    results = setup.run(
        only=["analyzeHeadless"],
        system=lambda: "Linux",
        find=_find_none,
        runner=lambda c: (1, "", ""),
        environ={},
    )
    assert results[0].status == "manual"
    assert "GHIDRA_INSTALL_DIR" in results[0].detail
