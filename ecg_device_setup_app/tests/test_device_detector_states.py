from __future__ import annotations

import pytest

from backend.adb.adb_command import AdbCommandResult
from backend.adb.device_detector import DeviceDetector
from backend.exceptions import DeviceNotFoundError, DeviceUnauthorizedError


class FakeAdbClient:
    def __init__(self, output: str) -> None:
        self.output = output

    def run(self, *_args, **_kwargs) -> AdbCommandResult:
        return AdbCommandResult(
            command=("adb", "devices", "-l"),
            stdout=self.output,
            stderr="",
            return_code=0,
            duration_seconds=0.01,
        )


def test_unauthorized_phone_has_specific_error() -> None:
    detector = DeviceDetector(
        FakeAdbClient(
            "List of devices attached\nRXCY7008ADP unauthorized usb:1-2 model:SM-A566E\n"
        )
    )
    with pytest.raises(DeviceUnauthorizedError, match="autoriza"):
        detector.detect_phone()


def test_offline_phone_has_specific_error() -> None:
    detector = DeviceDetector(
        FakeAdbClient(
            "List of devices attached\nRXCY7008ADP offline usb:1-2 model:SM-A566E\n"
        )
    )
    with pytest.raises(DeviceNotFoundError, match="offline"):
        detector.detect_phone()
