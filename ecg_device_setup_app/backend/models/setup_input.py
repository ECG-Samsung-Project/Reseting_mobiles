"""Dados fornecidos pelo operador no início de uma configuração."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


_UNSAFE_PATH_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_REPEATED_SEPARATORS = re.compile(r"[-_.]{2,}")
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def safe_path_component(value: str) -> str:
    """Converte um identificador em um único componente seguro de caminho."""

    normalized = _UNSAFE_PATH_CHARS.sub("-", value.strip())
    normalized = _REPEATED_SEPARATORS.sub("-", normalized).strip(" .-_")
    if not normalized or normalized in {".", ".."}:
        raise ValueError("O identificador não gera um nome de pasta seguro.")
    if normalized.split(".", 1)[0].upper() in _WINDOWS_RESERVED_NAMES:
        raise ValueError("O identificador coincide com um nome reservado do Windows.")
    return normalized


class SetupInput(BaseModel):
    """Entrada sensível mantida apenas em memória.

    ``google_password`` é mascarado no ``repr`` pelo ``SecretStr`` e excluído
    de qualquer ``model_dump``/serialização Pydantic.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    participant_id: str = Field(min_length=1, max_length=100)
    kit_id: str = Field(min_length=1, max_length=100)
    google_email: str = Field(min_length=3, max_length=254)
    google_password: SecretStr = Field(min_length=1, exclude=True, repr=False)

    @field_validator("participant_id", "kit_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        safe_path_component(value)
        return value

    @field_validator("google_email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if value.count("@") != 1:
            raise ValueError("Informe um e-mail Google válido.")
        local, domain = value.rsplit("@", 1)
        if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise ValueError("Informe um e-mail Google válido.")
        return value

    @property
    def participant_folder_name(self) -> str:
        return safe_path_component(self.participant_id)

    @property
    def kit_folder_name(self) -> str:
        return safe_path_component(self.kit_id)

    def persisted_identity(self) -> dict[str, str]:
        """Representação que pode ser persistida sem a senha."""

        return {
            "participant_id": self.participant_id,
            "kit_id": self.kit_id,
            "google_email": self.google_email,
        }
