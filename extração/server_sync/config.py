from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Mapping


DEFAULT_SYNC_FOLDERS = (
    "mobile_fl_data",
    "mobile_ic_data",
    "watch_fl_data",
    "watch_ic_data",
    "ecg_data",
    "holter_data",
    "looper_data",
    "eco_data",
    "redcap_data",
    "blood_test_data",
    "bio_data",
)

CONNECTION_PROFILES = {
    "external": "Externo",
    "laboratory": "Laboratório (rede local)",
}

PROFILE_ENV_PREFIXES = {
    "external": "ECG_SYNC_EXTERNAL",
    "laboratory": "ECG_SYNC_LAB",
}


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None or not value.strip():
        return default

    normalized = value.strip().lower()

    if normalized in {"1", "true", "yes", "sim", "on"}:
        return True

    if normalized in {"0", "false", "no", "não", "nao", "off"}:
        return False

    raise RuntimeError(f"Valor booleano inválido na configuração: {value!r}.")


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    stripped = value.strip()
    return stripped or None


def _optional_secret(value: str | None) -> str | None:
    if value is None or value == "":
        return None

    return value


@dataclass(frozen=True)
class ServerSyncConfig:
    host: str
    username: str
    local_raw_root: Path
    remote_raw_root: PurePosixPath
    port: int = 22
    authentication_method: str = "auto"
    folders: tuple[str, ...] = DEFAULT_SYNC_FOLDERS
    password: str | None = field(default=None, repr=False)
    private_key: Path | None = None
    private_key_passphrase: str | None = field(default=None, repr=False)
    known_hosts: Path | None = None
    allow_agent: bool = True
    look_for_keys: bool = True
    verify_sha256: bool = True
    connect_timeout_seconds: float = 20.0
    connection_profile: str | None = None

    @classmethod
    def load(
        cls,
        env_path: Path | None = None,
        connection_profile: str | None = None,
    ) -> "ServerSyncConfig":
        resolved_env_path = env_path or (
            Path(__file__).resolve().parents[2] / ".env"
        )

        if resolved_env_path.is_file():
            try:
                from dotenv import load_dotenv
            except ImportError as error:
                raise RuntimeError(
                    "O arquivo .env existe, mas python-dotenv não está instalado. "
                    "Execute: pip install -r requirements.txt"
                ) from error

            load_dotenv(
                dotenv_path=resolved_env_path,
                override=False,
            )

        return cls.from_mapping(
            os.environ,
            connection_profile=connection_profile,
        )

    @classmethod
    def from_mapping(
        cls,
        values: Mapping[str, str],
        connection_profile: str | None = None,
    ) -> "ServerSyncConfig":
        def required(name: str) -> str:
            value = _optional_text(values.get(name))

            if value is None:
                raise RuntimeError(
                    f"Configuração obrigatória ausente: {name}."
                )

            return value

        selected_profile = connection_profile or _optional_text(
            values.get("ECG_SYNC_DEFAULT_CONNECTION")
        )

        if (
            selected_profile is not None
            and selected_profile not in CONNECTION_PROFILES
        ):
            valid_profiles = ", ".join(CONNECTION_PROFILES)
            raise RuntimeError(
                "Perfil de conexão inválido: "
                f"{selected_profile!r}. Use: {valid_profiles}."
            )

        profile_prefix = (
            PROFILE_ENV_PREFIXES[selected_profile]
            if selected_profile is not None
            else None
        )

        def profile_value(
            name: str,
            fallback_to_common: bool = True,
        ) -> str:
            if profile_prefix is not None:
                profile_name = f"{profile_prefix}_{name}"
                value = _optional_text(values.get(profile_name))

                if value is not None:
                    return value

                if not fallback_to_common:
                    return required(profile_name)

            return required(f"ECG_SYNC_{name}")

        host = profile_value("HOST", fallback_to_common=False)
        username = profile_value("USER")
        local_raw_root = Path(required("ECG_SYNC_LOCAL_RAW_ROOT")).expanduser()
        remote_raw_root = PurePosixPath(
            required("ECG_SYNC_REMOTE_RAW_ROOT")
        )

        port_text = (
            profile_value("PORT", fallback_to_common=False)
            if profile_prefix is not None
            else values.get("ECG_SYNC_PORT", "22").strip()
        )

        try:
            port = int(port_text)
        except ValueError as error:
            raise RuntimeError(
                "ECG_SYNC_PORT deve ser um número inteiro."
            ) from error

        if port < 1 or port > 65535:
            raise RuntimeError(
                "ECG_SYNC_PORT deve estar entre 1 e 65535."
            )

        authentication_method = values.get(
            "ECG_SYNC_AUTH_METHOD",
            "auto",
        ).strip().lower()

        if authentication_method not in {"auto", "password", "key"}:
            raise RuntimeError(
                "ECG_SYNC_AUTH_METHOD deve ser auto, password ou key."
            )

        if not local_raw_root.is_absolute():
            raise RuntimeError(
                "ECG_SYNC_LOCAL_RAW_ROOT deve ser um caminho absoluto."
            )

        if not remote_raw_root.is_absolute() or ".." in remote_raw_root.parts:
            raise RuntimeError(
                "ECG_SYNC_REMOTE_RAW_ROOT deve ser um caminho Linux "
                "absoluto e não pode conter '..'."
            )

        folders_text = values.get(
            "ECG_SYNC_FOLDERS",
            ",".join(DEFAULT_SYNC_FOLDERS),
        )
        folders = tuple(
            folder.strip()
            for folder in folders_text.split(",")
            if folder.strip()
        )

        if not folders:
            raise RuntimeError(
                "ECG_SYNC_FOLDERS deve conter ao menos uma pasta."
            )

        if len(set(folders)) != len(folders):
            raise RuntimeError(
                "ECG_SYNC_FOLDERS contém nomes repetidos."
            )

        for folder in folders:
            folder_path = PurePosixPath(folder)

            if (
                folder_path.is_absolute()
                or len(folder_path.parts) != 1
                or folder in {".", ".."}
            ):
                raise RuntimeError(
                    "Cada item de ECG_SYNC_FOLDERS deve ser apenas "
                    f"um nome de pasta. Valor inválido: {folder!r}."
                )

        private_key_text = _optional_text(
            values.get("ECG_SYNC_PRIVATE_KEY")
        )
        known_hosts_text = _optional_text(
            values.get("ECG_SYNC_KNOWN_HOSTS")
        )

        timeout_text = values.get(
            "ECG_SYNC_CONNECT_TIMEOUT_SECONDS",
            "20",
        ).strip()

        try:
            connect_timeout_seconds = float(timeout_text)
        except ValueError as error:
            raise RuntimeError(
                "ECG_SYNC_CONNECT_TIMEOUT_SECONDS deve ser numérico."
            ) from error

        if connect_timeout_seconds <= 0:
            raise RuntimeError(
                "ECG_SYNC_CONNECT_TIMEOUT_SECONDS deve ser maior que zero."
            )

        return cls(
            host=host,
            username=username,
            local_raw_root=local_raw_root,
            remote_raw_root=remote_raw_root,
            port=port,
            authentication_method=authentication_method,
            folders=folders,
            password=_optional_secret(values.get("ECG_SYNC_PASSWORD")),
            private_key=(
                Path(private_key_text).expanduser()
                if private_key_text
                else None
            ),
            private_key_passphrase=_optional_secret(
                values.get("ECG_SYNC_PRIVATE_KEY_PASSPHRASE")
            ),
            known_hosts=(
                Path(known_hosts_text).expanduser()
                if known_hosts_text
                else None
            ),
            allow_agent=_parse_bool(
                values.get("ECG_SYNC_ALLOW_AGENT"),
                True,
            ),
            look_for_keys=_parse_bool(
                values.get("ECG_SYNC_LOOK_FOR_KEYS"),
                True,
            ),
            verify_sha256=_parse_bool(
                values.get("ECG_SYNC_VERIFY_SHA256"),
                True,
            ),
            connect_timeout_seconds=connect_timeout_seconds,
            connection_profile=selected_profile,
        )

    def validate_local_environment(self) -> None:
        if not self.local_raw_root.is_dir():
            raise RuntimeError(
                "Raiz local não encontrada ou não é uma pasta:\n"
                f"{self.local_raw_root}"
            )

        if self.private_key is not None and not self.private_key.is_file():
            raise RuntimeError(
                "Chave SSH privada não encontrada:\n"
                f"{self.private_key}"
            )

        if self.known_hosts is not None and not self.known_hosts.is_file():
            raise RuntimeError(
                "Arquivo known_hosts não encontrado:\n"
                f"{self.known_hosts}"
            )

    def safe_connection_summary(self) -> str:
        profile_summary = ""

        if self.connection_profile is not None:
            profile_summary = (
                f"{CONNECTION_PROFILES[self.connection_profile]} | "
            )

        return (
            f"{profile_summary}{self.username}@{self.host}:{self.port} | "
            f"{self.local_raw_root} → {self.remote_raw_root} | "
            f"autenticação: {self.authentication_method}"
        )
