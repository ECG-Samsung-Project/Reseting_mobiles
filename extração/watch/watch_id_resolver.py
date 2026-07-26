from pathlib import Path

from core.android_fs import AndroidFileSystem

from .watch_id import WatchIdParser


class WatchIdResolver:
    def __init__(
        self,
        android_fs: AndroidFileSystem,
        documents_path: str,
    ) -> None:
        self.android_fs = android_fs
        self.documents_path = documents_path

    def resolve_from_watch(self) -> tuple[str, dict]:
        files = self.android_fs.list_files(
            self.documents_path,
            check=False,
        )

        text = "\n".join(files)
        watch_ids = WatchIdParser.extract_ids(text)

        selected_id = watch_ids[0] if watch_ids else "SemId"

        id_metadata = {
            "id_type": "watch_id",
            "id_pattern": "MMZ-00-0000",
            "ids_found_raw": watch_ids,
            "ids_valid": watch_ids,
            "selected_id": selected_id,
            "has_valid_id": len(watch_ids) > 0,
            "has_multiple_valid_ids": len(watch_ids) > 1,
            "multiple_valid_ids_count": len(watch_ids),
            "multiple_valid_ids_warning": (
                "Mais de um ID de relógio encontrado. "
                "A extração foi feita usando o primeiro ID para nomear a pasta."
                if len(watch_ids) > 1
                else None
            ),
            "sample_files": [Path(file).name for file in files[:10]],
        }

        return selected_id, id_metadata