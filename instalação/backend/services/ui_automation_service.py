import time

from backend.services.adb_service import run_command

def is_screen_locked() -> bool:
    output = run_command(
        ["adb", "shell", "dumpsys", "window"],
        raise_on_error=False,
    ).lower()

    return "iskeyguardshowing=true" in output

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


def input_text(text: str, delay: float = 0.2):
    words = text.split()
    time.sleep(delay)  # Pequena pausa antes de começar a digitar
    for index, word in enumerate(words):
        run_command([
            "adb",
            "shell",
            "input",
            "text",
            word,
        ])

        if index < len(words) - 1:
            run_command([
                "adb",
                "shell",
                "input",
                "keyevent",
                "KEYCODE_SPACE",
            ])

        time.sleep(delay)

def tap_home():
    run_command([
        "adb",
        "shell",
        "input",
        "keyevent",
        "KEYCODE_HOME",
    ])

def swipe(start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300):
    run_command([
        "adb",
        "shell",
        "input",
        "swipe",
        str(start_x),
        str(start_y),
        str(end_x),
        str(end_y),
        str(duration_ms),
    ])

def unlock_screen():
    # Acorda a tela
    run_command(
        ["adb", "shell", "input", "keyevent", "KEYCODE_WAKEUP"],
        raise_on_error=False,
    )

    time.sleep(0.8)

    if not is_screen_locked():
        print("Tela já está desbloqueada.")
        tap_home()
        return

    # Tenta dispensar o keyguard
    run_command(
        ["adb", "shell", "wm", "dismiss-keyguard"],
        raise_on_error=False,
    )

    # Dá tempo para a animação do Android terminar
    time.sleep(1)
    tap(500, 1800)
    # Swipe vertical mais forte
    swipe(
        540, 2100,
        540, 500,
        duration_ms=250,
    )

    time.sleep(0.8)

    # Segunda tentativa, caso o primeiro não tenha passado
    if is_screen_locked():
        swipe(
            540, 2100,
            540, 400,
            duration_ms=250,
        )

        time.sleep(0.8)

    tap_home()

def close_all_apps():
    run_command([
        "adb",
        "shell",
        "input",
        "keyevent",
        "KEYCODE_APP_SWITCH",
    ])

    time.sleep(0.5)
    tap(500, 1800)
    time.sleep(0.5)


def open_settings():
    run_command([
        "adb",
        "shell",
        "am",
        "start",
        "-a",
        "android.settings.SETTINGS",
    ])


def get_screen_xml() -> str:
    run_command([
        "adb",
        "shell",
        "uiautomator",
        "dump",
        "/sdcard/window.xml",
    ])

    return run_command([
        "adb",
        "shell",
        "cat",
        "/sdcard/window.xml",
    ])