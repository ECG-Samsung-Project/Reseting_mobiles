# mobile/document_copier.py
# Substitua o arquivo inteiro.

import shutil
import tempfile
from pathlib import Path

from core.adb_client import AdbClient
from core.android_fs import AndroidFileSystem


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

        document_items = self.android_fs.list_item_paths(
            self.documents_path
        )

        if not document_items:
            shutil.rmtree(staging_root, ignore_errors=True)

            raise RuntimeError(
                f"Nenhum item encontrado em {self.documents_path}."
            )

        try:
            for item_path in document_items:
                result = self.adb.run(
                    [
                        "pull",
                        item_path,
                        str(staging_folder),
                    ],
                    check=False,
                )

                if result.returncode != 0:
                    raise RuntimeError(
                        "Erro ao copiar arquivos do celular.\n"
                        f"Comando: adb pull {item_path} "
                        f"{staging_folder}\n"
                        f"Erro:\n{result.stderr or result.stdout}"
                    )

        except Exception:
            shutil.rmtree(staging_root, ignore_errors=True)
            raise

        return staging_folder, archive_path

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