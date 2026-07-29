# watch/document_copier.py
# Substitua o arquivo inteiro por este.

import shutil
import tempfile
from pathlib import Path

from core.adb_client import AdbClient
from core.android_fs import AndroidFileSystem


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

        document_items = self.android_fs.list_item_paths(
            self.documents_path
        )

        if not document_items:
            shutil.rmtree(destination_folder, ignore_errors=True)

            raise RuntimeError(
                f"Nenhum item encontrado em {self.documents_path}."
            )

        try:
            for item_path in document_items:
                result = self.adb.run(
                    [
                        "pull",
                        item_path,
                        str(destination_folder),
                    ],
                    check=False,
                )

                if result.returncode != 0:
                    raise RuntimeError(
                        "Erro ao copiar arquivos do relógio.\n"
                        f"Comando: adb pull {item_path} "
                        f"{destination_folder}\n"
                        f"Erro:\n{result.stderr or result.stdout}"
                    )

        except Exception:
            shutil.rmtree(destination_folder, ignore_errors=True)
            raise

        return destination_folder

    @staticmethod
    def create_zip_archive(
        staging_folder: Path,
        archive_path: Path,
    ) -> Path:
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            created_archive = shutil.make_archive(
                base_name=str(archive_path.with_suffix("")),
                format="zip",
                root_dir=staging_folder,
            )

        except Exception:
            archive_path.unlink(missing_ok=True)
            raise

        return Path(created_archive)

    @staticmethod
    def cleanup_staging(staging_folder: Path) -> None:
        shutil.rmtree(
            staging_folder.parent,
            ignore_errors=True,
        )