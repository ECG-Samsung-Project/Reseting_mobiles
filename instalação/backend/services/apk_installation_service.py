from pathlib import Path
from backend.services.adb_service import run_command

## Apps are currently in folder C:\Users\Victo\Documents\GitHub\Reseting_mobiles\apps\com_sec_smartring2-Phone-24120318-1_3_4-1.apk
## while this script is in folder C:\Users\Victo\Documents\GitHub\Reseting_mobiles\instalação\backend\services

def get_apps_folder() -> Path:

    return Path(__file__).resolve().parent.parent.parent.parent / "apps"

def uninstall_all_apps():
    for app in ["com.hhw.hrpclinical", "com.sec.smartring2"]:
        uninstall_app(app)   

def is_app_installed(package_name: str) -> bool:
    output = run_command(
        ["adb", "shell", "pm", "list", "packages", package_name],
        raise_on_error=False,
    )

    return package_name in output

def uninstall_app(package_name: str) -> str:
    if not is_app_installed(package_name):
        return f"App {package_name} não está instalado."
    return run_command(
        ["adb", "uninstall", package_name],
        raise_on_error=False,
    )

def install_apk(apk_path: Path) -> str:
    commands_to_try = [
        [
            "adb",
            "install",
            "-r",
            "-g",
            "--bypass-low-target-sdk-block",
            str(apk_path),
        ],
        ["adb", "install", "-r", "-g", str(apk_path)],
        [
            "adb",
            "install",
            "-r",
            "--bypass-low-target-sdk-block",
            str(apk_path),
        ],
        ["adb", "install", "-r", str(apk_path)],
    ]

    last_error = ""

    for command in commands_to_try:
        output = run_command(command, raise_on_error=False)

        if "Success" in output:
            return output

        last_error = output

    raise RuntimeError(last_error)