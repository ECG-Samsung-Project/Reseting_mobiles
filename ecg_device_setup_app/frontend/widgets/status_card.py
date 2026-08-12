"""Cartão visual para um item do relatório de pré-validação."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from backend.services.preflight_service import PreflightCheck, PreflightCheckStatus


class StatusCard(QFrame):
    def __init__(self, check: PreflightCheck, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatusCard")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)
        icon = QLabel()
        icon.setFixedSize(26, 26)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content = QVBoxLayout()
        content.setSpacing(3)
        title = QLabel(check.label)
        title.setStyleSheet("font-weight:700;")
        message = QLabel(check.message)
        message.setWordWrap(True)
        message.setObjectName("MutedLabel")
        content.addWidget(title)
        content.addWidget(message)
        layout.addWidget(icon)
        layout.addLayout(content, 1)
        mapping = {
            PreflightCheckStatus.PASSED: ("✓", "#059669", "#ecfdf5"),
            PreflightCheckStatus.WARNING: ("!", "#d97706", "#fffbeb"),
            PreflightCheckStatus.FAILED: ("×", "#dc2626", "#fef2f2"),
        }
        text, color, background = mapping[check.status]
        icon.setText(text)
        icon.setStyleSheet(
            f"color:white; background:{color}; border-radius:13px; font-weight:800;"
        )
        self.setStyleSheet(
            f"QFrame#StatusCard {{background:{background}; border:1px solid {color}33; border-radius:9px;}}"
        )


class ProgressStatusCard(QFrame):
    """Cartão temporário para estados aguardando ou executando."""

    def __init__(
        self,
        label: str,
        *,
        running: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("StatusCard")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)
        icon = QLabel("…" if running else "·")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(26, 26)
        icon.setStyleSheet(
            "color:white; background:#64748b; border-radius:13px; font-weight:800;"
        )
        content = QVBoxLayout()
        content.setSpacing(3)
        title = QLabel(label)
        title.setStyleSheet("font-weight:700;")
        message = QLabel("Executando verificação..." if running else "Aguardando execução")
        message.setObjectName("MutedLabel")
        content.addWidget(title)
        content.addWidget(message)
        layout.addWidget(icon)
        layout.addLayout(content, 1)
