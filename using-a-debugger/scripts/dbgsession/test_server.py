import socket
import threading
from pathlib import Path

import pytest
from server import Server, _dispatch, _make_backend, run_server_child


class DummyBackend:
    def __init__(self):
        self.stopped = False
        self.started = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def set_breakpoint(self, file, line):
        return f"breakpoint set {file}:{line}"

    def run(self):
        return "running"

    def cont(self):
        return "continuing"

    def step_over(self):
        return "stepped over"

    def step_into(self):
        return "stepped into"

    def backtrace(self):
        return "frame #0"

    def read_local(self, name):
        return f"local {name}=42"

    def raw(self, cmd):
        return f"raw {cmd}"


def test_dispatch_stop():
    backend = DummyBackend()
    assert _dispatch(backend, "__STOP__") == "__STOP__"


def test_dispatch_empty():
    backend = DummyBackend()
    assert _dispatch(backend, "   ") == "error: empty command"


def test_dispatch_break_errors():
    backend = DummyBackend()
    assert "requires FILE:LINE" in _dispatch(backend, "break no_colon")
    assert "invalid line number" in _dispatch(backend, "break foo:abc")


def test_dispatch_break_success():
    backend = DummyBackend()
    assert _dispatch(backend, "break test.py:12") == "breakpoint set test.py:12"


def test_dispatch_no_arg_table():
    backend = DummyBackend()
    assert _dispatch(backend, "run") == "running"
    assert _dispatch(backend, "continue") == "continuing"
    assert _dispatch(backend, "step") == "stepped over"
    assert _dispatch(backend, "stepin") == "stepped into"
    assert _dispatch(backend, "bt") == "frame #0"


def test_dispatch_one_arg_table():
    backend = DummyBackend()
    assert _dispatch(backend, "local foo") == "local foo=42"
    assert _dispatch(backend, "raw p 1+1") == "raw p 1+1"


def test_dispatch_unknown_verb():
    backend = DummyBackend()
    assert "unknown verb" in _dispatch(backend, "unknown_cmd arg")


def test_server_serve_forever(tmp_path: Path):
    backend = DummyBackend()
    server = Server(backend, tmp_path)
    port = server.port
    assert port > 0

    # Daemon, so a failed assertion below cannot keep the pytest process alive.
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    # The socket listens from construction, so no wait for the port file is needed.
    with socket.create_connection(("127.0.0.1", port), timeout=5.0) as conn:
        conn.sendall(b"local x\n")
        resp = conn.recv(1024).decode()
        assert resp == "local x=42\n"

    # serve_forever writes the port file before it accepts, so an answered
    # command means the file is complete.
    assert (tmp_path / "port").read_text() == str(port)

    # Send __STOP__ command
    with socket.create_connection(("127.0.0.1", port), timeout=5.0) as conn:
        conn.sendall(b"__STOP__\n")
        resp = conn.recv(1024).decode()
        assert resp == "stopped\n"

    thread.join(timeout=5.0)
    assert not thread.is_alive()
    assert backend.stopped


def test_make_backend_all_debuggers(monkeypatch):
    monkeypatch.setattr("backends.mi.MiBackend.__init__", lambda self, *a, **k: None)
    monkeypatch.setattr("backends.lldb_cli.LldbCliBackend.__init__", lambda self, *a, **k: None)
    monkeypatch.setattr("backends.cdb.CdbBackend.__init__", lambda self, *a, **k: None)

    assert _make_backend("netcoredbg", "app.dll", [], None) is not None
    assert _make_backend("gdb", "app", [], None) is not None
    assert _make_backend("lldb", "app", [], None) is not None
    assert _make_backend("cdb", "app.exe", [], None) is not None

    with pytest.raises(ValueError, match="unknown debugger"):
        _make_backend("nonexistent", "app", [], None)


def test_run_server_child(monkeypatch, tmp_path: Path):
    class Args:
        def __init__(self):
            self.session = "test-session"
            self.debugger = "lldb"
            self.debugger_path = "/path/to/lldb"
            self.program = "dummy"
            self.program_args = []

    mock_backend = DummyBackend()
    monkeypatch.setattr("server._make_backend", lambda *a, **k: mock_backend)
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))

    serve_called = []

    def mock_serve(self):
        serve_called.append(True)

    monkeypatch.setattr("server.Server.serve_forever", mock_serve)

    run_server_child(Args())

    assert mock_backend.started
    assert serve_called == [True]
