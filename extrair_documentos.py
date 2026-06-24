import subprocess
import tkinter as tk
from tkinter import messagebox
from pathlib import Path


def run_command(command: list[str]) -> str:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())

    return result.stdout.strip()


def check_adb_installed() -> None:
    try:
        run_command(["adb", "version"])
    except Exception:
        raise RuntimeError(
            "ADB não encontrado. Instale o Android Platform Tools e coloque o adb no PATH."
        )


def get_connected_devices() -> list[str]:
    output = run_command(["adb", "devices"])

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
                "Celular conectado, mas não autorizado.\n\n"
                "Olhe a tela do celular e aceite a depuração USB."
            )

        elif "\toffline" in line:
            raise RuntimeError(
                "Celular aparece como offline.\n\n"
                "Desconecte e conecte o cabo USB novamente."
            )

    return devices


def get_script_folder() -> Path:
    return Path(__file__).resolve().parent


def pull_documents() -> Path:
    script_folder = get_script_folder()
    output_folder = script_folder / "extraído"

    output_folder.mkdir(parents=True, exist_ok=True)

    run_command([
        "adb",
        "pull",
        "/sdcard/Documents",
        str(output_folder)
    ])

    return output_folder


def extract_documents():
    try:
        status_label.config(text="Verificando ADB...")
        root.update_idletasks()

        check_adb_installed()

        status_label.config(text="Verificando celular conectado...")
        root.update_idletasks()

        devices = get_connected_devices()

        if not devices:
            raise RuntimeError(
                "Nenhum celular conectado via ADB.\n\n"
                "Confira:\n"
                "1. Cabo USB conectado\n"
                "2. Modo desenvolvedor ativado\n"
                "3. Depuração USB ativada\n"
                "4. Permissão aceita na tela do celular"
            )

        if len(devices) > 1:
            raise RuntimeError(
                "Mais de um dispositivo conectado.\n\n"
                "Desconecte os extras e deixe apenas o celular alvo."
            )

        status_label.config(text="Copiando /sdcard/Documents para /extraído...")
        root.update_idletasks()

        output_folder = pull_documents()

        status_label.config(text="Extração concluída.")

        messagebox.showinfo(
            "Sucesso",
            f"Pasta Documents copiada com sucesso:\n\n{output_folder}"
        )

    except Exception as error:
        status_label.config(text="Erro na extração.")

        messagebox.showerror(
            "Erro",
            str(error)
        )


root = tk.Tk()
root.title("Extrator de Documents do Celular")
root.geometry("500x220")
root.resizable(False, False)

title_label = tk.Label(
    root,
    text="Extrair pasta Documents do celular",
    font=("Arial", 16, "bold")
)
title_label.pack(pady=20)

description_label = tk.Label(
    root,
    text="Conecte o celular via USB, autorize a depuração USB e clique no botão.",
    font=("Arial", 10),
    wraplength=430
)
description_label.pack(pady=5)

extract_button = tk.Button(
    root,
    text="Pegar pasta Documents",
    font=("Arial", 12),
    width=25,
    command=extract_documents
)
extract_button.pack(pady=20)

status_label = tk.Label(
    root,
    text="Aguardando...",
    font=("Arial", 10)
)
status_label.pack(pady=5)

root.mainloop()