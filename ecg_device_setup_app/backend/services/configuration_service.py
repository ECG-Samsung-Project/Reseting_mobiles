"""Leitura validada das configurações fixas da aplicação."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from backend.exceptions import ConfigurationError


@dataclass(frozen=True, slots=True)
class AppSettings:
    adb_executable: str | None = None
    adb_default_timeout_seconds: float = 60
    minimum_free_space_bytes: int = 5 * 1024**3
    expected_phone_manufacturer: str = "Samsung"
    expected_phone_model_hint: str = "Galaxy A56"
    allow_apk_downgrade: bool = False

    @classmethod
    def from_yaml(cls, path: Path) -> AppSettings:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ConfigurationError(
                f"Arquivo de configurações não encontrado: {path}"
            ) from exc
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigurationError(
                f"Não foi possível ler as configurações: {path}"
            ) from exc
        if not isinstance(raw, dict):
            raise ConfigurationError("settings.yaml deve conter um objeto YAML.")

        adb = _mapping(raw.get("adb"), "adb")
        backup = _mapping(raw.get("backup"), "backup")
        phone = _mapping(raw.get("phone"), "phone")
        installation = _mapping(raw.get("installation"), "installation")

        timeout = _positive_number(
            adb.get("default_timeout_seconds", 60),
            "adb.default_timeout_seconds",
        )
        minimum_space = _non_negative_int(
            backup.get("minimum_free_space_bytes", 5 * 1024**3),
            "backup.minimum_free_space_bytes",
        )
        executable = adb.get("executable")
        if executable is not None and not isinstance(executable, str):
            raise ConfigurationError("adb.executable deve ser texto ou null.")

        return cls(
            adb_executable=executable.strip() if executable else None,
            adb_default_timeout_seconds=timeout,
            minimum_free_space_bytes=minimum_space,
            expected_phone_manufacturer=str(
                phone.get("expected_manufacturer", "Samsung")
            ).strip(),
            expected_phone_model_hint=str(
                phone.get("expected_model_hint", "Galaxy A56")
            ).strip(),
            allow_apk_downgrade=bool(
                installation.get("allow_downgrade", False)
            ),
        )


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigurationError(f"A seção {label!r} deve ser um objeto.")
    return value


def _positive_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigurationError(f"{label} deve ser um número maior que zero.")
    return float(value)


def _non_negative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ConfigurationError(f"{label} deve ser um inteiro não negativo.")
    return value
