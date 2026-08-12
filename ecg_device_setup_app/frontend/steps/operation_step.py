"""Página de dados da operação."""

from PySide6.QtCore import Signal
from pydantic import ValidationError
from PySide6.QtWidgets import QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from backend.models.setup_input import SetupInput

from frontend.widgets.password_field import PasswordField


class OperationStep(QWidget):
    validity_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        title = QLabel("Dados da operação")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Informe o participante, o kit e a nova conta Google que serão usados nesta configuração."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setVerticalSpacing(14)
        form.setHorizontalSpacing(24)
        self.participant_edit = QLineEdit()
        self.participant_edit.setPlaceholderText("Ex.: ABC-12-2345")
        self.kit_edit = QLineEdit()
        self.kit_edit.setPlaceholderText("Ex.: 12")
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("conta@gmail.com")
        self.password_field = PasswordField()
        form.addRow("Participante:", self.participant_edit)
        form.addRow("Kit:", self.kit_edit)
        form.addRow("E-mail Google:", self.email_edit)
        form.addRow("Senha Google:", self.password_field)
        layout.addLayout(form)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color:#b91c1c;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)
        note = QLabel(
            "A senha fica somente em memória durante a execução e não será gravada em relatórios ou logs."
        )
        note.setObjectName("MutedLabel")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        for field in (
            self.participant_edit,
            self.kit_edit,
            self.email_edit,
            self.password_field.line_edit,
        ):
            field.textChanged.connect(self._emit_validity)

    def values(self) -> tuple[str, str, str, str]:
        return (
            self.participant_edit.text(),
            self.kit_edit.text(),
            self.email_edit.text(),
            self.password_field.text(),
        )

    def show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setVisible(bool(message))

    def is_complete(self) -> bool:
        values = self.values()
        if not all(value.strip() for value in values):
            return False
        try:
            SetupInput(
                participant_id=values[0],
                kit_id=values[1],
                google_email=values[2],
                google_password=values[3],
            )
        except ValidationError:
            return False
        return True

    def _emit_validity(self) -> None:
        self.show_error("")
        self.validity_changed.emit(self.is_complete())
