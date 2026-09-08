from collections.abc import Callable
from backend.services.adb_service import check_adb_installed
from backend.services.connection_service import ensure_connected_devices
from backend.services.app_setup_service import setup_apps
from backend.services.setup_log_service import save_setup_log
from backend.services.ui_automation_service import open_app, tap

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

    open_app_and_finish_setup()

    return log

import time
def open_app_and_finish_setup():
    open_app("com.hhw.hrpclinical")
    tap(500, 1400) ## Tap on "Select"
    time.sleep(1)
    tap(150, 1250) ## Tap on Documents
    time.sleep(1)
    tap(500, 2140) ## Tap on "Select"
    time.sleep(1)
    tap(900, 2100) ## Tap on "Select"

    open_app("com.sec.smartring2")
    tap(750, 1300)
