from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt

from backend.models.device import DeviceInfo, DeviceKind
from backend.services.preflight_service import (
    PreflightCheck,
    PreflightCheckStatus,
    PreflightReport,
)
from frontend.controllers.setup_controller import SetupController
from frontend.main_window import MainWindow


class ImmediateThreadPool:
    def start(self, worker) -> None:
        worker.run()


def make_phone() -> DeviceInfo:
    return DeviceInfo(
        serial="RXCY7008ADP",
        kind=DeviceKind.PHONE,
        manufacturer="Samsung",
        model="SM-A566E",
        product_device="a56x",
        android_release="16",
        android_sdk="36",
        build_display_id="BP2A",
    )


def make_report(phone: DeviceInfo) -> PreflightReport:
    checks = (
        PreflightCheck(
            id="setup_input",
            label="Dados da operação",
            status=PreflightCheckStatus.PASSED,
            message="Dados validados.",
        ),
        PreflightCheck(
            id="apks",
            label="APKs obrigatórios",
            status=PreflightCheckStatus.PASSED,
            message="5 APKs validados.",
            details={str(index): {} for index in range(5)},
        ),
        PreflightCheck(
            id="phone",
            label="Celular USB",
            status=PreflightCheckStatus.PASSED,
            message="Celular identificado.",
        ),
    )
    return PreflightReport(checks=checks, summary={}, phone=phone, adb_version="ADB")


def build_window(qtbot, tmp_path: Path) -> MainWindow:
    phone = make_phone()
    controller = SetupController(
        tmp_path,
        thread_pool=ImmediateThreadPool(),
        device_loader=lambda: phone,
        preflight_runner=lambda _setup: make_report(phone),
    )
    window = MainWindow(tmp_path, controller=controller)
    qtbot.addWidget(window)
    window.show()
    return window


def fill_operation(window: MainWindow, *, email: str = "conta@gmail.com") -> None:
    window.operation_step.participant_edit.setText("ABC-12-2345")
    window.operation_step.kit_edit.setText("12")
    window.operation_step.email_edit.setText(email)
    window.operation_step.password_field.line_edit.setText("senha-temporaria")


def test_continue_is_blocked_for_invalid_input(qtbot, tmp_path: Path) -> None:
    window = build_window(qtbot, tmp_path)
    fill_operation(window, email="email-invalido")
    assert not window.next_button.isEnabled()

    window.operation_step.email_edit.setText("conta@gmail.com")
    assert window.next_button.isEnabled()


def test_wizard_shows_device_and_preflight(qtbot, tmp_path: Path) -> None:
    window = build_window(qtbot, tmp_path)
    fill_operation(window)

    qtbot.mouseClick(window.next_button, Qt.MouseButton.LeftButton)
    assert window.current_step == 1
    assert window.controller.phone is not None
    assert "SM-A566E" in window.device_step.card.values["model"].text()

    qtbot.mouseClick(window.next_button, Qt.MouseButton.LeftButton)
    assert window.current_step == 2
    qtbot.mouseClick(
        window.preflight_step.run_button,
        Qt.MouseButton.LeftButton,
    )
    assert window.controller.preflight_report is not None
    assert window.next_button.isEnabled()
