import json
from pathlib import Path


def write_json_metadata(
    metadata: dict,
    json_path: Path,
) -> Path:
    json_path.parent.mkdir(parents=True, exist_ok=True)

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=4)

    return json_path