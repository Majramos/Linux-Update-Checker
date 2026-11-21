import subprocess

import pytest

from linux_update_checker.managers.shell import run_subprocess


def test_run_subprocess_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyProcess:
        returncode = 0
        stdout = "hello\n"
        stderr = ""

    def fake_run(
        cmd: list, check: str, capture_output: bool, text: bool, timeout: int
    ) -> DummyProcess:
        assert cmd == ["echo", "hello"]
        assert capture_output is True
        assert text is True
        assert timeout == 120
        return DummyProcess()

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_subprocess(["echo", "hello"])

    assert result == (0, "hello\n", "")


def test_run_subprocess_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        cmd: list, check: str, capture_output: bool, text: bool, timeout: int
    ) -> None:
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_subprocess(["sleep", "999"], timeout=5)

    assert result == (1, "", "Command timed out after 5s: sleep 999")


def test_run_subprocess_command_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        cmd: list, check: str, capture_output: bool, text: bool, timeout: int
    ) -> FileNotFoundError:
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_subprocess(["missing-binary"])

    assert result == (127, "", "Command not found: missing-binary")


def test_run_subprocess_permission_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        cmd: list, check: str, capture_output: bool, text: bool, timeout: int
    ) -> PermissionError:
        raise PermissionError("boom")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_subprocess(["anything"])

    assert result == (126, "", "Permission denied: anything")


def test_run_subprocess_os_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        cmd: list, check: str, capture_output: bool, text: bool, timeout: int
    ) -> OSError:
        raise OSError("boom")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_subprocess(["anything"])

    assert result == (1, "", "Failed to execute anything: boom")
