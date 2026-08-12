"""Estado e coordenação do wizard, sem regras visuais."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from PySide6.QtCore import QObject, QThreadPool, Signal

from backend.adb.adb_client import AdbClient
from backend.adb.device_detector import DeviceDetector
from backend.logging_config import SensitiveDataFilter, redact_sensitive_text
from backend.models.device import DeviceInfo
from backend.models.setup_input import SetupInput
from backend.services.configuration_service import AppSettings
from backend.services.preflight_service import PreflightReport, PreflightService
from frontend.workers import CallableWorker

LOGGER = logging.getLogger(__name__)

DeviceLoader = Callable[[], DeviceInfo]
PreflightRunner = Callable[[SetupInput], PreflightReport]


class SetupController(QObject):
    operation_changed = Signal(object)
    device_loading_changed = Signal(bool)
    device_changed = Signal(object)
    device_error = Signal(str)
    preflight_loading_changed = Signal(bool)
    preflight_changed = Signal(object)
    preflight_error = Signal(str)
    log_message = Signal(str)

    def __init__(
        self,
        project_root: Path,
        *,
        thread_pool: QThreadPool | None = None,
        device_loader: DeviceLoader | None = None,
        preflight_runner: PreflightRunner | None = None,
        sensitive_filter: SensitiveDataFilter | None = None,
    ) -> None:
        super().__init__()
        self.project_root = project_root.resolve()
        self.thread_pool = thread_pool or QThreadPool.globalInstance()
        self._device_loader = device_loader or self._default_device_loader
        self._preflight_runner = preflight_runner or self._default_preflight_runner
        self.sensitive_filter = sensitive_filter

        self.setup_input: SetupInput | None = None
        self.phone: DeviceInfo | None = None
        self.preflight_report: PreflightReport | None = None
        self.device_loading = False
        self.preflight_loading = False
        self._workers: set[CallableWorker] = set()

    def set_operation_data(
        self,
        participant_id: str,
        kit_id: str,
        google_email: str,
        google_password: str,
    ) -> tuple[bool, str]:
        try:
            setup_input = SetupInput(
                participant_id=participant_id,
                kit_id=kit_id,
                google_email=google_email,
                google_password=google_password,
            )
        except ValidationError as exc:
            error = exc.errors(include_url=False)[0]["msg"]
            message = str(error).removeprefix("Value error, ")
            return False, message

        if self.sensitive_filter is not None:
            self.sensitive_filter.register_secret(google_password)
        self.setup_input = setup_input
        self.preflight_report = None
        self.operation_changed.emit(setup_input.persisted_identity())
        self._log("Dados da operação validados.")
        return True, ""

    def refresh_device(self) -> None:
        if self.device_loading:
            return
        self.device_loading = True
        self.device_loading_changed.emit(True)
        self._log("Consultando o celular conectado via ADB...")
        worker = CallableWorker(self._device_loader)
        self._keep_worker(worker)
        worker.signals.result.connect(self._on_device_result)
        worker.signals.error.connect(self._on_device_error)
        worker.signals.finished.connect(self._on_device_finished)
        self.thread_pool.start(worker)

    def run_preflight(self) -> None:
        if self.preflight_loading:
            return
        if self.setup_input is None:
            self.preflight_error.emit("Informe e valide os dados da operação primeiro.")
            return
        self.preflight_loading = True
        self.preflight_loading_changed.emit(True)
        self._log("Executando pré-validação não destrutiva...")
        worker = CallableWorker(lambda: self._preflight_runner(self.setup_input))
        self._keep_worker(worker)
        worker.signals.result.connect(self._on_preflight_result)
        worker.signals.error.connect(self._on_preflight_error)
        worker.signals.finished.connect(self._on_preflight_finished)
        self.thread_pool.start(worker)

    def _default_device_loader(self) -> DeviceInfo:
        settings = AppSettings.from_yaml(self.project_root / "config" / "settings.yaml")
        adb_client = AdbClient(
            settings.adb_executable,
            default_timeout_seconds=settings.adb_default_timeout_seconds,
        )
        return DeviceDetector(adb_client).detect_phone()

    def _default_preflight_runner(self, setup_input: SetupInput) -> PreflightReport:
        return PreflightService(self.project_root).run(setup_input)

    def _on_device_result(self, result: Any) -> None:
        if not isinstance(result, DeviceInfo):
            self._on_device_error("O detector retornou um dispositivo inválido.")
            return
        self.phone = result
        self.preflight_report = None
        self.device_changed.emit(result)
        self._log(f"Celular {result.model or result.serial} identificado.")

    def _on_device_error(self, message: str) -> None:
        self.phone = None
        self.preflight_report = None
        self.device_error.emit(message)
        self._log(f"Falha na detecção do celular: {message}")

    def _on_device_finished(self) -> None:
        self.device_loading = False
        self.device_loading_changed.emit(False)
        self._drop_finished_workers()

    def _on_preflight_result(self, result: Any) -> None:
        if not isinstance(result, PreflightReport):
            self._on_preflight_error("O serviço retornou um relatório inválido.")
            return
        self.preflight_report = result
        if result.phone is not None:
            self.phone = result.phone
            self.device_changed.emit(result.phone)
        self.preflight_changed.emit(result)
        status = "aprovada" if result.ready else "concluída com bloqueios"
        self._log(f"Pré-validação {status}.")

    def _on_preflight_error(self, message: str) -> None:
        self.preflight_report = None
        self.preflight_error.emit(message)
        self._log(f"Falha ao executar pré-validação: {message}")

    def _on_preflight_finished(self) -> None:
        self.preflight_loading = False
        self.preflight_loading_changed.emit(False)
        self._drop_finished_workers()

    def _keep_worker(self, worker: CallableWorker) -> None:
        self._workers.add(worker)

    def _drop_finished_workers(self) -> None:
        self._workers = {worker for worker in self._workers if not worker.autoDelete()}
        # QRunnable não informa estado com precisão. Manter a coleção limitada é
        # suficiente; os objetos já concluídos podem ser liberados após os sinais.
        if len(self._workers) > 8:
            self._workers.clear()

    def _log(self, message: str) -> None:
        secrets: tuple[str, ...] = ()
        if self.setup_input is not None:
            secrets = (self.setup_input.google_password.get_secret_value(),)
        safe_message = redact_sensitive_text(message, secrets)
        LOGGER.info(safe_message)
        self.log_message.emit(safe_message)
