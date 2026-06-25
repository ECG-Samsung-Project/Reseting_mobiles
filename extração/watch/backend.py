import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Callable


ADB_PATH = "adb"
WATCH_DOCUMENTS_PATH = "/sdcard/Documents"

OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "output"

WATCH_ID_REGEX = re.compile(r"([A-Z]{3}-\d{2}-\d{4})", re.IGNORECASE)

StatusCallback = Callable[[str], None] | None


class WatchBackend:
    def __init__(
        self,
        adb_path: str = ADB_PATH,
        output_root: Path = OUTPUT_ROOT,
    ) -> None:
        self.adb_path = adb_path
        self.output_root = output_root
        self.target_device_id: str | None = None

    def run_command(
        self,
        command: list[str],
        input_text: str | None = None,
    ) -> str:
        result = subprocess.run(
            command,
            input=input_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())

        return result.stdout.strip()

    def run_adb_command(
        self,
        args: list[str],
        input_text: str | None = None,
    ) -> str:
        commands_without_device = {
            "version",
            "devices",
            "pair",
            "connect",
            "disconnect",
            "kill-server",
            "start-server",
        }

        if (
            self.target_device_id
            and args
            and args[0] not in commands_without_device
        ):
            command = [self.adb_path, "-s", self.target_device_id, *args]
        else:
            command = [self.adb_path, *args]

        return self.run_command(command, input_text=input_text)

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
    def validate_ip(ip: str) -> str:
        ip = ip.strip()

        if not ip:
            raise RuntimeError("Informe o IP do relógio.")

        if ":" in ip:
            raise RuntimeError(
                "Informe apenas o IP, sem porta.\n\n"
                "Exemplo correto: 30.0.0.218\n"
                "Exemplo errado: 30.0.0.218:34347"
            )

        return ip

    @staticmethod
    def validate_port(port: str, field_name: str) -> str:
        port = port.strip()

        if not port:
            raise RuntimeError(f"Informe a {field_name}.")

        if not port.isdigit():
            raise RuntimeError(f"A {field_name} deve conter apenas números.")

        port_number = int(port)

        if port_number < 1 or port_number > 65535:
            raise RuntimeError(f"A {field_name} deve estar entre 1 e 65535.")

        return port

    def build_address(self, ip: str, port: str) -> str:
        return f"{ip}:{port}"

    def get_pairing_address(self, ip: str, pairing_port: str) -> str:
        ip = self.validate_ip(ip)
        pairing_port = self.validate_port(
            pairing_port,
            "porta de pareamento",
        )

        return self.build_address(ip, pairing_port)

    def get_connect_address(self, ip: str, connect_port: str) -> str:
        ip = self.validate_ip(ip)
        connect_port = self.validate_port(
            connect_port,
            "porta de conexão",
        )

        return self.build_address(ip, connect_port)

    @staticmethod
    def normalize_watch_id(value: str) -> str:
        return value.strip().upper()

    def extract_watch_ids_from_text(self, text: str) -> list[str]:
        matches = WATCH_ID_REGEX.findall(text)

        watch_ids = []

        for match in matches:
            watch_id = self.normalize_watch_id(match)

            if watch_id not in watch_ids:
                watch_ids.append(watch_id)

        return watch_ids

    def check_adb_installed(self) -> None:
        try:
            self.run_adb_command(["version"])
        except Exception:
            raise RuntimeError(
                "ADB não encontrado. Instale o Android Platform Tools e coloque o adb no PATH."
            )

    def get_connected_devices(self) -> list[str]:
        output = self.run_adb_command(["devices"])

        devices = []

        for line in output.splitlines()[1:]:
            line = line.strip()

            if not line:
                continue

            if "\tdevice" in line:
                device_id = line.split("\t")[0]
                devices.append(device_id)

            elif "\tunauthorized" in line:
                raise RuntimeError(
                    "Dispositivo conectado, mas não autorizado.\n\n"
                    "Olhe a tela do relógio e aceite a depuração USB/Wi-Fi."
                )

            elif "\toffline" in line:
                raise RuntimeError(
                    "Dispositivo aparece como offline.\n\n"
                    "Desconecte e conecte novamente, ou reinicie o ADB."
                )

        return devices

    def get_target_device_id(
        self,
        devices: list[str],
        connect_address: str,
    ) -> str:
        if connect_address in devices:
            return connect_address

        if self.target_device_id and self.target_device_id in devices:
            return self.target_device_id

        if len(devices) == 1:
            return devices[0]

        raise RuntimeError(
            "Mais de um dispositivo conectado, e não consegui identificar o relógio alvo.\n\n"
            f"Dispositivos encontrados:\n{devices}\n\n"
            "Confira se o IP e a porta de conexão estão exatamente iguais ao que aparece no adb devices.\n"
            "Exemplo: 30.0.0.218:34347"
        )

    def pair_watch(
        self,
        ip: str,
        pairing_port: str,
        pairing_code: str,
    ) -> str:
        pairing_address = self.get_pairing_address(ip, pairing_port)
        pairing_code = pairing_code.strip()

        if not pairing_code:
            raise RuntimeError("Informe a senha/código de pareamento.")

        return self.run_adb_command(
            ["pair", pairing_address],
            input_text=f"{pairing_code}\n",
        )

    def connect_watch(
        self,
        ip: str,
        connect_port: str,
    ) -> tuple[str, str]:
        connect_address = self.get_connect_address(ip, connect_port)

        output = self.run_adb_command(["connect", connect_address])

        self.target_device_id = connect_address

        return output, self.target_device_id

    def disconnect_all_devices(self) -> str:
        output = self.run_adb_command(["disconnect"])
        self.target_device_id = None

        return output

    def check_watch_documents_exists(self) -> None:
        try:
            self.run_adb_command(["shell", "ls", WATCH_DOCUMENTS_PATH])
        except Exception as error:
            raise RuntimeError(
                f"Não consegui acessar {WATCH_DOCUMENTS_PATH} no relógio.\n\n"
                f"Erro:\n{error}"
            )

    def get_watch_file_paths(self) -> list[str]:
        try:
            output = self.run_adb_command(
                [
                    "shell",
                    "find",
                    WATCH_DOCUMENTS_PATH,
                    "-type",
                    "f",
                ]
            )
        except Exception:
            return []

        return [
            line.strip()
            for line in output.splitlines()
            if line.strip()
        ]

    def get_selected_watch_id(self) -> tuple[str, dict]:
        files = self.get_watch_file_paths()
        text = "\n".join(files)

        watch_ids = self.extract_watch_ids_from_text(text)

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
                "Mais de um ID de relógio encontrado. A extração foi feita normalmente usando o primeiro ID para nomear a pasta."
                if len(watch_ids) > 1
                else None
            ),
            "sample_files": [Path(file).name for file in files[:10]],
        }

        return selected_id, id_metadata

    def get_adb_shell_output(self, args: list[str]) -> str | None:
        try:
            value = self.run_adb_command(["shell", *args]).strip()
        except Exception:
            return None

        return value if value else None

    def get_watch_property(self, prop_name: str) -> str | None:
        return self.get_adb_shell_output(["getprop", prop_name])

    def get_watch_metadata(self, device_id: str, watch_name: str) -> dict:
        return {
            "watch_name": watch_name,
            "adb_device_id": device_id,
            "manufacturer": self.get_watch_property("ro.product.manufacturer"),
            "brand": self.get_watch_property("ro.product.brand"),
            "model": self.get_watch_property("ro.product.model"),
            "device": self.get_watch_property("ro.product.device"),
            "product_name": self.get_watch_property("ro.product.name"),
            "android_version": self.get_watch_property("ro.build.version.release"),
            "android_sdk": self.get_watch_property("ro.build.version.sdk"),
            "build_id": self.get_watch_property("ro.build.id"),
            "build_fingerprint": self.get_watch_property("ro.build.fingerprint"),
            "serial_number": self.get_watch_property("ro.serialno"),
        }

    def get_watch_path_summary(self, path: str) -> dict:
        try:
            files_output = self.run_adb_command(
                [
                    "shell",
                    "find",
                    path,
                    "-type",
                    "f",
                ]
            )
            files = [
                line.strip()
                for line in files_output.splitlines()
                if line.strip()
            ]
        except Exception:
            files = []

        try:
            dirs_output = self.run_adb_command(
                [
                    "shell",
                    "find",
                    path,
                    "-type",
                    "d",
                ]
            )
            dirs = [
                line.strip()
                for line in dirs_output.splitlines()
                if line.strip()
            ]
        except Exception:
            dirs = []

        size_kb = None

        try:
            size_output = self.run_adb_command(
                [
                    "shell",
                    "du",
                    "-sk",
                    path,
                ]
            )

            if size_output:
                first_part = size_output.split()[0]

                if first_part.isdigit():
                    size_kb = int(first_part)
        except Exception:
            pass

        return {
            "path": path,
            "file_count": len(files),
            "folder_count": len(dirs),
            "size_kb": size_kb,
            "size_mb": round(size_kb / 1024, 2) if size_kb is not None else None,
            "sample_files": [Path(file).name for file in files[:10]],
        }

    @staticmethod
    def get_local_output_summary(destination_folder: Path) -> dict:
        files = [item for item in destination_folder.rglob("*") if item.is_file()]
        folders = [item for item in destination_folder.rglob("*") if item.is_dir()]

        total_size_bytes = sum(file.stat().st_size for file in files)

        extensions: dict[str, int] = {}

        for file in files:
            suffix = file.suffix.lower() if file.suffix else "[sem_extensao]"
            extensions[suffix] = extensions.get(suffix, 0) + 1

        return {
            "local_file_count": len(files),
            "local_folder_count": len(folders),
            "total_size_bytes": total_size_bytes,
            "total_size_mb": round(total_size_bytes / 1024 / 1024, 2),
            "extensions": extensions,
        }

    def pull_documents(self, selected_id: str, timestamp: str) -> Path:
        self.output_root.mkdir(parents=True, exist_ok=True)

        folder_name = f"{selected_id}_{timestamp}"
        destination_folder = self.output_root / folder_name

        if destination_folder.exists():
            counter = 2

            while destination_folder.exists():
                destination_folder = self.output_root / f"{folder_name}_{counter}"
                counter += 1

        destination_folder.mkdir(parents=True, exist_ok=True)

        self.run_adb_command(
            [
                "pull",
                WATCH_DOCUMENTS_PATH,
                str(destination_folder),
            ]
        )

        return destination_folder

    @staticmethod
    def get_optional_address(ip: str, port: str) -> str | None:
        ip = ip.strip()
        port = port.strip()

        if not ip or not port:
            return None

        return f"{ip}:{port}"

    def create_metadata_json(
        self,
        selected_id: str,
        id_metadata: dict,
        watch_name: str,
        destination_folder: Path,
        device_id: str,
        timestamp: str,
        connection: dict,
    ) -> Path:
        json_path = self.output_root / f"{destination_folder.name}.json"

        extracted_at = datetime.now()

        watch_metadata = self.get_watch_metadata(
            device_id=device_id,
            watch_name=watch_name,
        )

        documents_summary = self.get_watch_path_summary(WATCH_DOCUMENTS_PATH)
        local_output_summary = self.get_local_output_summary(destination_folder)

        metadata = {
            "watch_id": selected_id,
            "selected_id": selected_id,
            "watch_name": watch_name,
            "connection": {
                "ip": connection["ip"],
                "pairing_port": connection["pairing_port"] or None,
                "connect_port": connection["connect_port"] or None,
                "pairing_address": self.get_optional_address(
                    connection["ip"],
                    connection["pairing_port"],
                ),
                "connect_address": self.get_optional_address(
                    connection["ip"],
                    connection["connect_port"],
                ),
                "target_device_id": self.target_device_id,
            },
            "extraction_name": destination_folder.name,
            "timestamp": timestamp,
            "extracted_at": extracted_at.isoformat(timespec="seconds"),
            "status": "success",
            "warnings": {
                "has_valid_id": id_metadata["has_valid_id"],
                "has_multiple_valid_ids": id_metadata["has_multiple_valid_ids"],
                "multiple_valid_ids_count": id_metadata["multiple_valid_ids_count"],
                "multiple_valid_ids_warning": id_metadata["multiple_valid_ids_warning"],
            },
            "source": {
                "documents_path": WATCH_DOCUMENTS_PATH,
            },
            "output": {
                "output_root": str(self.output_root),
                "output_folder": str(destination_folder),
                "metadata_json": str(json_path),
            },
            "watch": watch_metadata,
            "id_summary": id_metadata,
            "watch_documents_summary": documents_summary,
            "local_output_summary": local_output_summary,
        }

        with json_path.open("w", encoding="utf-8") as file:
            json.dump(metadata, file, ensure_ascii=False, indent=4)

        return json_path

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
        connect_address = self.get_connect_address(ip, connect_port)

        set_status("Verificando ADB...")
        self.check_adb_installed()

        set_status("Verificando relógio conectado...")
        devices = self.get_connected_devices()

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

        device_id = self.get_target_device_id(
            devices=devices,
            connect_address=connect_address,
        )

        self.target_device_id = device_id

        set_status(f"Usando dispositivo: {device_id}")

        set_status("Verificando /sdcard/Documents...")
        self.check_watch_documents_exists()

        set_status("Buscando ID MMZ nos arquivos...")
        selected_id, id_metadata = self.get_selected_watch_id()

        set_status("Copiando /sdcard/Documents para output...")
        output_folder = self.pull_documents(
            selected_id=selected_id,
            timestamp=timestamp,
        )

        set_status("Criando JSON de metadados...")
        json_path = self.create_metadata_json(
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

        set_status("Extração concluída.")

        return {
            "watch_name": watch_name,
            "device_id": device_id,
            "selected_id": selected_id,
            "output_folder": output_folder,
            "json_path": json_path,
        }