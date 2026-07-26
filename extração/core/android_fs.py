from pathlib import Path

from core.adb_client import AdbClient


class AndroidFileSystem:
    def __init__(self, adb: AdbClient) -> None:
        self.adb = adb

    def check_path_exists(self, android_path: str) -> None:
        result = self.adb.run(
            ["shell", "ls", android_path],
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Não consegui acessar {android_path} no aparelho.\n"
                f"Erro:\n{result.stderr or result.stdout}"
            )

    def list_folder_paths(self, android_root_path: str) -> list[str]:
        command = (
            f'cd "{android_root_path}" 2>/dev/null || exit 1; '
            f'for item in *; do '
            f'[ "$item" = "*" ] && continue; '
            f'[ -d "$item" ] && echo "{android_root_path}/$item"; '
            f'done; '
            f'true'
        )

        result = self.adb.run(["shell", command], check=False)

        if result.returncode != 0:
            raise RuntimeError(
                f"Não consegui listar as pastas de {android_root_path}.\n"
                f"Erro:\n{result.stderr or result.stdout}"
            )

        return [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]


    def list_item_paths(self, android_root_path: str) -> list[str]:
        command = (
            f'cd "{android_root_path}" 2>/dev/null || exit 1; '
            f'for item in *; do '
            f'[ "$item" = "*" ] && continue; '
            f'echo "{android_root_path}/$item"; '
            f'done; '
            f'true'
        )

        result = self.adb.run(["shell", command], check=False)

        if result.returncode != 0:
            raise RuntimeError(
                f"Não consegui listar os itens de {android_root_path}.\n"
                f"Erro:\n{result.stderr or result.stdout}"
            )

        return [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]

    def list_files(self, android_path: str, check: bool = True) -> list[str]:
        result = self.adb.run(
            [
                "shell",
                "find",
                android_path,
                "-type",
                "f",
            ],
            check=False,
        )

        if check and result.returncode != 0:
            raise RuntimeError(
                f"Não consegui listar os arquivos em {android_path}.\n"
                f"Erro:\n{result.stderr or result.stdout}"
            )

        if result.returncode != 0:
            return []

        return [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]

    def list_dirs(self, android_path: str, check: bool = False) -> list[str]:
        result = self.adb.run(
            [
                "shell",
                "find",
                android_path,
                "-type",
                "d",
            ],
            check=False,
        )

        if check and result.returncode != 0:
            raise RuntimeError(
                f"Não consegui listar as pastas em {android_path}.\n"
                f"Erro:\n{result.stderr or result.stdout}"
            )

        if result.returncode != 0:
            return []

        return [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]

    def get_path_size_kb(self, android_path: str) -> int | None:
        result = self.adb.run(
            ["shell", "du", "-sk", android_path],
            check=False,
        )

        if result.returncode != 0 or not result.stdout:
            return None

        first_part = result.stdout.split()[0]

        if not first_part.isdigit():
            return None

        return int(first_part)

    def get_path_summary(self, android_path: str) -> dict:
        files = self.list_files(android_path, check=False)
        dirs = self.list_dirs(android_path, check=False)
        size_kb = self.get_path_size_kb(android_path)

        return {
            "path": android_path,
            "file_count": len(files),
            "folder_count": len(dirs),
            "size_kb": size_kb,
            "size_mb": round(size_kb / 1024, 2) if size_kb is not None else None,
            "sample_files": [Path(file).name for file in files[:10]],
        }

    def get_folder_summaries(self, android_root_path: str) -> list[dict]:
        folder_paths = self.list_folder_paths(android_root_path)

        summaries = []

        for folder_path in folder_paths:
            folder_name = folder_path.rstrip("/").split("/")[-1]
            summary = self.get_path_summary(folder_path)

            summaries.append(
                {
                    "folder_name": folder_name,
                    "folder_path": folder_path,
                    "file_count": summary["file_count"],
                    "folder_count": summary["folder_count"],
                    "size_mb": summary["size_mb"],
                    "sample_files": summary.get("sample_files", []),
                }
            )

        return sorted(
            summaries,
            key=lambda item: item["folder_name"].lower(),
        )