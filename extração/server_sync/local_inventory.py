from pathlib import Path, PurePosixPath

from .config import ServerSyncConfig
from .models import FileRecord


class LocalInventoryScanner:
    def scan(
        self,
        config: ServerSyncConfig,
    ) -> tuple[FileRecord, ...]:
        config.validate_local_environment()

        records: list[FileRecord] = []

        for folder in config.folders:
            folder_root = config.local_raw_root / folder

            if not folder_root.is_dir():
                raise RuntimeError(
                    "Pasta local esperada não encontrada:\n"
                    f"{folder_root}"
                )

            for local_path in sorted(folder_root.rglob("*")):
                if local_path.is_symlink():
                    raise RuntimeError(
                        "Links simbólicos não são aceitos no envio:\n"
                        f"{local_path}"
                    )

                if not local_path.is_file():
                    continue

                relative = local_path.relative_to(folder_root)
                relative_posix = PurePosixPath(*relative.parts)

                records.append(
                    FileRecord(
                        folder=folder,
                        relative_path=relative_posix,
                        size_bytes=local_path.stat().st_size,
                        local_path=Path(local_path),
                    )
                )

        return tuple(sorted(records, key=lambda record: record.key))
