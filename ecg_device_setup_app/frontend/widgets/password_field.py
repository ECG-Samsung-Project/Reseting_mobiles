"""Campo de senha com alternância de visibilidade."""

from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget


class PasswordField(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.line_edit = QLineEdit()
        self.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.line_edit.setPlaceholderText("Senha da nova conta Google")
        self.toggle_button = QPushButton("Mostrar")
        self.toggle_button.setObjectName("InlineButton")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setAccessibleName("Mostrar ou ocultar senha")
        self.toggle_button.toggled.connect(self._toggle_visibility)
        layout.addWidget(self.line_edit, 1)
        layout.addWidget(self.toggle_button)

    def text(self) -> str:
        return self.line_edit.text()

    def clear(self) -> None:
        self.line_edit.clear()

    def _toggle_visibility(self, visible: bool) -> None:
        self.line_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        )
        self.toggle_button.setText("Ocultar" if visible else "Mostrar")
