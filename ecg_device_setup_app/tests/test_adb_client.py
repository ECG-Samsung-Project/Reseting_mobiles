from __future__ import annotations

import shutil
from typing import Any

import pytest

from backend.adb.adb_client import AdbClient
from backend.exceptions import AdbCommandError


class FakeProcess:
    def __init__(
        self,
        *,
        stdout: str = "Success\n",
        stderr: str = "",
        returncode: int = 0,
    ) -> None:
        self._stdout = stdout
        self._stderr = stderr
        self.returncode: int | None = returncode
        self.received_input: str | None = None
        self.terminated = False

    def communicate(
        self, input: str | None = None, timeout: float | None = None
    ) -> tuple[str, str]:
        del timeout
        self.received_input = input
        return self._stdout, self._stderr

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.returncode = -9


def test_command_uses_explicit_device_and_never_uses_shell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: "C:\\tools\\adb.exe")
    captured: dict[str, Any] = {}
    fake_process = FakeProcess()

    def fake_popen(command: list[str], **kwargs: Any) -> FakeProcess:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return fake_process

    client = AdbClient(popen_factory=fake_popen)
    result = client.run(
        ["install", "-r", "C:\\apks\\phone.apk"],
        device_id="R5CX123",
    )

    assert captured["command"] == [
        "C:\\tools\\adb.exe",
        "-s",
        "R5CX123",
        "install",
        "-r",
        "C:\\apks\\phone.apk",
    ]
    assert captured["kwargs"]["shell"] is False
    assert result.succeeded


def test_string_command_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: "adb")
    client = AdbClient(popen_factory=lambda *_args, **_kwargs: FakeProcess())

    with pytest.raises(ValueError):
        client.run("devices")  # type: ignore[arg-type]


def test_pairing_code_can_be_sent_only_through_stdin_and_is_not_in_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: "adb")
    fake_process = FakeProcess()
    client = AdbClient(popen_factory=lambda *_args, **_kwargs: fake_process)

    result = client.run(["pair", "192.168.1.5:37123"], stdin_text="123456\n")

    assert fake_process.received_input == "123456\n"
    assert "123456" not in " ".join(result.command)


def test_nonzero_exit_raises_specific_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: "adb")
    client = AdbClient(
        popen_factory=lambda *_args, **_kwargs: FakeProcess(
            stdout="", stderr="installation failed", returncode=1
        )
    )

    with pytest.raises(AdbCommandError, match="installation failed"):
        client.run(["install", "-r", "app.apk"], device_id="R5CX123")
