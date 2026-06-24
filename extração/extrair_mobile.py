import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


ADB_PATH = "adb"

PHONE_DOCUMENTS_PATH = "/sdcard/Documents"
OUTPUT_ROOT = Path("output")


def run_adb_command(args: list[str]) -> subprocess.CompletedProcess:
    """
    Executa comando ADB e retorna o resultado.
    """
    try:
        result = subprocess.run(
            [ADB_PATH, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        return result
    except FileNotFoundError:
        raise RuntimeError(
            "ADB não encontrado. Instale o Android Platform Tools "
            "ou coloque o adb no PATH do Windows."
        )


def check_device_connected() -> str:
    """
    Verifica se existe exatamente um celular conectado via ADB.
    """
    result = run_adb_command(["devices"])

    if result.returncode != 0:
        raise RuntimeError(f"Erro ao executar adb devices:\n{result.stderr}")

    lines = result.stdout.strip().splitlines()[1:]

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

    if unauthorized:
        raise RuntimeError(
            "Celular conectado, mas não autorizado.\n"
            "Desbloqueie o celular e aceite a permissão de depuração USB."
        )

    if not devices:
        raise RuntimeError(
            "Nenhum celular encontrado via ADB.\n"
            "Verifique o cabo, a depuração USB e rode: adb devices"
        )

    if len(devices) > 1:
        raise RuntimeError(
            f"Mais de um celular conectado: {devices}\n"
            "Conecte apenas um aparelho por vez, porque caos já basta o humano."
        )

    return devices[0]


def check_phone_documents_exists() -> None:
    """
    Verifica se a pasta Documents existe no celular.
    """
    result = run_adb_command(["shell", "ls", PHONE_DOCUMENTS_PATH])

    if result.returncode != 0:
        raise RuntimeError(
            f"Não consegui acessar {PHONE_DOCUMENTS_PATH} no celular.\n"
            f"Erro:\n{result.stderr}"
        )


def sanitize_folder_name(value: str) -> str:
    """
    Remove caracteres problemáticos para nome de pasta.
    """
    value = value.strip()

    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        value = value.replace(char, "_")

    return value


def copy_documents_to_output(participant_id: str) -> Path:
    """
    Copia tudo de /sdcard/Documents para output/<participant_id>.
    """
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    destination_folder = OUTPUT_ROOT / participant_id

    if destination_folder.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination_folder = OUTPUT_ROOT / f"{participant_id}_{timestamp}"

    destination_folder.mkdir(parents=True, exist_ok=True)

    result = run_adb_command([
        "pull",
        PHONE_DOCUMENTS_PATH,
        str(destination_folder)
    ])

    if result.returncode != 0:
        if destination_folder.exists():
            shutil.rmtree(destination_folder, ignore_errors=True)

        raise RuntimeError(
            "Erro ao copiar arquivos do celular.\n"
            f"Comando: adb pull {PHONE_DOCUMENTS_PATH} {destination_folder}\n"
            f"Erro:\n{result.stderr}"
        )

    return destination_folder


def create_metadata_json(participant_id: str, destination_folder: Path, device_id: str) -> Path:
    """
    Cria um JSON com o mesmo nome da pasta de saída.
    Exemplo:
    output/ABC123/
    output/ABC123.json
    """
    json_path = OUTPUT_ROOT / f"{destination_folder.name}.json"

    metadata = {
        "participant_id": participant_id,
        "device_id": device_id,
        "source_path": PHONE_DOCUMENTS_PATH,
        "output_folder": str(destination_folder),
        "extracted_at": datetime.now().isoformat(timespec="seconds"),
        "status": "success"
    }

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=4)

    return json_path


def main() -> None:
    print("=== Extração de arquivos do celular ===")

    participant_id = input("Informe o ID do participante: ")
    participant_id = sanitize_folder_name(participant_id)

    if not participant_id:
        raise RuntimeError("ID do participante não pode ficar vazio.")

    print("\nVerificando celular conectado...")
    device_id = check_device_connected()
    print(f"Celular encontrado: {device_id}")

    print(f"\nVerificando pasta {PHONE_DOCUMENTS_PATH}...")
    check_phone_documents_exists()

    print("\nCopiando arquivos para a pasta output...")
    destination_folder = copy_documents_to_output(participant_id)

    print("\nCriando arquivo JSON de metadados...")
    json_path = create_metadata_json(
        participant_id=participant_id,
        destination_folder=destination_folder,
        device_id=device_id
    )

    print("\nExtração finalizada.")
    print(f"Pasta criada: {destination_folder}")
    print(f"JSON criado: {json_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("\nErro na extração:")
        print(error)