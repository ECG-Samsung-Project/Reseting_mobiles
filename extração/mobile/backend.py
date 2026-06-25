import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable

from core.adb_client import AdbClient
from core.android_metadata import get_android_device_metadata
from core.local_summary import get_local_output_summary

from .config import MobileExtractionConfig
from .participant_id import ParticipantIdParser


StatusCallback = Callable[[str], None] | None


class MobileBackend:
    def __init__(
        self,
        config: MobileExtractionConfig | None = None,
    ) -> None:
        self.config = config or MobileExtractionConfig()
        self.adb = AdbClient(self.config.adb_path)

        self.output_root = self.config.output_root
        self.output_root.mkdir(parents=True, exist_ok=True)

    def get_document_folder_paths(self) -> list[str]:
        command = (
            f'for d in "{self.config.phone_documents_path}"/*; do '
            f'[ -d "$d" ] && echo "$d"; '
            f'done'
        )

        result = self.adb.run(["shell", command], check=False)

        if result.returncode != 0:
            raise RuntimeError(
                f"Não consegui varrer {self.config.phone_documents_path}.\n"
                f"Erro:\n{result.stderr or result.stdout}"
            )

        return [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]

    def get_document_folder_summaries(self) -> list[dict]:
        folder_paths = self.get_document_folder_paths()

        summaries = []

        for folder_path in folder_paths:
            folder_name = folder_path.rstrip("/").split("/")[-1]
            summary = self.get_phone_path_summary(folder_path)

            summaries.append(
                {
                    "folder_name": folder_name,
                    "folder_path": folder_path,
                    "file_count": summary["file_count"],
                    "folder_count": summary["folder_count"],
                    "size_mb": summary["size_mb"],
                    "sample_files": summary.get("sample_files", []),
                }
            )

        return sorted(
            summaries,
            key=lambda item: item["folder_name"].lower(),
        )

    def inspect_phone_documents(
        self,
        status_callback: StatusCallback = None,
    ) -> dict:
        def set_status(text: str) -> None:
            if status_callback:
                status_callback(text)

        set_status("Verificando celular conectado...")
        device_id = self.check_device_connected()

        set_status(f"Celular encontrado: {device_id}")

        set_status(f"Verificando pasta {self.config.phone_documents_path}...")
        self.check_phone_documents_exists()

        set_status("Varrendo pasta Documents...")
        folder_summaries = self.get_document_folder_summaries()

        participant_id = None
        participant_id_error = None

        set_status("Buscando ID do participante...")
        try:
            participant_id = self.get_participant_id_from_phone()
        except RuntimeError as error:
            participant_id_error = str(error)

        set_status("Verificação concluída.")

        return {
            "device_id": device_id,
            "documents_path": self.config.phone_documents_path,
            "folders": folder_summaries,
            "participant_id": participant_id,
            "participant_id_error": participant_id_error,
        }

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

    def check_phone_documents_exists(self) -> None:
        result = self.adb.run(
            ["shell", "ls", self.config.phone_documents_path],
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Não consegui acessar {self.config.phone_documents_path} no celular.\n"
                f"Erro:\n{result.stderr or result.stdout}"
            )

    def get_raw_ring_file_paths(self) -> list[str]:
        result = self.adb.run(
            [
                "shell",
                "find",
                self.config.phone_raw_ring_path,
                "-type",
                "f",
            ],
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Não consegui listar os arquivos em {self.config.phone_raw_ring_path}.\n"
                "Confirme se a pasta RAW_DATA_RING existe dentro de Documents.\n"
                f"Erro:\n{result.stderr or result.stdout}"
            )

        return [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]

    def get_participant_id_from_phone(self) -> str:
        files = self.get_raw_ring_file_paths()
        text = "\n".join(files)

        participant_ids = ParticipantIdParser.extract_valid_ids(text)

        if not participant_ids:
            raise RuntimeError(
                "Não encontrei nenhum ID válido dentro da pasta RAW_DATA_RING.\n"
                "IDs com 5 zeros seguidos são ignorados.\n"
                "Exemplo esperado:\n"
                "RingSleepSpO2_Id26321088_DevDAE3_NoDev_..."
            )

        return participant_ids[0]

    def get_phone_path_summary(self, phone_path: str) -> dict:
        files = self.adb.list_files(phone_path, check=False)
        dirs = self.adb.list_dirs(phone_path, check=False)
        size_kb = self.adb.get_path_size_kb(phone_path)

        return {
            "path": phone_path,
            "file_count": len(files),
            "folder_count": len(dirs),
            "size_kb": size_kb,
            "size_mb": round(size_kb / 1024, 2) if size_kb is not None else None,
            "sample_files": [Path(file).name for file in files[:10]],
        }

    def get_raw_ring_metadata(self) -> dict:
        try:
            files = self.get_raw_ring_file_paths()
        except RuntimeError:
            files = []

        text = "\n".join(files)

        valid_ids = ParticipantIdParser.extract_valid_ids(text)
        ignored_ids = ParticipantIdParser.extract_ignored_ids(text)
        all_ids_found = ParticipantIdParser.extract_all_ids(text)

        file_names = [Path(file).name for file in files]

        return {
            "raw_ring_path": self.config.phone_raw_ring_path,
            "raw_ring_file_count": len(files),

            "ids_found_raw": all_ids_found,
            "ids_valid": valid_ids,
            "ignored_ids": ignored_ids,
            "ignored_rule": "IDs que contêm 5 zeros seguidos nos dígitos são ignorados.",

            "selected_id": valid_ids[0] if valid_ids else None,
            "has_multiple_valid_ids": len(valid_ids) > 1,
            "multiple_valid_ids_count": len(valid_ids),
            "multiple_valid_ids_warning": (
                "Mais de um ID válido encontrado na RAW_DATA_RING. "
                "A extração foi feita normalmente usando o primeiro ID válido para nomear a pasta."
                if len(valid_ids) > 1
                else None
            ),

            "sample_files": file_names[:10],
        }

    def build_destination_folder(
        self,
        participant_id: str,
        timestamp: str,
    ) -> Path:
        folder_name = f"{participant_id}_{timestamp}"
        destination_folder = self.output_root / folder_name

        if not destination_folder.exists():
            return destination_folder

        counter = 2

        while True:
            candidate = self.output_root / f"{folder_name}_{counter}"

            if not candidate.exists():
                return candidate

            counter += 1

    def copy_documents_to_output(
        self,
        participant_id: str,
        timestamp: str,
    ) -> Path:
        self.output_root.mkdir(parents=True, exist_ok=True)

        destination_folder = self.build_destination_folder(
            participant_id=participant_id,
            timestamp=timestamp,
        )

        destination_folder.mkdir(parents=True, exist_ok=True)

        result = self.adb.run(
            [
                "pull",
                self.config.phone_documents_path,
                str(destination_folder),
            ],
            check=False,
        )

        if result.returncode != 0:
            shutil.rmtree(destination_folder, ignore_errors=True)

            raise RuntimeError(
                "Erro ao copiar arquivos do celular.\n"
                f"Comando: adb pull {self.config.phone_documents_path} {destination_folder}\n"
                f"Erro:\n{result.stderr or result.stdout}"
            )

        return destination_folder

    def create_metadata_json(
        self,
        participant_id: str,
        mobile_name: str,
        destination_folder: Path,
        device_id: str,
        timestamp: str,
    ) -> Path:
        json_path = self.output_root / f"{destination_folder.name}.json"

        extracted_at = datetime.now()
        raw_ring_metadata = self.get_raw_ring_metadata()

        metadata = {
            "data_type": "mobile",
            "source_type": "mobile_data",

            "participant_id": participant_id,
            "id_participant": participant_id,

            "mobile_name": mobile_name,

            "extraction_name": destination_folder.name,
            "package_name": destination_folder.name,

            "timestamp": timestamp,
            "collected_date": extracted_at.strftime("%Y-%m-%d"),
            "extracted_at": extracted_at.isoformat(timespec="seconds"),

            "status": "success",

            "warnings": {
                "has_multiple_valid_ids": raw_ring_metadata["has_multiple_valid_ids"],
                "multiple_valid_ids_count": raw_ring_metadata["multiple_valid_ids_count"],
                "multiple_valid_ids_warning": raw_ring_metadata["multiple_valid_ids_warning"],
            },

            "source": {
                "documents_path": self.config.phone_documents_path,
                "raw_ring_path": self.config.phone_raw_ring_path,
            },

            "output": {
                "output_root": str(self.output_root),
                "output_folder": str(destination_folder),
                "metadata_json": str(json_path),
            },

            "phone": get_android_device_metadata(
                adb=self.adb,
                device_id=device_id,
                device_name=mobile_name,
                name_field="mobile_name",
            ),

            "phone_documents_summary": self.get_phone_path_summary(
                self.config.phone_documents_path,
            ),

            "raw_ring_summary": raw_ring_metadata,

            "local_output_summary": get_local_output_summary(destination_folder),
        }

        with json_path.open("w", encoding="utf-8") as file:
            json.dump(metadata, file, ensure_ascii=False, indent=4)

        return json_path

    def extract_documents(
        self,
        mobile_number: str,
        status_callback: StatusCallback = None,
    ) -> dict:
        def set_status(text: str) -> None:
            if status_callback:
                status_callback(text)

        mobile_name = self.format_mobile_name(mobile_number)
        timestamp = self.get_current_timestamp()

        set_status("Verificando celular conectado...")
        device_id = self.check_device_connected()

        set_status(f"Celular encontrado: {device_id}")

        set_status(f"Verificando pasta {self.config.phone_documents_path}...")
        self.check_phone_documents_exists()

        set_status("Buscando ID do participante automaticamente...")
        participant_id = self.get_participant_id_from_phone()

        set_status(f"ID encontrado: {participant_id}")

        set_status("Copiando arquivos para landing...")
        destination_folder = self.copy_documents_to_output(
            participant_id=participant_id,
            timestamp=timestamp,
        )

        set_status("Criando JSON de metadados...")
        json_path = self.create_metadata_json(
            participant_id=participant_id,
            mobile_name=mobile_name,
            destination_folder=destination_folder,
            device_id=device_id,
            timestamp=timestamp,
        )

        set_status("Extração concluída.")

        return {
            "mobile_name": mobile_name,
            "device_id": device_id,
            "participant_id": participant_id,
            "output_folder": destination_folder,
            "json_path": json_path,
        }