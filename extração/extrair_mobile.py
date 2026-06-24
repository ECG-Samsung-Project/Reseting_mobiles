import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


ADB_PATH = "adb"

PHONE_DOCUMENTS_PATH = "/sdcard/Documents"
PHONE_RAW_RING_PATH = "/sdcard/Documents/RAW_DATA_RING"

# Salvar output em uma pasta chamada "output" no diretório acima do atual.
OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "output"

PARTICIPANT_ID_REGEX = re.compile(r"(Id\d+)", re.IGNORECASE)
INVALID_IDS = {
    "Id000000000",
    "Id00000000",
    "Id0000000",
    "Id000000",
}


def run_adb_command(args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            [ADB_PATH, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
    except FileNotFoundError:
        raise RuntimeError(
            "ADB não encontrado. Instale o Android Platform Tools "
            "ou coloque o adb no PATH do Windows."
        )


def check_device_connected() -> str:
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
            "Conecte apenas um aparelho por vez."
        )

    return devices[0]


def check_phone_documents_exists() -> None:
    result = run_adb_command(["shell", "ls", PHONE_DOCUMENTS_PATH])

    if result.returncode != 0:
        raise RuntimeError(
            f"Não consegui acessar {PHONE_DOCUMENTS_PATH} no celular.\n"
            f"Erro:\n{result.stderr}"
        )


def normalize_participant_id(value: str) -> str:
    """
    Normaliza para o padrão Id26321088.
    """
    value = value.strip()
    return "Id" + value[2:]


def is_valid_participant_id(participant_id: str) -> bool:
    """
    Desconsidera IDs zerados tipo Id000000000.
    Porque aparentemente o sistema achou elegante gerar lixo antes do dado útil.
    """
    normalized = normalize_participant_id(participant_id)

    if normalized in INVALID_IDS:
        return False

    digits = normalized[2:]

    if not digits:
        return False

    if set(digits) == {"0"}:
        return False

    return True


def extract_participant_ids_from_text(text: str) -> list[str]:
    """
    Extrai todos os IDs encontrados e remove IDs inválidos/zerados.
    """
    matches = PARTICIPANT_ID_REGEX.findall(text)

    valid_ids = []

    for match in matches:
        participant_id = normalize_participant_id(match)

        if not is_valid_participant_id(participant_id):
            continue

        if participant_id not in valid_ids:
            valid_ids.append(participant_id)

    return valid_ids


def get_participant_id_from_phone() -> str:
    """
    Procura o ID do participante nos nomes dos arquivos dentro de:
    /sdcard/Documents/RAW_DATA_RING

    Ignora IDs zerados, como:
    Id000000000
    """
    print(f"Procurando ID em {PHONE_RAW_RING_PATH}...")

    result = run_adb_command([
        "shell",
        "find",
        PHONE_RAW_RING_PATH,
        "-type",
        "f"
    ])

    if result.returncode != 0:
        raise RuntimeError(
            f"Não consegui listar os arquivos em {PHONE_RAW_RING_PATH}.\n"
            "Confirme se a pasta RAW_DATA_RING existe dentro de Documents.\n"
            f"Erro:\n{result.stderr}"
        )

    participant_ids = extract_participant_ids_from_text(result.stdout)

    if not participant_ids:
        raise RuntimeError(
            "Não encontrei nenhum ID válido dentro da pasta RAW_DATA_RING.\n"
            "IDs zerados como Id000000000 são ignorados.\n"
            "Exemplo esperado:\n"
            "RingSleepSpO2_Id26321088_DevDAE3_NoDev_..."
        )

    if len(participant_ids) > 1:
        raise RuntimeError(
            "Encontrei mais de um ID válido dentro da RAW_DATA_RING:\n"
            f"{participant_ids}\n"
            "Isso pode indicar arquivos misturados de participantes diferentes."
        )

    return participant_ids[0]


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


def create_metadata_json(
    participant_id: str,
    destination_folder: Path,
    device_id: str
) -> Path:
    json_path = OUTPUT_ROOT / f"{destination_folder.name}.json"

    metadata = {
        "participant_id": participant_id,
        "device_id": device_id,
        "source_path": PHONE_DOCUMENTS_PATH,
        "raw_ring_path": PHONE_RAW_RING_PATH,
        "output_folder": str(destination_folder),
        "extracted_at": datetime.now().isoformat(timespec="seconds"),
        "status": "success"
    }

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=4)

    return json_path


def main() -> None:
    print("=== Extração de arquivos do celular ===")

    print("\nVerificando celular conectado...")
    device_id = check_device_connected()
    print(f"Celular encontrado: {device_id}")

    print(f"\nVerificando pasta {PHONE_DOCUMENTS_PATH}...")
    check_phone_documents_exists()

    print("\nBuscando ID do participante automaticamente...")
    participant_id = get_participant_id_from_phone()
    print(f"ID encontrado: {participant_id}")

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