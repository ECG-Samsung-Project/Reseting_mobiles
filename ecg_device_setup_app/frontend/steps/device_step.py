"""Página de detecção e inspeção do celular."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from backend.models.device import DeviceInfo
from frontend.widgets.device_card import DeviceCard


class DeviceStep(QWidget):
    refresh_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        title = QLabel("Celular conectado")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Conecte somente o celular alvo por USB, desbloqueie-o e autorize a depuração quando solicitado."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.card = DeviceCard()
        layout.addWidget(self.card)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.refresh_button = QPushButton("Atualizar dispositivos")
        self.refresh_button.setObjectName("PrimaryButton")
        self.refresh_button.clicked.connect(self.refresh_requested)
        layout.addWidget(self.refresh_button, 0)
        layout.addStretch(1)

    def set_loading(self, loading: bool) -> None:
        self.progress.setVisible(loading)
        self.refresh_button.setDisabled(loading)
        self.refresh_button.setText("Consultando..." if loading else "Atualizar dispositivos")
        if loading:
            self.card.set_loading()

    def set_device(self, device: DeviceInfo) -> None:
        self.card.set_device(device)

    def set_error(self, message: str) -> None:
        self.card.set_error(message)
