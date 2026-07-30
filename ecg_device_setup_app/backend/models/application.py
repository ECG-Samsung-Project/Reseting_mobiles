"""Catálogo de APKs definido por YAML."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from backend.exceptions import ConfigurationError


class DeviceTarget(StrEnum):
    PHONE = "phone"
    WATCH = "watch"


@dataclass(frozen=True, slots=True)
class ApplicationDefinition:
    id: str
    display_name: str
    filename: str
    target: DeviceTarget
    package_name: str | None = None
    required: bool = True

    def apk_path(self, project_root: Path) -> Path:
        base = (project_root / "apks" / self.target.value).resolve()
        candidate = (base / self.filename).resolve()
        if candidate.parent != base or candidate.name != self.filename:
            raise ConfigurationError(
                f"Caminho inseguro de APK configurado para {self.id!r}."
            )
        if candidate.suffix.lower() != ".apk":
            raise ConfigurationError(
                f"O arquivo configurado para {self.id!r} não possui extensão .apk."
            )
        return candidate


@dataclass(frozen=True, slots=True)
class ApplicationCatalog:
    phone: tuple[ApplicationDefinition, ...]
    watch: tuple[ApplicationDefinition, ...]

    @property
    def all(self) -> tuple[ApplicationDefinition, ...]:
        return self.phone + self.watch

    @classmethod
    def from_yaml(cls, path: Path) -> ApplicationCatalog:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ConfigurationError(
                f"Arquivo de aplicativos não encontrado: {path}"
            ) from exc
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigurationError(
                f"Não foi possível ler a configuração de aplicativos: {path}"
            ) from exc

        if not isinstance(raw, dict):
            raise ConfigurationError("applications.yaml deve conter um objeto YAML.")

        phone = cls._parse_group(raw.get("phone"), DeviceTarget.PHONE)
        watch = cls._parse_group(raw.get("watch"), DeviceTarget.WATCH)
        identifiers = [application.id for application in phone + watch]
        if len(identifiers) != len(set(identifiers)):
            raise ConfigurationError("Os IDs dos aplicativos devem ser únicos.")
        return cls(phone=phone, watch=watch)

    @staticmethod
    def _parse_group(
        entries: Any, target: DeviceTarget
    ) -> tuple[ApplicationDefinition, ...]:
        if not isinstance(entries, list):
            raise ConfigurationError(
                f"A seção {target.value!r} deve ser uma lista de aplicativos."
            )

        applications: list[ApplicationDefinition] = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ConfigurationError(
                    f"Entrada {index} de {target.value!r} deve ser um objeto."
                )
            try:
                app_id = str(entry["id"]).strip()
                display_name = str(entry["display_name"]).strip()
                filename = str(entry["filename"]).strip()
            except KeyError as exc:
                raise ConfigurationError(
                    f"Campo obrigatório ausente em {target.value}[{index}]: {exc.args[0]}"
                ) from exc
            if not app_id or not display_name or not filename:
                raise ConfigurationError(
                    f"Campos vazios não são permitidos em {target.value}[{index}]."
                )
            package_name = entry.get("package_name")
            if package_name is not None:
                package_name = str(package_name).strip() or None
            applications.append(
                ApplicationDefinition(
                    id=app_id,
                    display_name=display_name,
                    filename=filename,
                    target=target,
                    package_name=package_name,
                    required=bool(entry.get("required", True)),
                )
            )
        return tuple(applications)
