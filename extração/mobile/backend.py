from datetime import datetime
from pathlib import Path
from typing import Callable

from core.adb_client import AdbClient
from core.android_fs import AndroidFileSystem
from core.metadata_writer import write_json_metadata

from .config import MobileExtractionConfig
from .document_copier import MobileDocumentCopier
from .mobile_metadata import MobileMetadataBuilder
from .participant_id import ParticipantIdParser
from .participant_lookup import ParticipantLookup
from .participant_resolver import MobileParticipantResolver


StatusCallback = Callable[[str], None] | None
ParticipantIdPrompt = Callable[[str, str | None], str | None] | None


class MobileBackend:
    def __init__(
        self,
        config: MobileExtractionConfig | None = None,
    ) -> None:
        self.config = config or MobileExtractionConfig()

        self.adb = AdbClient(self.config.adb_path)
        self.android_fs = AndroidFileSystem(self.adb)

        self.participant_lookup = ParticipantLookup(
            self.config.participants_summary_csv
        )

        self.participant_resolver = MobileParticipantResolver(
            android_fs=self.android_fs,
            raw_ring_path=self.config.phone_raw_ring_path,
            participant_lookup=self.participant_lookup,
        )

        self.document_copier = MobileDocumentCopier(
            adb=self.adb,
            android_fs=self.android_fs,
            documents_path=self.config.phone_documents_path,
        )

        self.metadata_builder = MobileMetadataBuilder(
            config=self.config,
            adb=self.adb,
            android_fs=self.android_fs,
            participant_resolver=self.participant_resolver,
        )

    def get_output_root(self, collection_context: str) -> Path:
        return self.config.get_output_root(collection_context)

    @staticmethod
    def get_current_timestamp() -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @staticmethod
    def format_mobile_name(mobile_number: str) -> str:
        mobile_number = mobile_number.strip()

        if not mobile_number:
            raise RuntimeError("Número do mobile não pode ficar vazio.")

        if not mobile_number.isdigit():
            raise RuntimeError("O número do mobile deve conter apenas dígitos.")

        number = int(mobile_number)

        if number < 0 or number > 999:
            raise RuntimeError("O número do mobile deve estar entre 0 e 999.")

        return f"Mobile - {number:03d}"

    def check_device_connected(self) -> str:
        result = self.adb.run(["devices"])

        lines = result.stdout.splitlines()[1:]

        devices = [
            line.split()[0]
            for line in lines
            if line.strip() and "\tdevice" in line
        ]

        unauthorized = [
            line.split()[0]
            for line in lines
            if line.strip() and "\tunauthorized" in line
        ]

        offline = [
            line.split()[0]
            for line in lines
            if line.strip() and "\toffline" in line
        ]

        if unauthorized:
            raise RuntimeError(
                "Celular conectado, mas não autorizado.\n"
                "Desbloqueie o celular e aceite a permissão de depuração USB."
            )

        if offline:
            raise RuntimeError(
                f"Celular aparece como offline: {offline}\n"
                "Reconecte o cabo, aceite a depuração ou reinicie o ADB."
            )

        if not devices:
            raise RuntimeError(
                "Nenhum celular encontrado via ADB.\n"
                "Verifique o cabo, a depuração USB e rode: adb devices."
            )

        if len(devices) > 1:
            raise RuntimeError(
                f"Mais de um celular conectado: {devices}\n"
                "Conecte apenas um aparelho por vez."
            )

        return devices[0]

    @staticmethod
    def _validate_manual_participant_id(participant_id: str) -> str:
        participant_id = participant_id.strip()

        if not participant_id:
            raise RuntimeError("O ID do participante não pode ficar vazio.")

        if len(participant_id) > 100:
            raise RuntimeError(
                "O ID do participante é muito longo. "
                "Informe no máximo 100 caracteres."
            )

        if not all(
            character.isalnum() or character in {"-", "_"}
            for character in participant_id
        ):
            raise RuntimeError(
                "O ID informado contém caracteres inválidos.\n"
                "Use apenas letras, números, hífen (-) ou sublinhado (_)."
            )

        return participant_id

    def resolve_participant(
        self,
        participant_id_prompt: ParticipantIdPrompt = None,
    ) -> dict:
        try:
            return self.participant_resolver.resolve_from_phone()
        except RuntimeError as automatic_error:
            if participant_id_prompt is None:
                raise

            raw_metadata = self.participant_resolver.get_raw_ring_metadata()
            raw_ids = raw_metadata["ids_valid"]
            selected_raw_id = raw_metadata["selected_raw_id"]
            raw_lookup_key = (
                ParticipantIdParser.remove_id_prefix(selected_raw_id)
                if selected_raw_id
                else None
            )
            suggested_id = raw_lookup_key
            prompt_reason = str(automatic_error)

            while True:
                manual_id = participant_id_prompt(prompt_reason, suggested_id)

                if manual_id is None:
                    raise RuntimeError(
                        "Não foi possível identificar o participante "
                        "automaticamente e nenhum ID foi informado."
                    ) from automatic_error

                try:
                    participant_id = self._validate_manual_participant_id(manual_id)
                    break
                except RuntimeError as validation_error:
                    prompt_reason = str(validation_error)
                    suggested_id = manual_id.strip() or suggested_id

            return {
                "raw_ids": raw_ids,
                "selected_raw_id": selected_raw_id,
                "lookup_key": raw_lookup_key or participant_id,
                "participant_id": participant_id,
                "lookup_source": "manual_input",
                "matched_in_csv": False,
                "has_multiple_valid_ids": raw_metadata["has_multiple_valid_ids"],
                "multiple_valid_ids_count": raw_metadata[
                    "multiple_valid_ids_count"
                ],
                "multiple_valid_ids_warning": raw_metadata[
                    "multiple_valid_ids_warning"
                ],
                "automatic_resolution_error": str(automatic_error),
            }

    def inspect_phone_documents(
        self,
        status_callback: StatusCallback = None,
        participant_id_prompt: ParticipantIdPrompt = None,
    ) -> dict:
        def set_status(text: str) -> None:
            if status_callback:
                status_callback(text)

        set_status("Verificando celular conectado...")
        device_id = self.check_device_connected()

        set_status(f"Celular encontrado: {device_id}")

        set_status(f"Verificando pasta {self.config.phone_documents_path}...")
        self.android_fs.check_path_exists(self.config.phone_documents_path)

        set_status("Varrendo pasta Documents...")
        folder_summaries = self.android_fs.get_folder_summaries(
            self.config.phone_documents_path
        )

        participant_id = None
        participant_raw_id = None
        participant_lookup_source = None
        participant_matched_in_csv = None
        participant_id_error = None

        set_status("Buscando ID do participante...")

        try:
            participant_resolution = self.resolve_participant(
                participant_id_prompt=participant_id_prompt,
            )

            participant_id = participant_resolution["participant_id"]
            participant_raw_id = participant_resolution["selected_raw_id"]
            participant_lookup_source = participant_resolution["lookup_source"]
            participant_matched_in_csv = participant_resolution["matched_in_csv"]

        except RuntimeError as error:
            participant_id_error = str(error)

        set_status("Verificação concluída.")

        return {
            "device_id": device_id,
            "documents_path": self.config.phone_documents_path,
            "folders": folder_summaries,

            "participant_id": participant_id,
            "participant_raw_id": participant_raw_id,
            "participant_lookup_source": participant_lookup_source,
            "participant_matched_in_csv": participant_matched_in_csv,
            "participant_id_error": participant_id_error,
        }

    def extract_documents(
        self,
        mobile_number: str,
        collection_context: str,
        status_callback: StatusCallback = None,
        participant_id_prompt: ParticipantIdPrompt = None,
    ) -> dict:
        def set_status(text: str) -> None:
            if status_callback:
                status_callback(text)

        mobile_name = self.format_mobile_name(mobile_number)
        collection_context = self.config.normalize_collection_context(
            collection_context
        )
        collection_metadata = self.config.get_collection_context_metadata(
            collection_context
        )
        output_root = self.config.get_output_root(collection_context)
        timestamp = self.get_current_timestamp()

        set_status("Verificando celular conectado...")
        device_id = self.check_device_connected()

        set_status(f"Celular encontrado: {device_id}")

        set_status(f"Verificando pasta {self.config.phone_documents_path}...")
        self.android_fs.check_path_exists(self.config.phone_documents_path)

        set_status("Buscando ID do participante automaticamente...")
        participant_resolution = self.resolve_participant(
            participant_id_prompt=participant_id_prompt,
        )

        participant_id = participant_resolution["participant_id"]
        selected_raw_id = participant_resolution["selected_raw_id"]

        if participant_resolution["lookup_source"] == "manual_input":
            set_status(f"ID informado manualmente: {participant_id}")
        elif selected_raw_id != participant_id:
            set_status(f"ID encontrado: {selected_raw_id} -> {participant_id}")
        else:
            set_status(f"ID encontrado: {participant_id}")

        set_status(
            "Copiando arquivos para "
            f"{collection_metadata['label']}..."
        )
        set_status(
            "Copiando arquivos para "
            f"{collection_metadata['label']}..."
        )

        staging_folder, archive_path = (
            self.document_copier.copy_documents_to_staging(
                participant_id=participant_id,
                timestamp=timestamp,
                output_root=output_root,
            )
        )

        try:
            set_status("Criando JSON de metadados...")

            metadata = self.metadata_builder.build_metadata(
                participant_id=participant_id,
                mobile_name=mobile_name,
                staging_folder=staging_folder,
                archive_path=archive_path,
                output_root=output_root,
                device_id=device_id,
                timestamp=timestamp,
                participant_resolution=participant_resolution,
                collection_context=collection_context,
            )

            write_json_metadata(
                metadata=metadata,
                json_path=staging_folder / "metadata.json",
            )

            set_status("Compactando pacote em ZIP...")

            archive_path = self.document_copier.create_zip_archive(
                staging_folder=staging_folder,
                archive_path=archive_path,
            )

        finally:
            self.document_copier.cleanup_staging(staging_folder)

        set_status("Extração concluída.")

        return {
            "mobile_name": mobile_name,
            "device_id": device_id,

            "participant_id": participant_id,
            "raw_participant_id": selected_raw_id,
            "participant_lookup_source": participant_resolution[
                "lookup_source"
            ],
            "matched_in_csv": participant_resolution[
                "matched_in_csv"
            ],

            "collection_context": collection_context,
            "collection_context_code": collection_metadata["code"],
            "collection_context_label": collection_metadata["label"],
            "landing_folder": collection_metadata["folder_name"],

            "output_root": output_root,
            "output_archive": archive_path,
            "metadata_file": "metadata.json",
        }
