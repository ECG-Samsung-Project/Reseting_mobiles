"""Pré-validação completa antes de qualquer ação operacional."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from backend.adb.adb_client import AdbClient
from backend.adb.device_detector import DeviceDetector
from backend.exceptions import EcgDeviceSetupError
from backend.models.device import DeviceInfo
from backend.models.setup_input import SetupInput
from backend.services.apk_service import ApkService
from backend.services.configuration_service import AppSettings


class PreflightCheckStatus(StrEnum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class PreflightCheck:
    id: str
    label: str
    status: PreflightCheckStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PreflightReport:
    checks: tuple[PreflightCheck, ...]
    summary: dict[str, Any]
    phone: DeviceInfo | None = None
    adb_version: str | None = None

    @property
    def ready(self) -> bool:
        return all(
            check.status is not PreflightCheckStatus.FAILED
            for check in self.checks
        )

    @property
    def failures(self) -> tuple[PreflightCheck, ...]:
        return tuple(
            check
            for check in self.checks
            if check.status is PreflightCheckStatus.FAILED
        )


class PreflightService:
    WRITABLE_DATA_FOLDERS = ("backups", "sessions", "reports", "logs")

    def __init__(
        self,
        project_root: Path,
        *,
        adb_client: AdbClient | None = None,
        settings_path: Path | None = None,
        applications_path: Path | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.settings_path = (
            settings_path or self.project_root / "config" / "settings.yaml"
        )
        self.applications_path = (
            applications_path
            or self.project_root / "config" / "applications.yaml"
        )
        self._provided_adb_client = adb_client

    def run(self, setup_input: SetupInput) -> PreflightReport:
        checks: list[PreflightCheck] = [
            PreflightCheck(
                id="setup_input",
                label="Dados da operação",
                status=PreflightCheckStatus.PASSED,
                message="Participante, kit e e-mail foram validados.",
                details=setup_input.persisted_identity(),
            )
        ]

        settings: AppSettings | None = None
        try:
            settings = AppSettings.from_yaml(self.settings_path)
            checks.append(
                PreflightCheck(
                    id="settings",
                    label="Configurações",
                    status=PreflightCheckStatus.PASSED,
                    message="settings.yaml carregado com sucesso.",
                )
            )
        except EcgDeviceSetupError as exc:
            checks.append(self._failed("settings", "Configurações", str(exc)))

        checks.append(self._check_apks())
        checks.extend(self._check_writable_folders())
        checks.append(
            self._check_disk_space(
                settings.minimum_free_space_bytes if settings else 5 * 1024**3
            )
        )

        adb_client = self._provided_adb_client
        if adb_client is None and settings is not None:
            adb_client = AdbClient(
                settings.adb_executable,
                default_timeout_seconds=settings.adb_default_timeout_seconds,
            )

        phone: DeviceInfo | None = None
        adb_version: str | None = None
        if adb_client is None:
            checks.append(
                self._failed(
                    "adb",
                    "Android Debug Bridge",
                    "O cliente ADB não pôde ser configurado.",
                )
            )
            checks.append(
                self._failed(
                    "phone",
                    "Celular USB",
                    "A detecção do celular depende de uma configuração ADB válida.",
                )
            )
        else:
            try:
                version_result = adb_client.version()
                adb_version = next(
                    (line for line in version_result.stdout.splitlines() if line),
                    "ADB disponível",
                )
                checks.append(
                    PreflightCheck(
                        id="adb",
                        label="Android Debug Bridge",
                        status=PreflightCheckStatus.PASSED,
                        message=adb_version,
                    )
                )
            except EcgDeviceSetupError as exc:
                checks.append(
                    self._failed("adb", "Android Debug Bridge", str(exc))
                )

            if adb_version is not None:
                try:
                    phone = DeviceDetector(adb_client).detect_phone()
                    phone_status = (
                        PreflightCheckStatus.WARNING
                        if phone.warnings
                        else PreflightCheckStatus.PASSED
                    )
                    checks.append(
                        PreflightCheck(
                            id="phone",
                            label="Celular USB",
                            status=phone_status,
                            message=(
                                phone.warnings[0]
                                if phone.warnings
                                else f"{phone.model or 'Modelo desconhecido'} "
                                f"({phone.serial}) identificado."
                            ),
                            details=phone.to_dict(),
                        )
                    )
                except EcgDeviceSetupError as exc:
                    checks.append(self._failed("phone", "Celular USB", str(exc)))

        return PreflightReport(
            checks=tuple(checks),
            summary={
                **setup_input.persisted_identity(),
                "project_root": str(self.project_root),
                "requires_operator_confirmation": True,
            },
            phone=phone,
            adb_version=adb_version,
        )

    def _check_apks(self) -> PreflightCheck:
        try:
            result = ApkService(
                self.project_root, self.applications_path
            ).validate_all()
        except EcgDeviceSetupError as exc:
            return self._failed("apks", "APKs obrigatórios", str(exc))

        if result.valid:
            return PreflightCheck(
                id="apks",
                label="APKs obrigatórios",
                status=PreflightCheckStatus.PASSED,
                message=f"{len(result.files)} APKs foram encontrados e validados.",
                details={
                    status.application.id: {
                        "path": str(status.path),
                        "size_bytes": status.size_bytes,
                    }
                    for status in result.files
                },
            )
        missing = ", ".join(
            status.application.filename for status in result.missing_required
        )
        return self._failed(
            "apks",
            "APKs obrigatórios",
            f"APKs ausentes ou vazios: {missing}",
            details={
                "missing": [
                    str(status.path) for status in result.missing_required
                ]
            },
        )

    def _check_writable_folders(self) -> list[PreflightCheck]:
        checks: list[PreflightCheck] = []
        for folder_name in self.WRITABLE_DATA_FOLDERS:
            path = self.project_root / "data" / folder_name
            try:
                path.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    dir=path,
                    prefix=".write-test-",
                    delete=False,
                ) as temporary:
                    temporary_path = Path(temporary.name)
                temporary_path.unlink()
            except OSError as exc:
                checks.append(
                    self._failed(
                        f"writable_{folder_name}",
                        f"Escrita em data/{folder_name}",
                        f"Sem permissão de escrita em {path}: {exc}",
                    )
                )
            else:
                checks.append(
                    PreflightCheck(
                        id=f"writable_{folder_name}",
                        label=f"Escrita em data/{folder_name}",
                        status=PreflightCheckStatus.PASSED,
                        message=f"Pasta gravável: {path}",
                    )
                )
        return checks

    def _check_disk_space(self, minimum_bytes: int) -> PreflightCheck:
        try:
            usage = shutil.disk_usage(self.project_root)
        except OSError as exc:
            return self._failed(
                "disk_space",
                "Espaço em disco",
                f"Não foi possível consultar o espaço em disco: {exc}",
            )
        details = {
            "free_bytes": usage.free,
            "minimum_required_bytes": minimum_bytes,
        }
        if usage.free < minimum_bytes:
            return self._failed(
                "disk_space",
                "Espaço em disco",
                "O espaço livre é menor que o mínimo configurado para o backup.",
                details=details,
            )
        return PreflightCheck(
            id="disk_space",
            label="Espaço em disco",
            status=PreflightCheckStatus.PASSED,
            message=f"{usage.free} bytes livres.",
            details=details,
        )

    @staticmethod
    def _failed(
        check_id: str,
        label: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> PreflightCheck:
        return PreflightCheck(
            id=check_id,
            label=label,
            status=PreflightCheckStatus.FAILED,
            message=message,
            details=details or {},
        )
