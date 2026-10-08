import subprocess

def run_command(command: list[str], raise_on_error: bool = True) -> str:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    print("Running command:", " ".join(command))
    print(output)
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
