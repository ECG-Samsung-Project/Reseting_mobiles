# mobile/document_copier.py
# Substitua o arquivo inteiro.

import shutil
import tempfile
from pathlib import Path

from core.adb_client import AdbClient
from core.android_fs import AndroidFileSystem
from core.extraction import copy_verified, create_verified_archive
from watch.local_file_ops import merge_local_folder_contents


class MobileDocumentCopier:
    def __init__(
        self,
        adb: AdbClient,
        android_fs: AndroidFileSystem,
        documents_path: str,
    ) -> None:
        self.adb = adb
        self.android_fs = android_fs
        self.documents_path = documents_path

    @staticmethod
    def _build_unique_archive_path(
        output_root: Path,
        package_name: str,
    ) -> Path:
        archive_path = output_root / f"{package_name}.zip"
        suffix = 2

        while archive_path.exists():
            archive_path = output_root / f"{package_name}_{suffix}.zip"
            suffix += 1

        return archive_path

    def copy_documents_to_staging(
        self,
        participant_id: str,
        timestamp: str,
        output_root: Path,
    ) -> tuple[Path, Path]:
        output_root.mkdir(parents=True, exist_ok=True)

        package_name = f"{participant_id}_{timestamp}"

        archive_path = self._build_unique_archive_path(
            output_root=output_root,
            package_name=package_name,
        )

        staging_root = Path(
            tempfile.mkdtemp(prefix="mobile_extraction_")
        )

        staging_folder = staging_root / archive_path.stem
        staging_folder.mkdir(parents=True, exist_ok=True)

        try:
            sources = self.android_fs.existing_source_paths(self.documents_path)
            copied = 0
            for index, source in enumerate(sources, 1):
                destination = staging_root / f"source_{index:02d}"
                copied += len(copy_verified(self.adb, self.android_fs, source, destination))
                merge_local_folder_contents(destination, staging_folder)
            if not copied:
                raise RuntimeError("Nenhum arquivo encontrado nas pastas de coleta.")
        except Exception as error:
            raise RuntimeError(f"Extração incompleta. Temporários preservados em {staging_root}. {error}") from error

        return staging_folder, archive_path

    @staticmethod
    def create_zip_archive(
        staging_folder: Path,
        archive_path: Path,
    ) -> Path:
        return create_verified_archive(staging_folder, archive_path)

    @staticmethod
    def cleanup_staging(staging_folder: Path) -> None:
        shutil.rmtree(
            staging_folder.parent,
            ignore_errors=True,
        )
