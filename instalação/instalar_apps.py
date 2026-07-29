import subprocess
import tkinter as tk
from tkinter import messagebox
from pathlib import Path


APPS_TO_INSTALL = [
    {
        "apk": "com_sec_smartring2-Phone-24120318-1_3_4-1.apk",
        "package": "com.sec.android.app.shealthmonitor",  # ajuste se o package real for outro
    },
    {
        "apk": "GPT_HRPClinical_Release_2_0_6_Phone.apk",
        "package": "com.hhw.hrpclinical",  # ajuste se o package real for outro
    },
]


COMMON_PERMISSIONS = [
    "android.permission.CAMERA",
    "android.permission.RECORD_AUDIO",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.BLUETOOTH_SCAN",
    "android.permission.BLUETOOTH_CONNECT",
    "android.permission.BLUETOOTH_ADVERTISE",
    "android.permission.BODY_SENSORS",
    "android.permission.ACTIVITY_RECOGNITION",
    "android.permission.POST_NOTIFICATIONS",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.READ_MEDIA_IMAGES",
    "android.permission.READ_MEDIA_VIDEO",
    "android.permission.READ_MEDIA_AUDIO",
]


def run_command(command: list[str], raise_on_error: bool = True) -> str:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()

    if raise_on_error and result.returncode != 0:
        raise RuntimeError(output)

    return output


def check_adb_installed() -> None:
    try:
        run_command(["adb", "version"])
    except Exception:
        raise RuntimeError(
            "ADB não encontrado.\n\n"
            "Instale o Android Platform Tools e coloque o adb no PATH."
        )


def get_connected_devices() -> list[str]:
    output = run_command(["adb", "devices"])

    devices = []

    for line in output.splitlines()[1:]:
        line = line.strip()

        if not line:
            continue

        if "\tdevice" in line:
            devices.append(line.split("\t")[0])

        elif "\tunauthorized" in line:
            raise RuntimeError(
                "Celular conectado, mas não autorizado.\n\n"
                "Aceite a depuração USB na tela do celular."
            )

        elif "\toffline" in line:
            raise RuntimeError(
                "Celular aparece como offline.\n\n"
                "Desconecte e conecte o cabo USB novamente."
            )

    return devices


def get_script_folder() -> Path:
    return Path(__file__).resolve().parent


def get_apps_folder() -> Path:
    return get_script_folder() / "apps"


def install_apk(apk_path: Path) -> str:
    commands_to_try = [
        [
            "adb",
            "install",
            "-r",
            "-g",
            "--bypass-low-target-sdk-block",
            str(apk_path)
        ],
        [
            "adb",
            "install",
            "-r",
            "-g",
            str(apk_path)
        ],
        [
            "adb",
            "install",
            "-r",
            "--bypass-low-target-sdk-block",
            str(apk_path)
        ],
        [
            "adb",
            "install",
            "-r",
            str(apk_path)
        ],
    ]

    last_error = ""

    for command in commands_to_try:
        output = run_command(command, raise_on_error=False)

        if "Success" in output:
            return output

        last_error = output

    raise RuntimeError(last_error)


def get_declared_permissions(package_name: str) -> list[str]:
    output = run_command(
        ["adb", "shell", "dumpsys", "package", package_name],
        raise_on_error=False
    )

    permissions = []

    capture = False

    for line in output.splitlines():
        stripped = line.strip()

        if stripped.startswith("requested permissions:"):
            capture = True
            continue

        if capture:
            if not stripped:
                break

            if stripped.startswith("install permissions:"):
                break

            if stripped.startswith("User "):
                break

            if stripped.startswith("android.permission."):
                permissions.append(stripped)

    return permissions


def grant_permission(package_name: str, permission: str) -> str:
    return run_command(
        [
            "adb",
            "shell",
            "pm",
            "grant",
            package_name,
            permission
        ],
        raise_on_error=False
    )


def grant_common_permissions(package_name: str) -> list[str]:
    declared_permissions = get_declared_permissions(package_name)

    granted = []
    ignored = []

    for permission in COMMON_PERMISSIONS:
        if permission not in declared_permissions:
            ignored.append(f"{permission} não declarada")
            continue

        output = grant_permission(package_name, permission)

        if "Exception" in output or "not a changeable permission type" in output or "Unknown permission" in output:
            ignored.append(f"{permission}: {output}")
        else:
            granted.append(permission)

    return granted


def install_apps():
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
                "Confira cabo USB, modo desenvolvedor, depuração USB e autorização na tela."
            )

        if len(devices) > 1:
            raise RuntimeError(
                "Mais de um dispositivo conectado.\n\n"
                "Deixe conectado apenas o celular alvo."
            )

        apps_folder = get_apps_folder()

        if not apps_folder.exists():
            raise RuntimeError(
                f"A pasta 'apps' não foi encontrada:\n\n{apps_folder}"
            )

        final_log = []

        for app in APPS_TO_INSTALL:
            apk_name = app["apk"]
            package_name = app["package"]
            apk_path = apps_folder / apk_name

            if not apk_path.exists():
                raise RuntimeError(f"APK não encontrado:\n\n{apk_path}")

            status_label.config(text=f"Instalando {apk_name}...")
            root.update_idletasks()

            install_output = install_apk(apk_path)

            status_label.config(text=f"Dando permissões para {package_name}...")
            root.update_idletasks()

            granted_permissions = grant_common_permissions(package_name)

            final_log.append(
                f"{apk_name}\n"
                f"Pacote: {package_name}\n"
                f"Instalação: {install_output}\n"
                f"Permissões concedidas: {len(granted_permissions)}"
            )

        status_label.config(text="Instalação concluída.")

        messagebox.showinfo(
            "Sucesso",
            "Processo concluído:\n\n" + "\n\n".join(final_log)
        )

    except Exception as error:
        status_label.config(text="Erro na instalação.")
        messagebox.showerror("Erro", str(error))


root = tk.Tk()
root.title("Instalador de Apps")
root.geometry("650x270")
root.resizable(False, False)

title_label = tk.Label(
    root,
    text="Instalar apps e conceder permissões",
    font=("Arial", 16, "bold")
)
title_label.pack(pady=20)

description_label = tk.Label(
    root,
    text=(
        "Instala os APKs do celular usando ADB e tenta conceder permissões "
        "runtime declaradas pelos apps."
    ),
    font=("Arial", 10),
    wraplength=560
)
description_label.pack(pady=5)

install_button = tk.Button(
    root,
    text="Instalar apps",
    font=("Arial", 12),
    width=25,
    command=install_apps
)
install_button.pack(pady=20)

status_label = tk.Label(
    root,
    text="Aguardando...",
    font=("Arial", 10)
)
status_label.pack(pady=5)

root.mainloop()