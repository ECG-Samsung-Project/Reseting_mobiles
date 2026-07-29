from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from pathlib import Path, PurePosixPath
from uuid import uuid4

from .config import ServerSyncConfig
from .models import (
    ComparisonEntry,
    ComparisonStatus,
    UploadBatchResult,
    UploadProgress,
    UploadResult,
    UploadStatus,
)
from .ssh_client import RemoteHashUnavailable, SshSftpClient


ProgressCallback = Callable[[UploadProgress], None] | None
StatusCallback = Callable[[str], None] | None


class UploadService:
    HASH_CHUNK_SIZE = 8 * 1024 * 1024

    def __init__(
        self,
        config: ServerSyncConfig,
        client: SshSftpClient,
    ) -> None:
        self.config = config
        self.client = client

    def upload(
        self,
        entries: Iterable[ComparisonEntry],
        progress_callback: ProgressCallback = None,
        status_callback: StatusCallback = None,
    ) -> UploadBatchResult:
        selected_entries = tuple(entries)
        results: list[UploadResult] = []

        for entry in selected_entries:
            if entry.status != ComparisonStatus.NEW or entry.local is None:
                raise RuntimeError(
                    "Somente arquivos classificados como novos podem "
                    f"ser enviados: {entry.key}"
                )

        for index, entry in enumerate(selected_entries, start=1):
            result = self._upload_one(
                entry=entry,
                file_index=index,
                file_count=len(selected_entries),
                progress_callback=progress_callback,
                status_callback=status_callback,
            )
            results.append(result)

        return UploadBatchResult(results=tuple(results))

    def _upload_one(
        self,
        entry: ComparisonEntry,
        file_index: int,
        file_count: int,
        progress_callback: ProgressCallback,
        status_callback: StatusCallback,
    ) -> UploadResult:
        local = entry.local

        if local is None or local.local_path is None:
            raise RuntimeError(
                f"Registro local sem caminho de origem: {entry.key}"
            )

        local_path = local.local_path
        remote_folder_root = self.config.remote_raw_root / local.folder
        final_remote_path = (
            remote_folder_root / local.relative_path
        )
        temporary_remote_path: PurePosixPath | None = None
        local_sha256: str | None = None
        remote_sha256: str | None = None
        hash_verified = False
        hash_warning: str | None = None

        def notify(
            phase: str,
            transferred_bytes: int = 0,
            total_bytes: int = 0,
        ) -> None:
            if progress_callback:
                progress_callback(
                    UploadProgress(
                        file_index=file_index,
                        file_count=file_count,
                        key=entry.key,
                        phase=phase,
                        transferred_bytes=transferred_bytes,
                        total_bytes=total_bytes,
                    )
                )

        def set_status(text: str) -> None:
            if status_callback:
                status_callback(text)

        try:
            set_status(
                f"Preparando {file_index}/{file_count}: {entry.key}"
            )
            notify("preparing")

            if not local_path.is_file():
                raise RuntimeError(
                    f"O arquivo local não existe mais:\n{local_path}"
                )

            current_local_size = local_path.stat().st_size

            if current_local_size != local.size_bytes:
                raise RuntimeError(
                    "O arquivo local mudou desde a comparação. "
                    "Verifique o servidor novamente antes de enviar."
                )

            existing_size = self.client.stat_size(final_remote_path)

            if existing_size is not None:
                if existing_size == current_local_size:
                    return UploadResult(
                        key=entry.key,
                        status=UploadStatus.SKIPPED_ALREADY_SENT,
                        message=(
                            "O arquivo passou a existir no servidor com "
                            "o mesmo tamanho antes do upload."
                        ),
                        size_bytes=current_local_size,
                    )

                return UploadResult(
                    key=entry.key,
                    status=UploadStatus.BLOCKED_CONFLICT,
                    message=(
                        "O destino passou a existir no servidor com "
                        "tamanho diferente. Nada foi sobrescrito."
                    ),
                    size_bytes=current_local_size,
                )

            self.client.ensure_directory(
                remote_directory=final_remote_path.parent,
                base_directory=self.config.remote_raw_root,
            )

            if self.config.verify_sha256:
                set_status(
                    f"Calculando SHA-256 local {file_index}/{file_count}: "
                    f"{entry.key}"
                )
                notify("hashing_local")
                local_sha256 = self._calculate_local_sha256(local_path)

            temporary_remote_path = self._build_temporary_path(
                final_remote_path
            )

            set_status(
                f"Enviando {file_index}/{file_count}: {entry.key}"
            )

            def transfer_progress(
                transferred_bytes: int,
                total_bytes: int,
            ) -> None:
                notify(
                    "uploading",
                    transferred_bytes=transferred_bytes,
                    total_bytes=total_bytes,
                )

            self.client.upload_file(
                local_path=local_path,
                remote_path=temporary_remote_path,
                callback=transfer_progress,
            )

            notify(
                "validating_size",
                transferred_bytes=current_local_size,
                total_bytes=current_local_size,
            )
            remote_size = self.client.stat_size(temporary_remote_path)

            if remote_size != current_local_size:
                raise RuntimeError(
                    "O tamanho do arquivo temporário no servidor diverge "
                    f"do arquivo local ({remote_size} != "
                    f"{current_local_size})."
                )

            if self.config.verify_sha256 and local_sha256 is not None:
                set_status(
                    f"Validando SHA-256 remoto {file_index}/{file_count}: "
                    f"{entry.key}"
                )
                notify("hashing_remote")

                try:
                    remote_sha256 = self.client.remote_sha256(
                        temporary_remote_path
                    )
                except RemoteHashUnavailable as error:
                    hash_warning = str(error)
                else:
                    if remote_sha256 != local_sha256:
                        raise RuntimeError(
                            "O SHA-256 remoto diverge do arquivo local. "
                            "O arquivo temporário foi mantido e não foi "
                            "renomeado."
                        )

                    hash_verified = True

            notify("finalizing")

            if self.client.stat_size(final_remote_path) is not None:
                raise RuntimeError(
                    "O destino definitivo passou a existir durante o "
                    "upload. O arquivo temporário foi mantido e nada foi "
                    "sobrescrito."
                )

            self.client.rename_no_overwrite(
                source=temporary_remote_path,
                destination=final_remote_path,
            )

            final_size = self.client.stat_size(final_remote_path)

            if final_size != current_local_size:
                raise RuntimeError(
                    "O arquivo definitivo foi renomeado, mas a validação "
                    "final de tamanho falhou. Verifique o servidor."
                )

            notify(
                "completed",
                transferred_bytes=current_local_size,
                total_bytes=current_local_size,
            )

            message = "Upload concluído e tamanho validado."

            if hash_verified:
                message = "Upload concluído; tamanho e SHA-256 validados."
            elif hash_warning:
                message = (
                    "Upload concluído com validação de tamanho. "
                    f"{hash_warning}"
                )

            return UploadResult(
                key=entry.key,
                status=UploadStatus.SUCCESS,
                message=message,
                size_bytes=current_local_size,
                local_sha256=local_sha256,
                remote_sha256=remote_sha256,
                hash_verified=hash_verified,
            )

        except Exception as error:
            notify("failed")

            return UploadResult(
                key=entry.key,
                status=UploadStatus.FAILED,
                message=str(error),
                size_bytes=local.size_bytes,
                local_sha256=local_sha256,
                remote_sha256=remote_sha256,
                hash_verified=hash_verified,
                temporary_remote_path=temporary_remote_path,
            )

    def _build_temporary_path(
        self,
        final_remote_path: PurePosixPath,
    ) -> PurePosixPath:
        for _attempt in range(5):
            candidate = final_remote_path.with_name(
                f"{final_remote_path.name}.{uuid4().hex}.part"
            )

            if self.client.stat_size(candidate) is None:
                return candidate

        raise RuntimeError(
            "Não foi possível reservar um nome temporário para o upload."
        )

    @classmethod
    def _calculate_local_sha256(cls, local_path: Path) -> str:
        digest = hashlib.sha256()

        with local_path.open("rb") as file:
            while chunk := file.read(cls.HASH_CHUNK_SIZE):
                digest.update(chunk)

        return digest.hexdigest()
