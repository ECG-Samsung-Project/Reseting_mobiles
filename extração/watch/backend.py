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
from .watch_id import WatchIdParser
from .watch_id_resolver import WatchIdResolver
from .watch_metadata import WatchMetadataBuilder

StatusCallback = Callable[[str], None] | None
WatchIdPrompt = Callable[[str, str | None], str | None] | None


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

        self.config.landing_watch_base_root.mkdir(
            parents=True,
            exist_ok=True,
        )

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

    @staticmethod
    def validate_manual_watch_id(watch_id: str) -> str:
        normalized = WatchIdParser.normalize(watch_id)

        if not WatchIdParser.is_valid(normalized):
            raise RuntimeError(
                "ID inválido. Use o formato ABC-12-3456.\n"
                "Exemplo: HCM-32-3881."
            )

        return normalized

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

    # Proxies mantidos para não quebrar chamadas existentes do frontend.
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
        watch_id_prompt: WatchIdPrompt = None,
    ) -> tuple[str, dict]:
        ids_found: list[str] = []
        source_results: list[dict] = []
        resolver_errors: list[str] = []
        sample_files: list[str] = []
        selected_source_path: str | None = None

        for source_path in source_paths:
            try:
                resolver = WatchIdResolver(
                    android_fs=self.android_fs,
                    documents_path=source_path,
                )

                _, id_metadata = resolver.resolve_from_watch()

                ids_from_source = id_metadata.get("ids_valid", [])

                source_results.append(
                    {
                        "source_path": source_path,
                        "ids_found": ids_from_source,
                        "sample_files": id_metadata.get("sample_files", []),
                    }
                )

                for sample_file in id_metadata.get("sample_files", []):
                    if sample_file not in sample_files:
                        sample_files.append(sample_file)

                for current_id in ids_from_source:
                    normalized_id = WatchIdParser.normalize(current_id)

                    if normalized_id not in ids_found:
                        ids_found.append(normalized_id)

                        if selected_source_path is None:
                            selected_source_path = source_path

            except Exception as exc:
                resolver_errors.append(f"{source_path}: {exc}")

        if ids_found:
            selected_id = ids_found[0]

            return selected_id, {
                "id_type": "participant_id",
                "id_pattern": "ABC-12-3456",
                "ids_found_raw": ids_found,
                "ids_valid": ids_found,
                "selected_id": selected_id,
                "has_valid_id": True,
                "automatic_id_found": True,
                "resolution_source": "watch_files",
                "has_multiple_valid_ids": len(ids_found) > 1,
                "multiple_valid_ids_count": len(ids_found),
                "multiple_valid_ids_warning": (
                    "Mais de um ID válido foi encontrado nas pastas do relógio. "
                    "A extração usou o primeiro ID encontrado."
                    if len(ids_found) > 1
                    else None
                ),
                "source_path": selected_source_path,
                "source_results": source_results,
                "resolver_errors": resolver_errors,
                "sample_files": sample_files[:10],
                "warning": None,
            }

        error_lines = [
            "Não encontrei um ID no formato ABC-12-3456 nos arquivos do relógio."
        ]

        if resolver_errors:
            error_lines.append("")
            error_lines.append("Erros durante a busca:")
            error_lines.extend(f"- {error}" for error in resolver_errors)

        prompt_reason = "\n".join(error_lines)

        if watch_id_prompt is None:
            raise RuntimeError(
                f"{prompt_reason}\n\n"
                "Informe manualmente o ID do participante para continuar."
            )

        suggested_id: str | None = None

        while True:
            manual_id = watch_id_prompt(prompt_reason, suggested_id)

            if manual_id is None:
                raise RuntimeError(
                    "Não foi possível identificar o participante "
                    "automaticamente e nenhum ID foi informado."
                )

            try:
                selected_id = self.validate_manual_watch_id(manual_id)
                break
            except RuntimeError as validation_error:
                prompt_reason = str(validation_error)
                suggested_id = manual_id.strip() or suggested_id

        return selected_id, {
            "id_type": "participant_id",
            "id_pattern": "ABC-12-3456",
            "ids_found_raw": [],
            "ids_valid": [],
            "selected_id": selected_id,
            "has_valid_id": True,
            "automatic_id_found": False,
            "resolution_source": "manual_input",
            "manual_id": selected_id,
            "has_multiple_valid_ids": False,
            "multiple_valid_ids_count": 0,
            "multiple_valid_ids_warning": None,
            "source_path": None,
            "source_results": source_results,
            "resolver_errors": resolver_errors,
            "sample_files": sample_files[:10],
            "warning": (
                "ID não encontrado automaticamente. "
                "O participante foi informado manualmente."
            ),
        }

    def copy_watch_sources_to_staging(
        self,
        source_paths: list[str],
        selected_id: str,
        timestamp: str,
        output_root: Path,
    ) -> tuple[Path, Path, list[str]]:
        package_name = f"{selected_id}_{timestamp}"

        archive_path = WatchDocumentCopier.build_unique_archive_path(
            output_root=output_root,
            package_name=package_name,
        )

        staging_folder = WatchDocumentCopier.create_staging_folder(
            archive_path=archive_path,
        )

        copied_sources: list[str] = []
        errors: list[str] = []

        try:
            for index, source_path in enumerate(source_paths, start=1):
                source_staging = (
                    staging_folder.parent
                    / f"source_{index:02d}"
                )

                try:
                    copier = WatchDocumentCopier(
                        adb=self.adb,
                        android_fs=self.android_fs,
                        documents_path=source_path,
                    )

                    copier.copy_documents_to_staging(
                        destination_folder=source_staging,
                    )

                    merge_local_folder_contents(
                        source_folder=source_staging,
                        destination_folder=staging_folder,
                    )

                    copied_sources.append(source_path)

                except Exception as exc:
                    errors.append(f"{source_path}: {exc}")

            if not copied_sources:
                error_text = "\n".join(
                    f"- {error}"
                    for error in errors
                )

                raise RuntimeError(
                    "Nenhuma pasta com arquivos pôde ser copiada do relógio.\n\n"
                    "É necessário que pelo menos Download ou Documents "
                    "tenha arquivos disponíveis."
                    + (
                        f"\n\nDetalhes:\n{error_text}"
                        if error_text
                        else ""
                    )
                )

            # Se uma estiver vazia, a outra será usada normalmente.
            return staging_folder, archive_path, copied_sources

        except Exception:
            WatchDocumentCopier.cleanup_staging(staging_folder)
            raise

    def inspect_watch_documents(
        self,
        ip: str,
        connect_port: str,
        status_callback: StatusCallback = None,
        watch_id_prompt: WatchIdPrompt = None,
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
            watch_id_prompt=watch_id_prompt,
        )

        set_status("Varredura concluída.")

        return {
            "device_id": device_id,
            "selected_id": selected_id,
            "id_metadata": id_metadata,
            "id_resolution_source": id_metadata.get("resolution_source"),
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
        collection_context: str,
        status_callback: StatusCallback = None,
        watch_id_prompt: WatchIdPrompt = None,
    ) -> dict:
        def set_status(text: str) -> None:
            if status_callback:
                status_callback(text)

        watch_name = self.format_watch_name(watch_number)
        timestamp = self.get_current_timestamp()

        collection_context = self.config.normalize_collection_context(
            collection_context
        )
        collection_metadata = self.config.get_collection_context_metadata(
            collection_context
        )
        output_root = self.config.get_output_root(collection_context)

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
            watch_id_prompt=watch_id_prompt,
        )

        if id_metadata.get("resolution_source") == "manual_input":
            set_status(f"ID informado manualmente: {selected_id}")
        else:
            set_status(f"ID encontrado: {selected_id}")

        set_status(
            "Copiando Download e Documents para "
            f"{collection_metadata['label']}..."
        )

        staging_folder, archive_path, copied_sources = (
            self.copy_watch_sources_to_staging(
                source_paths=source_paths,
                selected_id=selected_id,
                timestamp=timestamp,
                output_root=output_root,
            )
        )

        try:
            set_status("Criando JSON de metadados...")

            metadata = self.metadata_builder.build_metadata(
                selected_id=selected_id,
                id_metadata=id_metadata,
                watch_name=watch_name,
                staging_folder=staging_folder,
                archive_path=archive_path,
                output_root=output_root,
                device_id=device_id,
                timestamp=timestamp,
                connection={
                    "ip": ip.strip(),
                    "pairing_port": pairing_port.strip(),
                    "connect_port": connect_port.strip(),
                },
                collection_context=collection_context,
                source_paths=source_paths,
                copied_sources=copied_sources,
            )

            write_json_metadata(
                metadata=metadata,
                json_path=staging_folder / "metadata.json",
            )

            set_status("Compactando pacote em ZIP...")

            archive_path = WatchDocumentCopier.create_zip_archive(
                staging_folder=staging_folder,
                archive_path=archive_path,
            )

        finally:
            WatchDocumentCopier.cleanup_staging(staging_folder)

        set_status("Extração concluída.")

        return {
            "watch_name": watch_name,
            "device_id": device_id,
            "selected_id": selected_id,
            "id_metadata": id_metadata,
            "id_resolution_source": id_metadata.get("resolution_source"),
            "source_paths": source_paths,
            "copied_sources": copied_sources,
            "collection_context": collection_context,
            "collection_context_code": collection_metadata["code"],
            "collection_context_label": collection_metadata["label"],
            "landing_folder": collection_metadata["folder_name"],
            "output_root": output_root,
            "output_archive": archive_path,
            "metadata_file": "metadata.json",
        }