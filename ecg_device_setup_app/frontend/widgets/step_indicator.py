"""Indicador lateral das etapas do wizard."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class _StepRow(QFrame):
    def __init__(self, number: int, title: str) -> None:
        super().__init__()
        self.number = number
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 7, 0, 7)
        layout.setSpacing(12)
        self.badge = QLabel(str(number))
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setFixedSize(28, 28)
        self.title = QLabel(title)
        self.title.setWordWrap(True)
        layout.addWidget(self.badge)
        layout.addWidget(self.title, 1)
        self.set_state("pending")

    def set_state(self, state: str) -> None:
        styles = {
            "pending": ("#374151", "#9ca3af", "#9ca3af"),
            "active": ("#2563eb", "#ffffff", "#ffffff"),
            "complete": ("#059669", "#ffffff", "#d1fae5"),
        }
        background, badge_text, label_text = styles[state]
        self.badge.setStyleSheet(
            f"background:{background}; color:{badge_text}; border-radius:14px; font-weight:700;"
        )
        self.title.setStyleSheet(
            f"color:{label_text}; font-weight:{'700' if state == 'active' else '500'};"
        )
        self.badge.setText("✓" if state == "complete" else str(self.number))


class StepIndicator(QWidget):
    def __init__(self, titles: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.rows = [_StepRow(index + 1, title) for index, title in enumerate(titles)]
        for row in self.rows:
            layout.addWidget(row)
        layout.addStretch(1)
        self.set_current(0)

    def set_current(self, index: int) -> None:
        for row_index, row in enumerate(self.rows):
            if row_index < index:
                row.set_state("complete")
            elif row_index == index:
                row.set_state("active")
            else:
                row.set_state("pending")
