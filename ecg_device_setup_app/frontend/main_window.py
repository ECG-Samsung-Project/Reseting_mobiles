"""Janela principal do wizard ECG Device Setup."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from frontend.controllers.setup_controller import SetupController
from frontend.steps.confirmation_step import ConfirmationStep
from frontend.steps.device_step import DeviceStep
from frontend.steps.operation_step import OperationStep
from frontend.steps.preflight_step import PreflightStep
from frontend.widgets.log_panel import LogPanel
from frontend.widgets.step_indicator import StepIndicator

LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    STEP_TITLES = ["Dados da operação", "Celular", "Pré-validação", "Confirmação"]

    def __init__(
        self,
        project_root: Path,
        *,
        controller: SetupController | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("ECG Device Setup")
        self.resize(1080, 720)
        self.setMinimumSize(900, 620)
        self.controller = controller or SetupController(project_root)
        self.current_step = 0
        self._build_ui()
        self._connect_signals()
        self._set_step(0)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(255)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(24, 28, 24, 24)
        sidebar_layout.setSpacing(18)
        brand = QLabel("ECG Device Setup")
        brand.setObjectName("BrandTitle")
        subtitle = QLabel("Preparação segura de kits")
        subtitle.setObjectName("BrandSubtitle")
        sidebar_layout.addWidget(brand)
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addSpacing(16)
        self.step_indicator = StepIndicator(self.STEP_TITLES)
        sidebar_layout.addWidget(self.step_indicator, 1)
        version = QLabel("MVP de pré-validação\nNenhuma ação destrutiva")
        version.setObjectName("BrandSubtitle")
        version.setWordWrap(True)
        sidebar_layout.addWidget(version)
        root_layout.addWidget(sidebar)

        main_area = QWidget()
        main_layout = QVBoxLayout(main_area)
        main_layout.setContentsMargins(30, 26, 30, 24)
        main_layout.setSpacing(14)
        content_card = QFrame()
        content_card.setObjectName("ContentCard")
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(28, 26, 28, 22)
        content_layout.setSpacing(16)

        self.stack = QStackedWidget()
        self.operation_step = OperationStep()
        self.device_step = DeviceStep()
        self.preflight_step = PreflightStep()
        self.confirmation_step = ConfirmationStep()
        for page in (
            self.operation_step,
            self.device_step,
            self.preflight_step,
            self.confirmation_step,
        ):
            self.stack.addWidget(page)
        content_layout.addWidget(self.stack, 1)

        self.log_panel = LogPanel()
        content_layout.addWidget(self.log_panel)

        navigation = QHBoxLayout()
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setObjectName("DangerButton")
        self.back_button = QPushButton("Voltar")
        self.next_button = QPushButton("Continuar")
        self.next_button.setObjectName("PrimaryButton")
        navigation.addWidget(self.cancel_button)
        navigation.addStretch(1)
        navigation.addWidget(self.back_button)
        navigation.addWidget(self.next_button)
        content_layout.addLayout(navigation)
        main_layout.addWidget(content_card, 1)
        root_layout.addWidget(main_area, 1)

    def _connect_signals(self) -> None:
        self.cancel_button.clicked.connect(self.close)
        self.back_button.clicked.connect(self._go_back)
        # PySide6 6.11 passa o estado checked no sinal clicked(bool). O slot aceita
        # explicitamente esse argumento, evitando que a navegação dependa da forma
        # como a versão do binding descarta argumentos excedentes.
        self.next_button.clicked.connect(self._go_next)
        self.stack.currentChanged.connect(self._on_stack_changed)

        self.operation_step.validity_changed.connect(
            lambda _valid: self._update_navigation()
        )
        self.device_step.refresh_requested.connect(self.controller.refresh_device)
        self.preflight_step.run_requested.connect(self.controller.run_preflight)
        self.confirmation_step.confirmation_changed.connect(
            lambda _checked: self._update_navigation()
        )

        self.controller.device_loading_changed.connect(self.device_step.set_loading)
        self.controller.device_changed.connect(self._on_device_changed)
        self.controller.device_error.connect(self._on_device_error)
        self.controller.preflight_loading_changed.connect(
            self.preflight_step.set_loading
        )
        self.controller.preflight_changed.connect(self._on_preflight_changed)
        self.controller.preflight_error.connect(self._on_preflight_error)
        self.controller.log_message.connect(self.log_panel.append_message)

    @Slot(bool)
    def _go_next(self, _checked: bool = False) -> None:
        """Avança usando a página realmente exibida como fonte de verdade."""
        try:
            step = self.stack.currentIndex()

            if step == 0:
                success, message = self.controller.set_operation_data(
                    *self.operation_step.values()
                )
                if not success:
                    self.operation_step.show_error(message)
                    return
                self._set_step(1)
                if self.controller.phone is None:
                    self.controller.refresh_device()
                return

            if step == 1:
                if self.controller.device_loading:
                    return
                if self.controller.phone is None:
                    QMessageBox.warning(
                        self,
                        "Celular necessário",
                        "Identifique um celular autorizado antes de continuar.",
                    )
                    return
                self.controller.log_message.emit("Abrindo a etapa de pré-validação.")
                self._set_step(2)
                return

            if step == 2:
                report = self.controller.preflight_report
                if report is None or not report.ready:
                    QMessageBox.warning(
                        self,
                        "Pré-validação necessária",
                        "Execute a pré-validação e corrija os bloqueios antes de continuar.",
                    )
                    return
                setup_input = self.controller.setup_input
                if setup_input is None:
                    QMessageBox.warning(
                        self,
                        "Dados ausentes",
                        "Os dados da operação não estão mais disponíveis. Volte à primeira etapa.",
                    )
                    return
                self.confirmation_step.update_summary(
                    setup_input,
                    self.controller.phone,
                    report,
                )
                self._set_step(3)
                return

            if not self.confirmation_step.confirm_checkbox.isChecked():
                return
            QMessageBox.information(
                self,
                "Pré-validação concluída",
                "A pré-validação foi concluída. As rotinas de backup, limpeza, "
                "instalação e configuração serão adicionadas nas próximas etapas.",
            )
        except Exception as exc:
            LOGGER.exception("Falha ao avançar no wizard")
            QMessageBox.critical(
                self,
                "Falha de navegação",
                "Não foi possível abrir a próxima etapa.\n\n"
                f"Detalhe técnico: {exc}",
            )

    @Slot(bool)
    def _go_back(self, _checked: bool = False) -> None:
        step = self.stack.currentIndex()
        if step > 0:
            self._set_step(step - 1)

    def _set_step(self, index: int) -> None:
        if not 0 <= index < self.stack.count():
            raise ValueError(f"Etapa inválida: {index}")
        self.stack.setCurrentIndex(index)
        # currentChanged normalmente sincroniza isto. A atribuição explícita torna
        # o método determinístico também em testes e chamadas antes do event loop.
        self.current_step = index
        self.step_indicator.set_current(index)
        self._update_navigation()

    @Slot(int)
    def _on_stack_changed(self, index: int) -> None:
        self.current_step = index
        self.step_indicator.set_current(index)
        self._update_navigation()

    def _update_navigation(self) -> None:
        step = self.stack.currentIndex()
        self.current_step = step
        self.back_button.setEnabled(step > 0)

        if step == 0:
            self.next_button.setText("Continuar")
            self.next_button.setEnabled(self.operation_step.is_complete())
        elif step == 1:
            self.next_button.setText("Ir para pré-validação")
            self.next_button.setEnabled(
                self.controller.phone is not None
                and not self.controller.device_loading
            )
        elif step == 2:
            self.next_button.setText("Ir para confirmação")
            report = self.controller.preflight_report
            self.next_button.setEnabled(
                bool(
                    report
                    and report.ready
                    and not self.controller.preflight_loading
                )
            )
        else:
            self.next_button.setText("Preparar configuração")
            self.next_button.setEnabled(
                self.confirmation_step.confirm_checkbox.isChecked()
            )

    def _on_device_changed(self, device: object) -> None:
        self.device_step.set_device(device)  # sinal tipado pelo controlador
        self._update_navigation()

    def _on_device_error(self, message: str) -> None:
        self.device_step.set_error(message)
        self._update_navigation()

    def _on_preflight_changed(self, report: object) -> None:
        self.preflight_step.set_report(report)  # sinal tipado pelo controlador
        self._update_navigation()

    def _on_preflight_error(self, message: str) -> None:
        self.preflight_step.set_error(message)
        self._update_navigation()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.controller.device_loading or self.controller.preflight_loading:
            answer = QMessageBox.question(
                self,
                "Operação em andamento",
                "Existe uma verificação em andamento. Fechar a aplicação mesmo assim?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        event.accept()