from pathlib import Path


def get_local_output_summary(destination_folder: Path) -> dict:
    files = [item for item in destination_folder.rglob("*") if item.is_file()]
    folders = [item for item in destination_folder.rglob("*") if item.is_dir()]

    total_size_bytes = sum(file.stat().st_size for file in files)

    extensions: dict[str, int] = {}

    for file in files:
        suffix = file.suffix.lower() if file.suffix else "[sem_extensao]"
        extensions[suffix] = extensions.get(suffix, 0) + 1

    return {
        "local_file_count": len(files),
        "local_folder_count": len(folders),
        "total_size_bytes": total_size_bytes,
        "total_size_mb": round(total_size_bytes / 1024 / 1024, 2),
        "extensions": extensions,
    }