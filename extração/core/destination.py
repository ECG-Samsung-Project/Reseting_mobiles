from pathlib import Path


def build_unique_destination_folder(
    output_root: Path,
    folder_name: str,
) -> Path:
    destination_folder = output_root / folder_name

    if not destination_folder.exists():
        return destination_folder

    counter = 2

    while True:
        candidate = output_root / f"{folder_name}_{counter}"

        if not candidate.exists():
            return candidate

        counter += 1