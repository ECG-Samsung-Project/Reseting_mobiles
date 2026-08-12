"""Painel recolhível de logs operacionais seguros."""

from datetime import datetime

from PySide6.QtWidgets import QFrame, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget


class LogPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        self.toggle = QPushButton("Logs operacionais")
        self.toggle.setCheckable(True)
        self.toggle.setChecked(False)
        self.toggle.setObjectName("InlineButton")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumHeight(150)
        self.output.hide()
        self.toggle.toggled.connect(self.output.setVisible)
        layout.addWidget(self.toggle)
        layout.addWidget(self.output)

    def append_message(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.output.appendPlainText(f"[{timestamp}] {message}")
