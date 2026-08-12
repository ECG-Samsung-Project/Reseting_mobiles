"""Página de confirmação final do MVP não destrutivo."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QFormLayout, QLabel, QVBoxLayout, QWidget

from backend.models.device import DeviceInfo
from backend.models.setup_input import SetupInput
from backend.services.preflight_service import PreflightReport


def mask_email(email: str) -> str:
    local, separator, domain = email.partition("@")
    if not separator:
        return email
    visible = local[:2]
    return f"{visible}{'*' * max(3, len(local) - len(visible))}@{domain}"


class ConfirmationStep(QWidget):
    confirmation_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        title = QLabel("Confirmação do operador")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Revise os dados. O botão final apenas encerra este MVP de pré-validação e não modifica o aparelho."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        form = QFormLayout()
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(10)
        self.values: dict[str, QLabel] = {}
        for key, label in (
            ("participant", "Participante"),
            ("kit", "Kit"),
            ("email", "Conta Google"),
            ("phone", "Celular"),
            ("serial", "Serial"),
            ("apks", "APKs validados"),
            ("preflight", "Pré-validação"),
        ):
            value = QLabel("—")
            value.setWordWrap(True)
            self.values[key] = value
            form.addRow(f"{label}:", value)
        layout.addLayout(form)
        self.confirm_checkbox = QCheckBox(
            "Confirmo que os dados, o celular e o kit selecionados estão corretos."
        )
        self.confirm_checkbox.toggled.connect(self.confirmation_changed)
        layout.addWidget(self.confirm_checkbox)
        layout.addStretch(1)

    def update_summary(
        self,
        setup_input: SetupInput,
        phone: DeviceInfo | None,
        report: PreflightReport,
    ) -> None:
        self.values["participant"].setText(setup_input.participant_id)
        self.values["kit"].setText(setup_input.kit_id)
        self.values["email"].setText(mask_email(setup_input.google_email))
        self.values["phone"].setText(phone.model if phone else "Não identificado")
        self.values["serial"].setText(phone.serial if phone else "—")
        apk_check = next((check for check in report.checks if check.id == "apks"), None)
        apk_count = len(apk_check.details) if apk_check and apk_check.details else 0
        self.values["apks"].setText(str(apk_count))
        self.values["preflight"].setText("Aprovada" if report.ready else "Com bloqueios")
        self.confirm_checkbox.setChecked(False)
