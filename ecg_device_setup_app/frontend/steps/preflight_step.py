"""Página do relatório de pré-validação."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from backend.services.preflight_service import PreflightReport
from frontend.widgets.status_card import ProgressStatusCard, StatusCard


class PreflightStep(QWidget):
    run_requested = Signal()
    EXPECTED_CHECKS = (
        "Dados da operação",
        "Configurações",
        "APKs obrigatórios",
        "Pastas de dados",
        "Espaço em disco",
        "Android Debug Bridge",
        "Celular USB",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        title = QLabel("Pré-validação")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Verifique a infraestrutura antes de qualquer backup, limpeza ou instalação. Esta etapa não altera o celular."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.summary_label = QLabel("A pré-validação ainda não foi executada.")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 4, 0)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch(1)
        self._render_progress_cards(running=False)
        self.scroll.setWidget(self.cards_container)
        layout.addWidget(self.scroll, 1)
        self.run_button = QPushButton("Executar pré-validação")
        self.run_button.setObjectName("PrimaryButton")
        self.run_button.clicked.connect(self.run_requested)
        layout.addWidget(self.run_button, 0)

    def set_loading(self, loading: bool) -> None:
        self.progress.setVisible(loading)
        self.run_button.setDisabled(loading)
        self.run_button.setText("Validando..." if loading else "Executar pré-validação")
        if loading:
            self.summary_label.setText("Executando verificações...")
            self._render_progress_cards(running=True)


    def _clear_cards(self) -> None:
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _render_progress_cards(self, *, running: bool) -> None:
        self._clear_cards()
        for label in self.EXPECTED_CHECKS:
            self.cards_layout.insertWidget(
                self.cards_layout.count() - 1,
                ProgressStatusCard(label, running=running),
            )

    def set_report(self, report: PreflightReport) -> None:
        self._clear_cards()
        for check in report.checks:
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, StatusCard(check))
        if report.ready:
            self.summary_label.setText("Pré-validação aprovada. O operador pode revisar e confirmar os dados.")
            self.summary_label.setStyleSheet("color:#047857; font-weight:700;")
        else:
            self.summary_label.setText("Existem bloqueios. Corrija os itens em vermelho e execute novamente.")
            self.summary_label.setStyleSheet("color:#b91c1c; font-weight:700;")

    def set_error(self, message: str) -> None:
        self.summary_label.setText(message)
        self.summary_label.setStyleSheet("color:#b91c1c; font-weight:700;")
