from collections.abc import Iterable

from .models import (
    ComparisonEntry,
    ComparisonReport,
    ComparisonStatus,
    FileRecord,
)


class InventoryComparator:
    @staticmethod
    def compare(
        local_files: Iterable[FileRecord],
        remote_files: Iterable[FileRecord],
        remote_partial_files: Iterable[FileRecord] = (),
    ) -> ComparisonReport:
        local_by_key = InventoryComparator._index_files(
            local_files,
            "local",
        )
        remote_by_key = InventoryComparator._index_files(
            remote_files,
            "remoto",
        )

        entries: list[ComparisonEntry] = []

        for key in sorted(set(local_by_key) | set(remote_by_key)):
            local = local_by_key.get(key)
            remote = remote_by_key.get(key)

            if local is not None and remote is None:
                status = ComparisonStatus.NEW
            elif local is None and remote is not None:
                status = ComparisonStatus.REMOTE_ONLY
            elif (
                local is not None
                and remote is not None
                and local.size_bytes == remote.size_bytes
            ):
                status = ComparisonStatus.ALREADY_SENT
            else:
                status = ComparisonStatus.CONFLICT

            entries.append(
                ComparisonEntry(
                    status=status,
                    local=local,
                    remote=remote,
                )
            )

        return ComparisonReport(
            entries=tuple(entries),
            remote_partial_files=tuple(remote_partial_files),
        )

    @staticmethod
    def _index_files(
        records: Iterable[FileRecord],
        inventory_name: str,
    ) -> dict[str, FileRecord]:
        indexed: dict[str, FileRecord] = {}

        for record in records:
            if record.key in indexed:
                raise RuntimeError(
                    f"Arquivo duplicado no inventário {inventory_name}: "
                    f"{record.key}"
                )

            indexed[record.key] = record

        return indexed
