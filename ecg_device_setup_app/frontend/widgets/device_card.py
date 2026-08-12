"""Cartão de apresentação do celular detectado."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QFrame, QLabel, QVBoxLayout, QWidget

from backend.models.device import DeviceInfo


class DeviceCard(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DeviceCard")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(10)
        self.status_label = QLabel("Nenhum celular consultado")
        self.status_label.setObjectName("SectionTitle")
        outer.addWidget(self.status_label)
        form = QFormLayout()
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(9)
        self.values: dict[str, QLabel] = {}
        for key, label in (
            ("model", "Modelo"),
            ("manufacturer", "Fabricante"),
            ("serial", "Serial"),
            ("android", "Android"),
            ("build", "Build"),
            ("transport", "Transporte"),
        ):
            value = QLabel("—")
            value.setTextInteractionFlags(value.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse)
            self.values[key] = value
            form.addRow(f"{label}:", value)
        outer.addLayout(form)
        self.warning_label = QLabel("")
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet("color:#b45309;")
        self.warning_label.hide()
        outer.addWidget(self.warning_label)

    def set_loading(self) -> None:
        self.status_label.setText("Consultando ADB...")
        self.status_label.setStyleSheet("color:#2563eb;")

    def set_device(self, device: DeviceInfo) -> None:
        self.status_label.setText("Celular autorizado e identificado")
        self.status_label.setStyleSheet("color:#047857;")
        self.values["model"].setText(device.model or "Desconhecido")
        self.values["manufacturer"].setText(device.manufacturer or "Desconhecido")
        self.values["serial"].setText(device.serial)
        android = device.android_release or "Desconhecido"
        if device.android_sdk:
            android += f" (SDK {device.android_sdk})"
        self.values["android"].setText(android)
        self.values["build"].setText(device.build_display_id or "—")
        self.values["transport"].setText(device.transport_id or device.connection)
        if device.warnings:
            self.warning_label.setStyleSheet("color:#b45309;")
            self.warning_label.setText(device.warnings[0])
            self.warning_label.show()
        else:
            self.warning_label.hide()

    def set_error(self, message: str) -> None:
        self.status_label.setText("Celular indisponível")
        self.status_label.setStyleSheet("color:#b91c1c;")
        for value in self.values.values():
            value.setText("—")
        self.warning_label.setText(message)
        self.warning_label.setStyleSheet("color:#b91c1c;")
        self.warning_label.show()
