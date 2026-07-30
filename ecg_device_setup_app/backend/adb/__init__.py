"""Acesso centralizado e seguro ao Android Debug Bridge."""

from backend.adb.adb_client import AdbClient
from backend.adb.adb_command import AdbCommandResult
from backend.adb.device_detector import DeviceDetector, parse_adb_devices
from backend.adb.models import AdbDeviceRecord, AdbDeviceState

__all__ = [
    "AdbClient",
    "AdbCommandResult",
    "AdbDeviceRecord",
    "AdbDeviceState",
    "DeviceDetector",
    "parse_adb_devices",
]
