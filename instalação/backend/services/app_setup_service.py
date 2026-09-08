from collections.abc import Callable

from backend.config import APPS_TO_INSTALL
from backend.services.apk_installation_service import (
    get_apps_folder,
    install_apk,
)
from backend.services.permission_service import grant_common_permissions


def setup_apps(
    progress_callback: Callable[[str], None],
) -> list[str]:

    apps_folder = get_apps_folder()

    if not apps_folder.exists():
        raise RuntimeError(
            f"A pasta 'apps' não foi encontrada:\n\n{apps_folder}"
        )

    logs = []

    for app in APPS_TO_INSTALL:
        apk_path = apps_folder / app["apk"]

        if not apk_path.exists():
            raise RuntimeError(f"APK não encontrado:\n\n{apk_path}")

        progress_callback(f"Instalando {app['apk']}...")
        install_output = install_apk(apk_path)

        progress_callback(f"Configurando {app['package']}...")
        granted = grant_common_permissions(app["package"])

        logs.append(
            f"{app['apk']}\n"
            f"Pacote: {app['package']}\n"
            f"Instalação: {install_output}\n"
            f"Permissões concedidas: {len(granted)}"
        )

    return logs