import time

from backend.services.adb_service import run_command


def open_app(package_name: str):
    run_command([
        "adb",
        "shell",
        "monkey",
        "-p",
        package_name,
        "1",
    ])

    time.sleep(2)


def tap(x: int, y: int):
    run_command([
        "adb",
        "shell",
        "input",
        "tap",
        str(x),
        str(y),
    ])