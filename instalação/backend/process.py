from collections.abc import Callable
from backend.services.adb_service import check_adb_installed, run_command
from backend.services.apk_installation_service import uninstall_all_apps
from backend.services.connection_service import ensure_connected_devices
from backend.services.app_setup_service import setup_apps
from backend.services.setup_log_service import save_setup_log
import backend.workflows.hrpclinical_setup as hrpclinical
import backend.workflows.smartring_setup as smartring

def setup_device(progress_callback: Callable[[str], None] | None = None,) -> list[str]:

    def update_status(message: str):
        if progress_callback:
            progress_callback(message)

    update_status("Verificando ADB...")
    check_adb_installed()

    update_status("Verificando celular conectado...")
    ensure_connected_devices()
    
    log = setup_apps(progress_callback=update_status)
    save_setup_log()
    update_status("Instalação concluída.")

    hrpclinical.setup()
    smartring.setup()
    
    return log


def reset_device(progress_callback: Callable[[str], None] | None = None,) -> None:

    def update_status(message: str):
        if progress_callback:
            progress_callback(message)

    update_status("Verificando ADB...")
    check_adb_installed()

    update_status("Verificando celular conectado...")
    ensure_connected_devices()

    update_status("Desinstalando apps do projeto...")
    uninstall_all_apps()

    clean_user_folders()
    update_status("Limpeza concluída.")



def clean_user_folders():
    run_command([
        "adb", "shell",
        "rm", "-rf",
        "/sdcard/Documents/*"
    ])

    run_command([
        "adb", "shell",
        "rm", "-rf",
        "/sdcard/Download/*"
    ])