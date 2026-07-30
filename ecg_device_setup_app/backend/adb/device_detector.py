"""Parse e identificação do único smartphone USB autorizado."""

from __future__ import annotations

from dataclasses import replace

from backend.adb.adb_client import AdbClient
from backend.adb.models import AdbDeviceRecord, AdbDeviceState
from backend.exceptions import (
    DeviceNotFoundError,
    DeviceUnauthorizedError,
    MultipleDevicesError,
)
from backend.models.device import DeviceInfo, DeviceKind


PHONE_PROPERTIES = {
    "manufacturer": "ro.product.manufacturer",
    "model": "ro.product.model",
    "product_device": "ro.product.device",
    "android_release": "ro.build.version.release",
    "android_sdk": "ro.build.version.sdk",
    "build_display_id": "ro.build.display.id",
}


def parse_adb_devices(output: str) -> list[AdbDeviceRecord]:
    """Interpreta a saída de ``adb devices -l`` sem descartar estados de erro."""

    devices: list[AdbDeviceRecord] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if (
            not line
            or line.startswith("List of devices attached")
            or line.startswith("*")
        ):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, state_text, *attribute_tokens = parts
        attributes: dict[str, str] = {}
        for token in attribute_tokens:
            if ":" not in token:
                continue
            key, value = token.split(":", 1)
            if key:
                attributes[key] = value
        devices.append(
            AdbDeviceRecord(
                serial=serial,
                state=AdbDeviceState.from_text(state_text),
                attributes=attributes,
            )
        )
    return devices


class DeviceDetector:
    def __init__(self, adb_client: AdbClient) -> None:
        self.adb_client = adb_client

    def list_devices(self) -> list[AdbDeviceRecord]:
        result = self.adb_client.run(["devices", "-l"], timeout_seconds=20)
        return parse_adb_devices(result.stdout)

    def detect_phone(self) -> DeviceInfo:
        records = self.list_devices()
        usb_records = [record for record in records if record.is_usb]
        authorized = [
            record
            for record in usb_records
            if record.state is AdbDeviceState.DEVICE
        ]

        if len(authorized) > 1:
            serials = ", ".join(record.serial for record in authorized)
            raise MultipleDevicesError(
                "Mais de um dispositivo USB autorizado foi encontrado "
                f"({serials}). Deixe conectado somente o celular alvo."
            )
        if not authorized:
            unauthorized = [
                record
                for record in usb_records
                if record.state is AdbDeviceState.UNAUTHORIZED
            ]
            if unauthorized:
                raise DeviceUnauthorizedError(
                    "O celular está conectado, mas a depuração USB não foi "
                    "autorizada. Desbloqueie o aparelho e aceite a chave RSA."
                )
            offline = [
                record
                for record in usb_records
                if record.state is AdbDeviceState.OFFLINE
            ]
            if offline:
                raise DeviceNotFoundError(
                    "O celular aparece como offline. Reconecte o cabo USB e "
                    "verifique a depuração."
                )
            raise DeviceNotFoundError(
                "Nenhum celular USB autorizado foi encontrado."
            )

        record = authorized[0]
        values = {
            field: self.adb_client.get_property(property_name, device_id=record.serial)
            for field, property_name in PHONE_PROPERTIES.items()
        }
        device = DeviceInfo(
            serial=record.serial,
            kind=DeviceKind.PHONE,
            transport_id=record.transport_id,
            connection="usb",
            **values,
        )
        if not device.is_galaxy_a56:
            warning = (
                "O modelo identificado não parece ser um Samsung Galaxy A56. "
                "A continuação exigirá confirmação do operador."
            )
            device = replace(device, warnings=(warning,))
        return device
