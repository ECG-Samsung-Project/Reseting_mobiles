"""Linhas retornadas por ``adb devices -l``."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AdbDeviceState(StrEnum):
    DEVICE = "device"
    UNAUTHORIZED = "unauthorized"
    OFFLINE = "offline"
    RECOVERY = "recovery"
    SIDELOAD = "sideload"
    UNKNOWN = "unknown"

    @classmethod
    def from_text(cls, value: str) -> AdbDeviceState:
        try:
            return cls(value.lower())
        except ValueError:
            return cls.UNKNOWN


@dataclass(frozen=True, slots=True)
class AdbDeviceRecord:
    serial: str
    state: AdbDeviceState
    attributes: dict[str, str] = field(default_factory=dict)

    @property
    def model(self) -> str:
        return self.attributes.get("model", "")

    @property
    def transport_id(self) -> str | None:
        return self.attributes.get("transport_id")

    @property
    def is_usb(self) -> bool:
        if "usb" in self.attributes:
            return True
        serial_lower = self.serial.lower()
        return ":" not in self.serial and not serial_lower.startswith("emulator-")
