from decompilers import discovery


def test_supported_kinds_are_fixed():
    assert discovery.SUPPORTED_KINDS == (
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


def test_find_tool_prefers_path():
    found = discovery.find_tool(
        "ilspycmd",
        which=lambda name: "/usr/bin/ilspycmd" if name == "ilspycmd" else None,
        environ={},
        system=lambda: "Linux",
    )
    assert found == "/usr/bin/ilspycmd"


def test_find_tool_falls_back_to_dotnet_tools_dir(tmp_path):
    tool = tmp_path / ".dotnet" / "tools" / "ilspycmd"
    tool.parent.mkdir(parents=True)
    tool.write_text("")
    found = discovery.find_tool(
        "ilspycmd",
        which=lambda name: None,
        environ={"HOME": str(tmp_path)},
        system=lambda: "Linux",
    )
    assert found == str(tool)


def test_dotnet_tools_dir_honours_dotnet_cli_home(tmp_path):
    expected = tmp_path / ".dotnet" / "tools"
    assert discovery.dotnet_tools_dir({"DOTNET_CLI_HOME": str(tmp_path)}) == expected


def test_java_major_version_parses_modern_and_legacy():
    assert discovery.java_major_version('openjdk version "21.0.2" 2024-01-16') == 21
    assert discovery.java_major_version('java version "1.8.0_392"') == 8
    assert discovery.java_major_version("garbage") is None


def test_ghidra_search_roots_env_first_then_home_globs(tmp_path):
    older = tmp_path / "ghidra_10.0_PUBLIC"
    newer = tmp_path / "ghidra_11.4.2_PUBLIC"
    older.mkdir()
    newer.mkdir()
    configured = tmp_path / "configured"
    roots = discovery.ghidra_search_roots(
        {"GHIDRA_INSTALL_DIR": str(configured), "HOME": str(tmp_path)},
        home=tmp_path,
        system="Windows",
    )
    assert roots == [configured, newer, older]


def test_ghidra_search_roots_without_env_lists_home_globs_only(tmp_path):
    install = tmp_path / "ghidra_11.4.2_PUBLIC"
    install.mkdir()
    assert discovery.ghidra_search_roots(
        {"HOME": str(tmp_path)}, home=tmp_path, system="Windows"
    ) == [install]


def test_find_analyze_headless_under_ghidra_install_dir(tmp_path):
    script = tmp_path / "ghidra_11.4.2_PUBLIC" / "support" / "analyzeHeadless.bat"
    script.parent.mkdir(parents=True)
    script.write_text("")
    found = discovery.find_tool(
        "analyzeHeadless",
        which=lambda name: None,
        environ={"GHIDRA_INSTALL_DIR": str(script.parent.parent)},
        system=lambda: "Windows",
    )
    assert found == str(script)


def test_find_dumpbin_uses_vswhere_output(tmp_path):
    dumpbin = tmp_path / "dumpbin.exe"
    dumpbin.write_text("")
    vswhere = tmp_path / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    vswhere.parent.mkdir(parents=True)
    vswhere.write_text("")
    calls = []

    def runner(command):
        calls.append(command)
        return 0, f"{dumpbin}\n", ""

    found = discovery.find_tool(
        "dumpbin",
        which=lambda name: None,
        environ={"ProgramFiles(x86)": str(tmp_path)},
        system=lambda: "Windows",
        runner=runner,
    )
    assert found == str(dumpbin)
    assert calls
    assert calls[0][-1].startswith("VC/Tools/MSVC/")


def test_find_dumpbin_is_none_off_windows():
    found = discovery.find_tool(
        "dumpbin", which=lambda name: None, environ={}, system=lambda: "Linux"
    )
    assert found is None


def _dumpbin_environ(tmp_path, *, create_vswhere):
    if create_vswhere:
        vswhere = tmp_path / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
        vswhere.parent.mkdir(parents=True)
        vswhere.write_text("")
    return {"ProgramFiles(x86)": str(tmp_path), "HOME": str(tmp_path)}


def _find_dumpbin(environ, runner):
    return discovery.find_tool(
        "dumpbin",
        which=lambda name: None,
        environ=environ,
        system=lambda: "Windows",
        runner=runner,
    )


def test_find_dumpbin_is_none_when_vswhere_is_absent(tmp_path):
    calls = []

    def runner(command):
        calls.append(command)
        return 0, "", ""

    environ = _dumpbin_environ(tmp_path, create_vswhere=False)
    assert _find_dumpbin(environ, runner) is None
    assert calls == []


def test_find_dumpbin_is_none_when_runner_raises_file_not_found(tmp_path):
    def runner(command):
        raise FileNotFoundError(command[0])

    environ = _dumpbin_environ(tmp_path, create_vswhere=True)
    assert _find_dumpbin(environ, runner) is None


def test_find_dumpbin_is_none_on_non_zero_exit(tmp_path):
    environ = _dumpbin_environ(tmp_path, create_vswhere=True)
    assert _find_dumpbin(environ, lambda command: (1, "ignored.exe\n", "")) is None


def test_find_dumpbin_is_none_on_empty_output(tmp_path):
    environ = _dumpbin_environ(tmp_path, create_vswhere=True)
    assert _find_dumpbin(environ, lambda command: (0, "", "")) is None


def test_find_dumpbin_skips_blank_lines(tmp_path):
    environ = _dumpbin_environ(tmp_path, create_vswhere=True)
    assert _find_dumpbin(environ, lambda command: (0, "\n   \n", "")) is None
    dumpbin = tmp_path / "dumpbin.exe"
    dumpbin.write_text("")
    found = _find_dumpbin(environ, lambda command: (0, f"\n{dumpbin}\n", ""))
    assert found == str(dumpbin)
