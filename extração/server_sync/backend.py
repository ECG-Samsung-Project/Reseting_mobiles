from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import replace

from .comparator import InventoryComparator
from .config import ServerSyncConfig
from .local_inventory import LocalInventoryScanner
from .models import (
    ComparisonReport,
    UploadBatchResult,
    UploadProgress,
)
from .remote_inventory import RemoteInventoryScanner
from .ssh_client import SshSftpClient
from .upload_service import UploadService


StatusCallback = Callable[[str], None] | None
ProgressCallback = Callable[[UploadProgress], None] | None
PasswordPrompt = Callable[[str, str], str | None] | None
ConfigLoader = Callable[[], ServerSyncConfig]
ClientFactory = Callable[[ServerSyncConfig], SshSftpClient]


class ServerSyncBackend:
    def __init__(
        self,
        config_loader: ConfigLoader | None = None,
        client_factory: ClientFactory | None = None,
        local_scanner: LocalInventoryScanner | None = None,
        remote_scanner: RemoteInventoryScanner | None = None,
        comparator: InventoryComparator | None = None,
    ) -> None:
        self._uses_default_config_loader = config_loader is None
        self.config_loader = config_loader or ServerSyncConfig.load
        self.client_factory = client_factory or SshSftpClient
        self.local_scanner = local_scanner or LocalInventoryScanner()
        self.remote_scanner = remote_scanner or RemoteInventoryScanner()
        self.comparator = comparator or InventoryComparator()

        self._active_config: ServerSyncConfig | None = None
        self._active_report: ComparisonReport | None = None

    def compare_all(
        self,
        status_callback: StatusCallback = None,
        password_prompt: PasswordPrompt = None,
        connection_profile: str | None = None,
    ) -> ComparisonReport:
        def set_status(text: str) -> None:
            if status_callback:
                status_callback(text)

        self._active_config = None
        self._active_report = None

        set_status("Carregando configuração...")
        if connection_profile is None:
            config = self.config_loader()
        elif self._uses_default_config_loader:
            config = ServerSyncConfig.load(
                connection_profile=connection_profile,
            )
        else:
            raise RuntimeError(
                "O carregador de configuração personalizado não aceita "
                "seleção de perfil."
            )
        config.validate_local_environment()
        config = self._resolve_runtime_password(
            config=config,
            password_prompt=password_prompt,
        )

        set_status(
            f"Consultando {len(config.folders)} pastas locais..."
        )
        local_files = self.local_scanner.scan(config)

        set_status("Conectando ao servidor SSH/SFTP...")

        with self.client_factory(config) as client:
            set_status(
                f"Consultando {len(config.folders)} pastas do servidor..."
            )
            remote_inventory = self.remote_scanner.scan(
                config=config,
                client=client,
            )

        set_status("Comparando arquivos locais e remotos...")
        report = self.comparator.compare(
            local_files=local_files,
            remote_files=remote_inventory.files,
            remote_partial_files=remote_inventory.partial_files,
        )

        self._active_config = config
        self._active_report = report
        set_status("Comparação concluída.")

        return report

    def upload_selected(
        self,
        report: ComparisonReport,
        selected_keys: Iterable[str],
        progress_callback: ProgressCallback = None,
        status_callback: StatusCallback = None,
    ) -> UploadBatchResult:
        if (
            self._active_config is None
            or self._active_report is None
            or report is not self._active_report
        ):
            raise RuntimeError(
                "A comparação não está mais válida. "
                "Verifique o servidor novamente."
            )

        selected_key_set = set(selected_keys)

        if not selected_key_set:
            raise RuntimeError("Nenhum arquivo novo foi selecionado.")

        new_entries_by_key = {
            entry.key: entry
            for entry in report.new_entries
        }
        invalid_keys = selected_key_set - set(new_entries_by_key)

        if invalid_keys:
            raise RuntimeError(
                "A seleção contém arquivos que não estão classificados "
                f"como novos: {', '.join(sorted(invalid_keys))}"
            )

        selected_entries = tuple(
            new_entries_by_key[key]
            for key in sorted(selected_key_set)
        )
        config = self._active_config

        try:
            if status_callback:
                status_callback("Conectando ao servidor para o upload...")

            with self.client_factory(config) as client:
                service = UploadService(
                    config=config,
                    client=client,
                )
                result = service.upload(
                    entries=selected_entries,
                    progress_callback=progress_callback,
                    status_callback=status_callback,
                )
        finally:
            self._active_report = None
            self._active_config = None

        if status_callback:
            status_callback("Processamento dos uploads concluído.")

        return result

    def get_active_connection_summary(self) -> str | None:
        if self._active_config is None:
            return None

        return self._active_config.safe_connection_summary()

    def invalidate_comparison(self) -> None:
        self._active_report = None
        self._active_config = None

    @staticmethod
    def _resolve_runtime_password(
        config: ServerSyncConfig,
        password_prompt: PasswordPrompt,
    ) -> ServerSyncConfig:
        if (
            config.authentication_method != "password"
            or config.password is not None
        ):
            return config

        if password_prompt is None:
            raise RuntimeError(
                "A autenticação está configurada como password, mas "
                "nenhuma senha foi informada."
            )

        password = password_prompt(
            config.host,
            config.username,
        )

        if password is None:
            raise RuntimeError("Entrada da senha SSH cancelada.")

        if password == "":
            raise RuntimeError("A senha SSH não pode ficar vazia.")

        return replace(config, password=password)
