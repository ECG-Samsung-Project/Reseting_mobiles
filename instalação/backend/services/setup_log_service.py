from datetime import datetime
from fileinput import filename
from pathlib import Path
import json
import tempfile

from backend.services.adb_service import run_command

def save_setup_log() -> str:
    now = datetime.now().astimezone()

    data = {
        "setup_datetime": now.strftime("%Y-%m-%d %H:%M:%S %Z")
    }

    filename = f"ecg_setup_{now.strftime('%Y%m%d_%H%M%S')}.txt"

    local_path = Path(tempfile.gettempdir()) / filename

    with open(local_path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False,
        )
    device_path = f"/sdcard/documents/{filename}"

    print(f"Salvando log de instalação em {device_path}...")
    run_command(["adb", "push", str(local_path), device_path])

    return device_path