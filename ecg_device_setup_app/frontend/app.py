"""Inicialização do aplicativo PySide6."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from backend.logging_config import SensitiveDataFilter, configure_session_logging
from frontend.controllers.setup_controller import SetupController
from frontend.main_window import MainWindow
from frontend.theme import APP_STYLESHEET


def run_app(project_root: Path) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("ECG Device Setup")
    app.setOrganizationName("ECG")
    app.setStyleSheet(APP_STYLESHEET)

    sensitive_filter: SensitiveDataFilter | None = None
    try:
        sensitive_filter = configure_session_logging(
            project_root / "data" / "logs" / "ecg_device_setup.log"
        )
    except OSError:
        logging.basicConfig(level=logging.INFO)

    controller = SetupController(project_root, sensitive_filter=sensitive_filter)
    window = MainWindow(project_root, controller=controller)
    window.show()
    try:
        return app.exec()
    except Exception as exc:
        QMessageBox.critical(None, "Erro inesperado", f"A interface foi interrompida: {exc}")
        return 1
