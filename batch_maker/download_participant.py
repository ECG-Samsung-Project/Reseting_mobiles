from __future__ import annotations

import os
import re
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath

import paramiko


# ============================================================
# CONFIGURAÇÃO
# ============================================================

SSH_HOST = "200.129.187.45"
SSH_PORT = 26157
SSH_USER = "ecg_admin"
SSH_PASSWORD = "ecgadmin2025"

DATALAKE_ROOT = "/mnt/ecg-dados/datalake"

OUTPUT_DIR = Path("Output")


# mode:
#   participant = procura somente dados daquele participante
#   all         = baixa a pasta inteira
#
# Nome da chave = nome da pasta que será criada dentro do ZIP.
SOURCES = {

    # ========================================================
    # SILVER
    # ========================================================

    "ecg_data": {
        "remote": f"{DATALAKE_ROOT}/silver/ecg_data",
        "mode": "participant",
    },

    "holter_data": {
        "remote": f"{DATALAKE_ROOT}/silver/holter_data",
        "mode": "participant",
    },

    # ========================================================
    # BRONZE
    # ========================================================

    "looper_data": {
        "remote": f"{DATALAKE_ROOT}/bronze/looper_data",
        "mode": "participant",
    },

    "eco_data": {
        "remote": f"{DATALAKE_ROOT}/bronze/eco_data",
        "mode": "participant",
    },

    # ========================================================
    # LANDING / RAW
    # ========================================================

    "ecg_raw": {
        "remote": f"{DATALAKE_ROOT}/landing/raw/ecg_data",
        "mode": "participant",
    },

    "holter_raw": {
        "remote": f"{DATALAKE_ROOT}/landing/raw/holter_data",
        "mode": "participant",
    },

    "looper_raw": {
        "remote": f"{DATALAKE_ROOT}/landing/raw/looper_data",
        "mode": "participant",
    },

    "mobile_fl_data": {
        "remote": f"{DATALAKE_ROOT}/landing/raw/mobile_fl_data",
        "mode": "participant",
    },

    "mobile_ic_data": {
        "remote": f"{DATALAKE_ROOT}/landing/raw/mobile_ic_data",
        "mode": "participant",
    },

    "watch_fl_data": {
        "remote": f"{DATALAKE_ROOT}/landing/raw/watch_fl_data",
        "mode": "participant",
    },

    "watch_ic_data": {
        "remote": f"{DATALAKE_ROOT}/landing/raw/watch_ic_data",
        "mode": "participant",
    },

    # ========================================================
    # PASTAS COMPLETAS
    # ========================================================

    # REDCap e Bio são enviados completos,
    # sem filtrar por participante.

    "redcap_data": {
        "remote": f"{DATALAKE_ROOT}/bronze/redcap_data",
        "mode": "all",
    },

    "bio_data": {
        "remote": f"{DATALAKE_ROOT}/bronze/bio_data",
        "mode": "all",
    },
}


# ============================================================
# SSH
# ============================================================

def connect_ssh() -> paramiko.SSHClient:
    client = paramiko.SSHClient()

    client.set_missing_host_key_policy(
        paramiko.AutoAddPolicy()
    )

    print()
    print(
        f"Conectando em "
        f"{SSH_USER}@{SSH_HOST}:{SSH_PORT}..."
    )

    client.connect(
        hostname=SSH_HOST,
        port=SSH_PORT,
        username=SSH_USER,
        password=SSH_PASSWORD,
        look_for_keys=False,
        allow_agent=False,
        timeout=15,
    )

    print("Conectado.")

    return client


# ============================================================
# HELPERS SFTP
# ============================================================

def remote_exists(
    sftp: paramiko.SFTPClient,
    remote_path: str,
) -> bool:

    try:
        sftp.stat(remote_path)
        return True

    except FileNotFoundError:
        return False

    except OSError:
        return False


def remote_is_dir(
    sftp: paramiko.SFTPClient,
    remote_path: str,
) -> bool:

    try:
        info = sftp.stat(remote_path)

        return stat.S_ISDIR(
            info.st_mode
        )

    except OSError:
        return False


def download_file(
    sftp: paramiko.SFTPClient,
    remote_file: str,
    local_file: Path,
):
    local_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"    arquivo: {remote_file}"
    )

    sftp.get(
        remote_file,
        str(local_file),
    )


def download_directory(
    sftp: paramiko.SFTPClient,
    remote_dir: str,
    local_dir: Path,
):
    """
    Baixa recursivamente o conteúdo de remote_dir
    para local_dir.
    """

    local_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        entries = sftp.listdir_attr(
            remote_dir
        )

    except OSError as exc:
        print(
            f"    Não foi possível abrir "
            f"{remote_dir}: {exc}"
        )
        return

    for entry in entries:

        remote_item = str(
            PurePosixPath(remote_dir)
            / entry.filename
        )

        local_item = (
            local_dir
            / entry.filename
        )

        if stat.S_ISDIR(
            entry.st_mode
        ):

            download_directory(
                sftp,
                remote_item,
                local_item,
            )

        else:

            download_file(
                sftp,
                remote_item,
                local_item,
            )


# ============================================================
# IDENTIFICAÇÃO DO PARTICIPANTE
# ============================================================

def participant_tokens(
    participant_id: str,
) -> set[str]:
    """
    Exemplo:

    EDI-21-2196

    gera:

    edi-21-2196
    edi212196
    212196

    Isso permite identificar tanto:

    EDI-21-2196_arquivo.zip

    quanto:

    212196_20260806_102225.zip
    """

    participant_id = (
        participant_id.lower()
    )

    compact = re.sub(
        r"[^a-z0-9]",
        "",
        participant_id,
    )

    digits = "".join(
        char
        for char in participant_id
        if char.isdigit()
    )

    tokens = {
        participant_id,
        compact,
    }

    if digits:
        tokens.add(digits)

    return {
        token
        for token in tokens
        if token
    }


def matches_participant(
    name: str,
    participant_id: str,
) -> bool:

    name_lower = (
        name.lower()
    )

    compact_name = re.sub(
        r"[^a-z0-9]",
        "",
        name_lower,
    )

    for token in participant_tokens(
        participant_id
    ):

        if token in name_lower:
            return True

        if token in compact_name:
            return True

    return False


# ============================================================
# PROCURA DOS DADOS DO PARTICIPANTE
# ============================================================

def download_participant_matches(
    sftp: paramiko.SFTPClient,
    remote_base: str,
    local_base: Path,
    participant_id: str,
) -> int:
    """
    Estratégia:

    1. Primeiro tenta:

       remote_base/PARTICIPANT_ID

       Exemplo:

       silver/ecg_data/EDI-21-2196/


    2. Se não encontrar uma pasta direta,
       procura recursivamente arquivos e pastas
       contendo:

       EDI-21-2196

       ou:

       EDI212196

       ou:

       212196


    Retorna a quantidade de ocorrências encontradas.
    """

    local_base.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not remote_exists(
        sftp,
        remote_base,
    ):
        return 0

    # ========================================================
    # CASO DIRETO
    # ========================================================

    direct_path = str(
        PurePosixPath(remote_base)
        / participant_id
    )

    if remote_exists(
        sftp,
        direct_path,
    ):

        if remote_is_dir(
            sftp,
            direct_path,
        ):

            # Baixa o conteúdo da pasta do participante
            # diretamente para a pasta da fonte.

            download_directory(
                sftp,
                direct_path,
                local_base,
            )

        else:

            download_file(
                sftp,
                direct_path,
                local_base / participant_id,
            )

        return 1

    # ========================================================
    # PROCURA RECURSIVA
    # ========================================================

    found = 0

    def walk(
        current_remote: str,
        relative: PurePosixPath,
    ):
        nonlocal found

        try:
            entries = sftp.listdir_attr(
                current_remote
            )

        except OSError:
            return

        for entry in entries:

            remote_item = str(
                PurePosixPath(
                    current_remote
                )
                / entry.filename
            )

            relative_item = (
                relative
                / entry.filename
            )

            local_item = (
                local_base
                / Path(
                    *relative_item.parts
                )
            )

            is_directory = (
                stat.S_ISDIR(
                    entry.st_mode
                )
            )

            # =================================================
            # O próprio nome bate com o participante
            # =================================================

            if matches_participant(
                entry.filename,
                participant_id,
            ):

                found += 1

                if is_directory:

                    download_directory(
                        sftp,
                        remote_item,
                        local_item,
                    )

                else:

                    download_file(
                        sftp,
                        remote_item,
                        local_item,
                    )

                # Já baixamos tudo desse diretório.
                # Não precisa continuar descendo nele.
                continue

            # =================================================
            # Continua procurando dentro das subpastas
            # =================================================

            if is_directory:

                walk(
                    remote_item,
                    relative_item,
                )

    walk(
        remote_base,
        PurePosixPath(),
    )

    return found


# ============================================================
# ZIP
# ============================================================

def create_zip(
    source_dir: Path,
    zip_path: Path,
):
    """
    Cria o ZIP incluindo também diretórios vazios.

    Isso é importante para fontes ausentes.
    Exemplo:

    participante/
        eco_data/

    Mesmo sem arquivos, eco_data aparecerá no ZIP.
    """

    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        allowZip64=True,
    ) as zip_file:

        for root, dirs, files in os.walk(
            source_dir
        ):

            root_path = Path(root)

            relative_root = (
                root_path.relative_to(
                    source_dir.parent
                )
            )

            # Insere explicitamente a pasta no ZIP.
            # Isso mantém diretórios vazios.

            zip_file.writestr(
                relative_root
                .as_posix()
                .rstrip("/")
                + "/",
                "",
            )

            for file_name in files:

                file_path = (
                    root_path
                    / file_name
                )

                archive_name = (
                    file_path.relative_to(
                        source_dir.parent
                    )
                )

                zip_file.write(
                    file_path,
                    archive_name.as_posix(),
                )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 60
    )

    print(
        "ECG - GERADOR DE PACOTE DO PARTICIPANTE"
    )

    print(
        "=" * 60
    )

    participant_id = input(
        "\nID do participante "
        "(ex: EDI-21-2196): "
    ).strip().upper()

    # ========================================================
    # VALIDAÇÃO
    # ========================================================

    if not participant_id:

        print(
            "ID vazio."
        )

        return

    if not re.fullmatch(
        r"[A-Z0-9_-]+",
        participant_id,
    ):

        print(
            "ID inválido. "
            "Use somente letras, números, '-' e '_'."
        )

        return

    # ========================================================
    # OUTPUT
    # ========================================================

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    zip_path = (
        OUTPUT_DIR
        / f"{participant_id}.zip"
    )

    staging_root = (
        OUTPUT_DIR
        / f".tmp_{participant_id}"
    )

    participant_root = (
        staging_root
        / participant_id
    )

    # ========================================================
    # LIMPA EXECUÇÃO ANTERIOR
    # ========================================================

    if staging_root.exists():

        shutil.rmtree(
            staging_root
        )

    participant_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    if zip_path.exists():

        zip_path.unlink()

    ssh = None
    sftp = None

    try:

        # ====================================================
        # CONECTA
        # ====================================================

        ssh = connect_ssh()

        sftp = (
            ssh.open_sftp()
        )

        print()
        print(
            "=" * 60
        )

        print(
            f"Participante: {participant_id}"
        )

        print(
            "=" * 60
        )

        # ====================================================
        # PROCESSA CADA FONTE
        # ====================================================

        for source_name, config in SOURCES.items():

            remote_path = (
                config["remote"]
            )

            mode = (
                config["mode"]
            )

            local_path = (
                participant_root
                / source_name
            )

            # Cria SEMPRE.
            #
            # Caso nenhum arquivo seja encontrado,
            # a pasta ficará vazia e será mantida
            # dentro do ZIP.

            local_path.mkdir(
                parents=True,
                exist_ok=True,
            )

            print()

            print(
                f"[{source_name}]"
            )

            print(
                f"  Origem: {remote_path}"
            )

            # =================================================
            # PASTA COMPLETA
            # =================================================

            if mode == "all":

                if not remote_exists(
                    sftp,
                    remote_path,
                ):

                    print(
                        "  AUSENTE -> "
                        "pasta vazia será criada."
                    )

                    continue

                print(
                    "  Baixando pasta completa..."
                )

                download_directory(
                    sftp,
                    remote_path,
                    local_path,
                )

                print(
                    "  OK"
                )

                continue

            # =================================================
            # SOMENTE PARTICIPANTE
            # =================================================

            found = download_participant_matches(
                sftp=sftp,
                remote_base=remote_path,
                local_base=local_path,
                participant_id=participant_id,
            )

            if found == 0:

                print(
                    "  AUSENTE -> "
                    "pasta vazia será criada."
                )

            else:

                print(
                    f"  OK -> "
                    f"{found} ocorrência(s) encontrada(s)."
                )

        # ====================================================
        # CRIA ZIP
        # ====================================================

        print()
        print(
            "=" * 60
        )

        print(
            "Criando ZIP..."
        )

        print(
            "=" * 60
        )

        create_zip(
            participant_root,
            zip_path,
        )

        print()
        print(
            "PACOTE CRIADO:"
        )

        print(
            zip_path.resolve()
        )

    # ========================================================
    # ENCERRA CONEXÕES / LIMPA TEMPORÁRIOS
    # ========================================================

    finally:

        if sftp:

            sftp.close()

        if ssh:

            ssh.close()

        if staging_root.exists():

            shutil.rmtree(
                staging_root,
                ignore_errors=True,
            )


if __name__ == "__main__":
    main()