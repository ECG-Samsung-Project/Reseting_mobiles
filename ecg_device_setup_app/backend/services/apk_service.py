"""Carregamento e validação de todos os APKs configurados."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.models.application import ApplicationCatalog, ApplicationDefinition


@dataclass(frozen=True, slots=True)
class ApkFileStatus:
    application: ApplicationDefinition
    path: Path
    exists: bool
    size_bytes: int = 0
    error: str | None = None

    @property
    def valid(self) -> bool:
        return self.exists and self.size_bytes > 0 and self.error is None


@dataclass(frozen=True, slots=True)
class ApkValidationResult:
    catalog: ApplicationCatalog
    files: tuple[ApkFileStatus, ...]

    @property
    def missing_required(self) -> tuple[ApkFileStatus, ...]:
        return tuple(
            status
            for status in self.files
            if status.application.required and not status.valid
        )

    @property
    def valid(self) -> bool:
        return not self.missing_required


class ApkService:
    def __init__(self, project_root: Path, applications_yaml: Path | None = None) -> None:
        self.project_root = project_root.resolve()
        self.applications_yaml = (
            applications_yaml or self.project_root / "config" / "applications.yaml"
        )

    def load_catalog(self) -> ApplicationCatalog:
        return ApplicationCatalog.from_yaml(self.applications_yaml)

    def validate_all(self) -> ApkValidationResult:
        catalog = self.load_catalog()
        statuses: list[ApkFileStatus] = []
        for application in catalog.all:
            path = application.apk_path(self.project_root)
            try:
                exists = path.is_file()
                size = path.stat().st_size if exists else 0
                error = "arquivo vazio" if exists and size == 0 else None
            except OSError as exc:
                exists = False
                size = 0
                error = str(exc)
            statuses.append(
                ApkFileStatus(
                    application=application,
                    path=path,
                    exists=exists,
                    size_bytes=size,
                    error=error,
                )
            )
        return ApkValidationResult(catalog=catalog, files=tuple(statuses))
