from datetime import datetime
from pathlib import Path
from typing import Callable

from core.adb_client import AdbClient
from core.android_fs import AndroidFileSystem
from core.metadata_writer import write_json_metadata

from .android_storage import WatchAndroidStorage
from .config import WatchExtractionConfig
from .document_copier import WatchDocumentCopier
from .local_file_ops import merge_local_folder_contents
from .watch_connection import WatchConnectionManager
from .watch_id_resolver import WatchIdResolver
from .watch_metadata import WatchMetadataBuilder

StatusCallback = Callable[[str], None] | None


class WatchBackend:
    def __init__(
        self,
        config: WatchExtractionConfig | None = None,
    ) -> None:
        self.config = config or WatchExtractionConfig()

        self.adb = AdbClient(self.config.adb_path)
        self.android_fs = AndroidFileSystem(self.adb)

        self.connection_manager = WatchConnectionManager(self.adb)

        self.storage = WatchAndroidStorage(
            adb=self.adb,
            config=self.config,
        )

        self.metadata_builder = WatchMetadataBuilder(
            config=self.config,
            adb=self.adb,
            android_fs=self.android_fs,
            connection_manager=self.connection_manager,
        )

        self.output_root = self.config.output_root
        self.output_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_current_timestamp() -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @staticmethod
    def format_watch_name(watch_number: str) -> str:
        watch_number = watch_number.strip()

        if not watch_number:
            raise RuntimeError("Número do relógio não pode ficar vazio.")

        if not watch_number.isdigit():
            raise RuntimeError("O número do relógio deve conter apenas dígitos.")

        number = int(watch_number)

        if number < 0 or number > 999:
            raise RuntimeError("O número do relógio deve estar entre 0 e 999.")

        return f"Relógio - {number:03d}"

    def get_pairing_address(self, ip: str, pairing_port: str) -> str:
        return self.connection_manager.get_pairing_address(
            ip=ip,
            pairing_port=pairing_port,
        )

    def get_connect_address(self, ip: str, connect_port: str) -> str:
        return self.connection_manager.get_connect_address(
            ip=ip,
            connect_port=connect_port,
        )

    def check_adb_installed(self) -> None:
        self.connection_manager.check_adb_installed()

    def pair_watch(
        self,
        ip: str,
        pairing_port: str,
        pairing_code: str,
    ) -> str:
        return self.connection_manager.pair_watch(
            ip=ip,
            pairing_port=pairing_port,
            pairing_code=pairing_code,
        )

    def connect_watch(
        self,
        ip: str,
        connect_port: str,
    ) -> tuple[str, str]:
        return self.connection_manager.connect_watch(
            ip=ip,
            connect_port=connect_port,
        )

    def disconnect_all_devices(self) -> str:
        return self.connection_manager.disconnect_all_devices()

    # Mantidos como proxy para não quebrar o frontend.
    # Porque humanos clicam em botão antes de refatorar interface, aparentemente.
    def adb_shell_stdout(self, shell_command: str) -> str:
        return self.storage.adb_shell_stdout(shell_command)

    def android_dir_exists(self, root_path: str) -> bool:
        return self.storage.android_dir_exists(root_path)

    def get_android_folder_tree(
        self,
        root_path: str,
        max_items: int = 1000,
    ) -> dict:
        return self.storage.get_android_folder_tree(
            root_path=root_path,
            max_items=max_items,
        )

    def get_existing_watch_source_paths(self) -> list[str]:
        return self.storage.get_existing_watch_source_paths()

    def get_watch_documents_tree(
        self,
        max_items: int = 1000,
        source_paths: list[str] | None = None,
    ) -> dict:
        return self.storage.get_watch_documents_tree(
            max_items=max_items,
            source_paths=source_paths,
        )

    def resolve_watch_id_from_sources(
        self,
        source_paths: list[str],
        allow_fallback: bool = True,
    ) -> tuple[str, dict]:
        errors: list[str] = []

        for source_path in source_paths:
            try:
                resolver = WatchIdResolver(
                    android_fs=self.android_fs,
                    documents_path=source_path,
                )

                selected_id, id_metadata = resolver.resolve_from_watch()

                if not selected_id:
                    raise RuntimeError("ID vazio retornado pelo resolver.")

                if isinstance(id_metadata, dict):
                    id_metadata = {
                        **id_metadata,
                        "source_path": source_path,
                    }
                else:
                    id_metadata = {
                        "source_path": source_path,
                        "raw_metadata": id_metadata,
                    }

                return selected_id, id_metadata

            except Exception as exc:
                errors.append(f"{source_path}: {exc}")

        if allow_fallback:
            return (
                "SemId",
                {
                    "source_path": None,
                    "resolver_errors": errors,
                    "warning": "ID não encontrado. Usando SemId como fallback.",
                },
            )

        error_text = "\n".join(f"- {error}" for error in errors)

        raise RuntimeError(
            "Não consegui encontrar o ID do participante nas pastas verificadas.\n\n"
            "Pastas verificadas:\n"
            f"{error_text}"
        )

    def copy_watch_sources_to_output(
        self,
        source_paths: list[str],
        watch_id: str,
        timestamp: str,
    ) -> tuple[Path, list[str]]:
        output_folder: Path | None = None
        copied_sources: list[str] = []
        errors: list[str] = []

        for source_path in source_paths:
            try:
                copier = WatchDocumentCopier(
                    adb=self.adb,
                    android_fs=self.android_fs,
                    documents_path=source_path,
                    output_root=self.output_root,
                )

                current_output_folder = Path(
                    copier.copy_documents_to_output(
                        watch_id=watch_id,
                        timestamp=timestamp,
                    )
                )

                if output_folder is None:
                    output_folder = current_output_folder
                else:
                    merge_local_folder_contents(
                        source_folder=current_output_folder,
                        destination_folder=output_folder,
                    )

                copied_sources.append(source_path)

            except Exception as exc:
                errors.append(f"{source_path}: {exc}")

        if errors:
            error_text = "\n".join(f"- {error}" for error in errors)

            raise RuntimeError(
                "Falha ao copiar uma ou mais pastas do relógio.\n\n"
                f"{error_text}"
            )

        if output_folder is None:
            raise RuntimeError("Nenhuma pasta foi copiada do relógio.")

        return output_folder, copied_sources

    def inspect_watch_documents(
        self,
        ip: str,
        connect_port: str,
        status_callback: StatusCallback = None,
    ) -> dict:
        def set_status(text: str) -> None:
            if status_callback:
                status_callback(text)

        connect_address = self.get_connect_address(
            ip=ip,
            connect_port=connect_port,
        )

        set_status("Verificando ADB...")
        self.check_adb_installed()

        set_status("Verificando relógio conectado...")
        devices = self.connection_manager.get_connected_devices()

        if not devices:
            raise RuntimeError(
                "Nenhum relógio conectado via ADB.\n\n"
                "Clique primeiro em 'Conectar relógio'."
            )

        device_id = self.connection_manager.get_target_device_id(
            devices=devices,
            connect_address=connect_address,
        )

        self.adb.target_device_id = device_id

        set_status(f"Usando dispositivo: {device_id}")

        set_status("Procurando pastas Download e Documents...")
        source_paths = self.get_existing_watch_source_paths()

        set_status("Varrendo Download e Documents...")
        documents_tree = self.get_watch_documents_tree(
            source_paths=source_paths,
        )

        set_status("Buscando ID nos arquivos...")
        selected_id, id_metadata = self.resolve_watch_id_from_sources(
            source_paths=source_paths,
            allow_fallback=True,
        )

        set_status("Varredura concluída.")

        return {
            "device_id": device_id,
            "selected_id": selected_id,
            "id_metadata": id_metadata,
            "documents_path": documents_tree["root_path"],
            "source_paths": source_paths,
            "file_count": documents_tree["file_count"],
            "folder_count": documents_tree["folder_count"],
            "total_items": documents_tree["total_items"],
            "tree_text": documents_tree["tree_text"],
        }

    def extract_documents(
        self,
        watch_number: str,
        ip: str,
        pairing_port: str,
        connect_port: str,
        status_callback: StatusCallback = None,
    ) -> dict:
        def set_status(text: str) -> None:
            if status_callback:
                status_callback(text)

        watch_name = self.format_watch_name(watch_number)
        timestamp = self.get_current_timestamp()

        connect_address = self.get_connect_address(
            ip=ip,
            connect_port=connect_port,
        )

        set_status("Verificando ADB...")
        self.check_adb_installed()

        set_status("Verificando relógio conectado...")
        devices = self.connection_manager.get_connected_devices()

        if not devices:
            raise RuntimeError(
                "Nenhum relógio conectado via ADB.\n\n"
                "Clique primeiro em 'Conectar relógio'.\n\n"
                "Confira:\n"
                "1. Relógio na mesma rede Wi-Fi do PC\n"
                "2. Depuração sem fio ativada no relógio\n"
                "3. Pareamento feito\n"
                "4. IP e porta de conexão informados corretamente"
            )

        device_id = self.connection_manager.get_target_device_id(
            devices=devices,
            connect_address=connect_address,
        )

        self.adb.target_device_id = device_id

        set_status(f"Usando dispositivo: {device_id}")

        set_status("Procurando pastas Download e Documents...")
        source_paths = self.get_existing_watch_source_paths()

        set_status("Buscando ID nos arquivos...")
        selected_id, id_metadata = self.resolve_watch_id_from_sources(
            source_paths=source_paths,
            allow_fallback=True,
        )

        set_status("Copiando Download e Documents para landing...")
        output_folder, copied_sources = self.copy_watch_sources_to_output(
            source_paths=source_paths,
            watch_id=selected_id,
            timestamp=timestamp,
        )

        set_status("Criando JSON de metadados...")
        metadata = self.metadata_builder.build_metadata(
            selected_id=selected_id,
            id_metadata=id_metadata,
            watch_name=watch_name,
            destination_folder=output_folder,
            device_id=device_id,
            timestamp=timestamp,
            connection={
                "ip": ip.strip(),
                "pairing_port": pairing_port.strip(),
                "connect_port": connect_port.strip(),
            },
        )

        metadata["source_paths_checked"] = source_paths
        metadata["source_paths_copied"] = copied_sources
        metadata["id_source_path"] = id_metadata.get("source_path")
        metadata["id_resolver_warning"] = id_metadata.get("warning")

        json_path = write_json_metadata(
            metadata=metadata,
            json_path=output_folder / "metadata.json",
        )

        set_status("Extração concluída.")

        return {
            "watch_name": watch_name,
            "device_id": device_id,
            "selected_id": selected_id,
            "id_metadata": id_metadata,
            "source_paths": source_paths,
            "copied_sources": copied_sources,
            "output_folder": output_folder,
            "json_path": json_path,
        }