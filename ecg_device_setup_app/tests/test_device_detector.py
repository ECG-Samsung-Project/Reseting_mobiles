from __future__ import annotations

import pytest

from backend.adb.adb_command import AdbCommandResult
from backend.adb.device_detector import DeviceDetector, parse_adb_devices
from backend.adb.models import AdbDeviceState
from backend.exceptions import DeviceUnauthorizedError, MultipleDevicesError


def command_result(stdout: str) -> AdbCommandResult:
    return AdbCommandResult(
        command=("adb", "devices", "-l"),
        stdout=stdout,
        stderr="",
        return_code=0,
        duration_seconds=0.01,
    )


class FakeAdbClient:
    def __init__(self, devices_output: str, properties: dict[str, str] | None = None):
        self.devices_output = devices_output
        self.properties = properties or {}
        self.property_calls: list[tuple[str, str]] = []

    def run(self, arguments: list[str], **_kwargs: object) -> AdbCommandResult:
        assert arguments == ["devices", "-l"]
        return command_result(self.devices_output)

    def get_property(
        self, property_name: str, *, device_id: str, timeout_seconds: float = 15
    ) -> str:
        del timeout_seconds
        self.property_calls.append((property_name, device_id))
        return self.properties.get(property_name, "")


def test_parse_adb_devices_long_format() -> None:
    output = """List of devices attached
R5CX123 device usb:1-2 product:a56x model:SM-A566B device:a56x transport_id:4
192.168.1.9:5555 offline product:e2s model:SM-L320 device:e2s transport_id:8
R5CX999 unauthorized usb:1-3 transport_id:9
"""

    devices = parse_adb_devices(output)

    assert len(devices) == 3
    assert devices[0].serial == "R5CX123"
    assert devices[0].state is AdbDeviceState.DEVICE
    assert devices[0].model == "SM-A566B"
    assert devices[0].is_usb
    assert not devices[1].is_usb
    assert devices[2].state is AdbDeviceState.UNAUTHORIZED


def test_authorized_phone_collects_required_properties() -> None:
    client = FakeAdbClient(
        "R5CX123 device usb:1-2 model:SM-A566B transport_id:4",
        {
            "ro.product.manufacturer": "Samsung",
            "ro.product.model": "SM-A566B",
            "ro.product.device": "a56x",
            "ro.build.version.release": "16",
            "ro.build.version.sdk": "36",
            "ro.build.display.id": "BUILD123",
        },
    )

    phone = DeviceDetector(client).detect_phone()  # type: ignore[arg-type]

    assert phone.serial == "R5CX123"
    assert phone.model == "SM-A566B"
    assert phone.is_galaxy_a56
    assert not phone.warnings
    assert {device_id for _, device_id in client.property_calls} == {"R5CX123"}
    assert len(client.property_calls) == 6


def test_unauthorized_phone_has_specific_instruction() -> None:
    client = FakeAdbClient("R5CX123 unauthorized usb:1-2 transport_id:4")

    with pytest.raises(DeviceUnauthorizedError, match="chave RSA"):
        DeviceDetector(client).detect_phone()  # type: ignore[arg-type]


def test_multiple_authorized_usb_devices_are_rejected() -> None:
    client = FakeAdbClient(
        """R5CX123 device usb:1-2 transport_id:4
R5CX456 device usb:1-3 transport_id:5
"""
    )

    with pytest.raises(MultipleDevicesError, match="R5CX123, R5CX456"):
        DeviceDetector(client).detect_phone()  # type: ignore[arg-type]


def test_network_watch_does_not_count_as_usb_phone() -> None:
    client = FakeAdbClient(
        """R5CX123 device usb:1-2 model:SM-A566B transport_id:4
192.168.1.9:5555 device product:e2s model:SM-L320 transport_id:8
""",
        {
            "ro.product.manufacturer": "Samsung",
            "ro.product.model": "SM-A566B",
            "ro.product.device": "a56x",
        },
    )

    phone = DeviceDetector(client).detect_phone()  # type: ignore[arg-type]

    assert phone.serial == "R5CX123"
