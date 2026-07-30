"""Modelos de dispositivos Android identificados pelo ADB."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class DeviceKind(StrEnum):
    PHONE = "phone"
    WATCH = "watch"


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    serial: str
    kind: DeviceKind
    manufacturer: str = ""
    model: str = ""
    product_device: str = ""
    android_release: str = ""
    android_sdk: str = ""
    build_display_id: str = ""
    transport_id: str | None = None
    connection: str = "usb"
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_galaxy_a56(self) -> bool:
        identity = f"{self.manufacturer} {self.model} {self.product_device}".upper()
        return (
            "A56" in identity
            or "SM-A566" in identity
            or ("SAMSUNG" in identity and "A566" in identity)
        )

    def to_dict(self) -> dict[str, str | list[str] | None]:
        return {
            "serial": self.serial,
            "kind": self.kind.value,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "product_device": self.product_device,
            "android_release": self.android_release,
            "android_sdk": self.android_sdk,
            "build_display_id": self.build_display_id,
            "transport_id": self.transport_id,
            "connection": self.connection,
            "warnings": list(self.warnings),
        }
