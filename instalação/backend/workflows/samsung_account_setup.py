import time
from backend.services.ui_automation_service import open_app, tap
from backend.services.adb_service import run_command

def setup():
    if has_samsung_account():
        print("Samsung account already exists.")
        remove_samsung_account()
    else:
        print("No Samsung account found.")
    return

    

def has_samsung_account() -> bool:
    output = run_command([
        "adb", 
        "shell", 
        "dumpsys",
        "account"])
    return "com.osp.app.signin" in output.lower()

def remove_samsung_account():
    run_command([
        "adb",
        "shell",
        "am",
        "start",
        "-a",
        "android.settings.SYNC_SETTINGS",
    ])
    input("Press Enter after removing the Samsung account...")

    print("Press on first account...")
    tap(400, 120)
    print("Press on remove account...")
    tap(400, 1060)
    print("Confirm removal of the Samsung account...")
    tap(750, 2050)
    tap(750, 2050)