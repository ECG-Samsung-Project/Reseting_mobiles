# watch/document_copier.py
# Substitua o arquivo inteiro por este.

import shutil
import tempfile
from pathlib import Path

from core.adb_client import AdbClient
from core.android_fs import AndroidFileSystem
from core.extraction import copy_verified, create_verified_archive


class WatchDocumentCopier:
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
    def build_unique_archive_path(
        output_root: Path,
        package_name: str,
    ) -> Path:
        output_root.mkdir(parents=True, exist_ok=True)

        archive_path = output_root / f"{package_name}.zip"
        suffix = 2

        while archive_path.exists():
            archive_path = output_root / f"{package_name}_{suffix}.zip"
            suffix += 1

        return archive_path

    @staticmethod
    def create_staging_folder(
        archive_path: Path,
    ) -> Path:
        staging_root = Path(
            tempfile.mkdtemp(prefix="watch_extraction_")
        )

        staging_folder = staging_root / archive_path.stem
        staging_folder.mkdir(parents=True, exist_ok=True)

        return staging_folder

    def copy_documents_to_staging(
        self,
        destination_folder: Path,
    ) -> Path:
        destination_folder.mkdir(parents=True, exist_ok=True)

        report = copy_verified(self.adb, self.android_fs, self.documents_path, destination_folder)
        if not report:
            return destination_folder

        return destination_folder

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