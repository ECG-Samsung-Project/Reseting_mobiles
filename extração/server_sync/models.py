from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath


class ComparisonStatus(str, Enum):
    NEW = "new"
    ALREADY_SENT = "already_sent"
    CONFLICT = "conflict"
    REMOTE_ONLY = "remote_only"


class UploadStatus(str, Enum):
    SUCCESS = "success"
    SKIPPED_ALREADY_SENT = "skipped_already_sent"
    BLOCKED_CONFLICT = "blocked_conflict"
    FAILED = "failed"


@dataclass(frozen=True)
class FileRecord:
    folder: str
    relative_path: PurePosixPath
    size_bytes: int
    local_path: Path | None = None
    remote_path: PurePosixPath | None = None

    def __post_init__(self) -> None:
        if not self.folder or "/" in self.folder or "\\" in self.folder:
            raise ValueError(f"Nome de pasta inválido: {self.folder!r}.")

        if (
            self.relative_path.is_absolute()
            or not self.relative_path.parts
            or ".." in self.relative_path.parts
        ):
            raise ValueError(
                f"Caminho relativo inválido: {self.relative_path!s}."
            )

        if self.size_bytes < 0:
            raise ValueError("O tamanho do arquivo não pode ser negativo.")

    @property
    def key(self) -> str:
        return f"{self.folder}/{self.relative_path.as_posix()}"

    @property
    def display_path(self) -> str:
        return self.key


@dataclass(frozen=True)
class ComparisonEntry:
    status: ComparisonStatus
    local: FileRecord | None
    remote: FileRecord | None

    @property
    def key(self) -> str:
        record = self.local or self.remote

        if record is None:
            raise RuntimeError("Comparação sem registro local ou remoto.")

        return record.key

    @property
    def display_path(self) -> str:
        return self.key

    @property
    def size_for_total(self) -> int:
        if self.local is not None:
            return self.local.size_bytes

        if self.remote is not None:
            return self.remote.size_bytes

        return 0


@dataclass(frozen=True)
class ComparisonReport:
    entries: tuple[ComparisonEntry, ...]
    remote_partial_files: tuple[FileRecord, ...] = ()

    def entries_with_status(
        self,
        status: ComparisonStatus,
    ) -> tuple[ComparisonEntry, ...]:
        return tuple(
            entry for entry in self.entries if entry.status == status
        )

    def count(self, status: ComparisonStatus) -> int:
        return len(self.entries_with_status(status))

    def total_size(self, status: ComparisonStatus) -> int:
        return sum(
            entry.size_for_total
            for entry in self.entries
            if entry.status == status
        )

    @property
    def new_entries(self) -> tuple[ComparisonEntry, ...]:
        return self.entries_with_status(ComparisonStatus.NEW)


@dataclass(frozen=True)
class RemoteInventory:
    files: tuple[FileRecord, ...]
    partial_files: tuple[FileRecord, ...] = ()


@dataclass(frozen=True)
class UploadProgress:
    file_index: int
    file_count: int
    key: str
    phase: str
    transferred_bytes: int = 0
    total_bytes: int = 0


@dataclass(frozen=True)
class UploadResult:
    key: str
    status: UploadStatus
    message: str
    size_bytes: int
    local_sha256: str | None = None
    remote_sha256: str | None = None
    hash_verified: bool = False
    temporary_remote_path: PurePosixPath | None = None


@dataclass(frozen=True)
class UploadBatchResult:
    results: tuple[UploadResult, ...]

    def count(self, status: UploadStatus) -> int:
        return sum(result.status == status for result in self.results)

    @property
    def successful_bytes(self) -> int:
        return sum(
            result.size_bytes
            for result in self.results
            if result.status == UploadStatus.SUCCESS
        )
