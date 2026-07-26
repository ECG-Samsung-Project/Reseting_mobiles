import shutil
from pathlib import Path


def get_unique_local_path(destination_path: Path) -> Path:
    if not destination_path.exists():
        return destination_path

    parent = destination_path.parent
    stem = destination_path.stem
    suffix = destination_path.suffix

    index = 2

    while True:
        candidate = parent / f"{stem}_{index}{suffix}"

        if not candidate.exists():
            return candidate

        index += 1


def merge_local_folder_contents(
    source_folder: Path,
    destination_folder: Path,
) -> None:
    source_folder = Path(source_folder)
    destination_folder = Path(destination_folder)

    if source_folder.resolve() == destination_folder.resolve():
        return

    destination_folder.mkdir(parents=True, exist_ok=True)

    for child in source_folder.iterdir():
        target = destination_folder / child.name

        if child.is_dir():
            if target.exists() and target.is_dir():
                merge_local_folder_contents(
                    source_folder=child,
                    destination_folder=target,
                )

                if child.exists():
                    shutil.rmtree(child, ignore_errors=True)
            else:
                if target.exists():
                    target = get_unique_local_path(target)

                shutil.move(str(child), str(target))

        else:
            if target.exists():
                target = get_unique_local_path(target)

            shutil.move(str(child), str(target))

    if source_folder.exists():
        shutil.rmtree(source_folder, ignore_errors=True)