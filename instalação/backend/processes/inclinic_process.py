import backend.workflows.hrpclinical_setup as hrpclinical
import backend.workflows.smartring_setup as smartring
import backend.workflows.play_protect_setup as play_protect
import backend.workflows.samsung_account_setup as samsungAccount


from collections.abc import Callable
from backend.services.adb_service import check_adb_installed, run_command
from backend.services.apk_installation_service import uninstall_all_apps
from backend.services.connection_service import ensure_connected_devices
from backend.services.app_setup_service import setup_apps
from backend.services.setup_log_service import save_setup_log
from backend.services.ui_automation_service import unlock_screen, close_all_apps


def setup(progress_callback: Callable[[str], None] | None = None,) -> list[str]:

    def update_status(message: str):
        if progress_callback:
            progress_callback(message)

    print("Iniciando configuração do dispositivo...")
    print("Verificando ADB...")
    check_adb_installed()
    print("ADB verificado com sucesso.")
    print("Verificando celular conectado...")

    ensure_connected_devices()
    print("Celular conectado com sucesso.")
    unlock_screen()
    print("Tela desbloqueada com sucesso.")
    close_all_apps()
    print("Todos os aplicativos fechados.")
    print("Pausando Play Protect...")
    play_protect.pause_play_protect()
    print("Play Protect pausado.")
    close_all_apps()
    print("Todos os aplicativos fechados novamente após pausar Play Protect.")
    log = setup_apps(progress_callback=update_status)
    save_setup_log()
    print("Instalação concluída.")
    print("Configuração do dispositivo concluída.")
    print("Iniciando configuração do HRP Clinical...")

    hrpclinical.setup()
    print("Configuração do HRP Clinical concluída.")
    print("Iniciando configuração do Smart Ring...")
    smartring.setup()
    print("Configuração do Smart Ring concluída.")
    print("Configuração do dispositivo InClinic concluída.")



    return log


def reset(progress_callback: Callable[[str], None] | None = None,) -> None:

    def update_status(message: str):
        if progress_callback:
            progress_callback(message)

    update_status("Verificando ADB...")
    check_adb_installed()

    update_status("Verificando celular conectado...")
    ensure_connected_devices()

    unlock_screen()
    close_all_apps()

    update_status("Desinstalando apps do projeto...")
    uninstall_all_apps()

    clean_user_folders()
    update_status("Limpeza concluída.")

    close_all_apps()

    samsungAccount.setup()
    return None

def clean_user_folders():

    run_command([
        "adb", 
        "shell",
        "rm", 
        "-rf",
        "/sdcard/Documents/*"
    ])

    run_command([
        "adb", 
        "shell",
        "rm", 
        "-rf",
        "/sdcard/Download/*"
    ])