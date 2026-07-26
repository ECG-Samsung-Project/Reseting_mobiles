import shutil
from pathlib import Path

from core.adb_client import AdbClient
from core.android_fs import AndroidFileSystem
from core.destination import build_unique_destination_folder


class WatchDocumentCopier:
    def __init__(
        self,
        adb: AdbClient,
        android_fs: AndroidFileSystem,
        documents_path: str,
        output_root: Path,
    ) -> None:
        self.adb = adb
        self.android_fs = android_fs
        self.documents_path = documents_path
        self.output_root = output_root

    def copy_documents_to_output(
        self,
        watch_id: str,
        timestamp: str,
    ) -> Path:
        self.output_root.mkdir(parents=True, exist_ok=True)

        folder_name = f"{watch_id}_{timestamp}"

        destination_folder = build_unique_destination_folder(
            output_root=self.output_root,
            folder_name=folder_name,
        )

        destination_folder.mkdir(parents=True, exist_ok=True)

        document_items = self.android_fs.list_item_paths(self.documents_path)

        if not document_items:
            shutil.rmtree(destination_folder, ignore_errors=True)

            raise RuntimeError(
                f"Nenhum item encontrado em {self.documents_path}."
            )

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
                shutil.rmtree(destination_folder, ignore_errors=True)

                raise RuntimeError(
                    "Erro ao copiar arquivos do relógio.\n"
                    f"Comando: adb pull {item_path} {destination_folder}\n"
                    f"Erro:\n{result.stderr or result.stdout}"
                )

        return destination_folder