from pathlib import Path
from backend.services.adb_service import run_command

## Apps are currently in folder C:\Users\Victo\Documents\GitHub\Reseting_mobiles\apps\com_sec_smartring2-Phone-24120318-1_3_4-1.apk
## while this script is in folder C:\Users\Victo\Documents\GitHub\Reseting_mobiles\instalação\backend\services

def get_apps_folder() -> Path:

    return Path(__file__).resolve().parent.parent.parent.parent / "apps"


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