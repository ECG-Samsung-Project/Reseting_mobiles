import shlex
from pathlib import PurePosixPath

from core.adb_client import AdbClient

from .config import WatchExtractionConfig

SourceCandidate = tuple[str, str]


class WatchAndroidStorage:
    def __init__(
        self,
        adb: AdbClient,
        config: WatchExtractionConfig,
    ) -> None:
        self.adb = adb
        self.config = config

    @staticmethod
    def normalize_android_path(path: str) -> str:
        return path.strip().rstrip("/")

    @staticmethod
    def get_source_kind_from_path(path: str) -> str:
        folder_name = PurePosixPath(path.strip().rstrip("/")).name.lower()

        if folder_name in {"download", "downloads"}:
            return "download"

        if folder_name == "documents":
            return "documents"

        return "unknown"

    def adb_shell_stdout(self, shell_command: str) -> str:
        result = self.adb.run(
            ["shell", shell_command],
            check=False,
        )

        stdout = getattr(result, "stdout", "") or ""
        stderr = getattr(result, "stderr", "") or ""

        text = stdout.strip()

        if not text:
            text = stderr.strip()

        return text

    def android_dir_exists(self, root_path: str) -> bool:
        root_path = self.normalize_android_path(root_path)

        if not root_path:
            return False

        quoted_path = shlex.quote(root_path)

        command = (
            f"if [ -d {quoted_path} ]; then "
            f"echo EXISTS; "
            f"elif ls -la {quoted_path} >/dev/null 2>&1; then "
            f"echo EXISTS; "
            f"else "
            f"echo MISSING; "
            f"fi"
        )

        output = self.adb_shell_stdout(command)

        return "EXISTS" in output

    def append_unique_path(self, paths: list[str], path: str) -> None:
        clean_path = self.normalize_android_path(path)

        if not clean_path:
            return

        if clean_path not in paths:
            paths.append(clean_path)

    def append_unique_candidate(
        self,
        candidates: list[SourceCandidate],
        source_kind: str,
        path: str,
    ) -> None:
        clean_path = self.normalize_android_path(path)

        if not clean_path:
            return

        candidate = (source_kind, clean_path)

        if candidate not in candidates:
            candidates.append(candidate)

    def get_watch_source_path_candidates(self) -> list[SourceCandidate]:
        candidates: list[SourceCandidate] = []

        raw_candidates = [
            ("download", "/sdcard/Download"),
            ("download", "/sdcard/Downloads"),
            ("documents", "/sdcard/Documents"),
            ("download", "/storage/emulated/0/Download"),
            ("download", "/storage/emulated/0/Downloads"),
            ("documents", "/storage/emulated/0/Documents"),
            ("download", "/storage/self/primary/Download"),
            ("download", "/storage/self/primary/Downloads"),
            ("documents", "/storage/self/primary/Documents"),
            ("download", "/mnt/sdcard/Download"),
            ("download", "/mnt/sdcard/Downloads"),
            ("documents", "/mnt/sdcard/Documents"),
        ]

        config_path = self.normalize_android_path(
            self.config.watch_documents_path,
        )

        if config_path:
            config_kind = self.get_source_kind_from_path(config_path)

            if config_kind == "unknown":
                config_kind = "documents"

            raw_candidates.append((config_kind, config_path))

        for source_kind, path in raw_candidates:
            self.append_unique_candidate(
                candidates=candidates,
                source_kind=source_kind,
                path=path,
            )

        return candidates

    def discover_watch_source_candidates(self) -> list[SourceCandidate]:
        candidates: list[SourceCandidate] = []

        base_paths = [
            "/sdcard",
            "/storage/emulated/0",
            "/storage/self/primary",
            "/mnt/sdcard",
        ]

        wanted_names = {
            "download",
            "downloads",
            "documents",
        }

        for base_path in base_paths:
            quoted_base_path = shlex.quote(base_path)

            list_output = self.adb_shell_stdout(
                f"ls -1 {quoted_base_path} 2>/dev/null"
            )

            for line in list_output.splitlines():
                folder_name = line.strip().rstrip("/")

                if not folder_name:
                    continue

                if folder_name.lower() not in wanted_names:
                    continue

                full_path = f"{base_path.rstrip('/')}/{folder_name}"
                source_kind = self.get_source_kind_from_path(full_path)

                self.append_unique_candidate(
                    candidates=candidates,
                    source_kind=source_kind,
                    path=full_path,
                )

        for base_path in base_paths:
            quoted_base_path = shlex.quote(base_path)

            find_output = self.adb_shell_stdout(
                f"find {quoted_base_path} "
                f"-maxdepth 2 "
                f"-type d "
                f"\\( -iname 'Download' -o -iname 'Downloads' -o -iname 'Documents' \\) "
                f"2>/dev/null"
            )

            for line in find_output.splitlines():
                full_path = self.normalize_android_path(line)

                if not full_path:
                    continue

                source_kind = self.get_source_kind_from_path(full_path)

                if source_kind == "unknown":
                    continue

                self.append_unique_candidate(
                    candidates=candidates,
                    source_kind=source_kind,
                    path=full_path,
                )

        return candidates

    def get_storage_debug_text(self, max_chars: int = 5000) -> str:
        sections: list[str] = []

        ping = self.adb_shell_stdout("echo ADB_SHELL_OK")

        sections.append(
            f"Teste shell:\n{ping or 'sem retorno'}"
        )

        env_output = self.adb_shell_stdout(
            "echo EXTERNAL_STORAGE=$EXTERNAL_STORAGE; "
            "echo SECONDARY_STORAGE=$SECONDARY_STORAGE; "
            "echo ANDROID_DATA=$ANDROID_DATA"
        )

        sections.append(
            f"Variáveis:\n{env_output or 'sem retorno'}"
        )

        base_paths = [
            "/",
            "/sdcard",
            "/storage",
            "/storage/emulated",
            "/storage/emulated/0",
            "/storage/self",
            "/storage/self/primary",
            "/mnt/sdcard",
        ]

        for base_path in base_paths:
            quoted_base_path = shlex.quote(base_path)

            output = self.adb_shell_stdout(
                f"ls -la {quoted_base_path} 2>&1"
            )

            if not output:
                output = "sem retorno"

            sections.append(
                f"{base_path}:\n{output}"
            )

        debug_text = "\n\n".join(sections)

        if len(debug_text) > max_chars:
            debug_text = debug_text[:max_chars] + "\n\n... diagnóstico truncado."

        return debug_text

    def get_existing_watch_source_paths(self) -> list[str]:
        shell_test = self.adb_shell_stdout("echo ADB_SHELL_OK")

        if "ADB_SHELL_OK" not in shell_test:
            raise RuntimeError(
                "ADB conectou no relógio, mas o comando shell não está retornando saída.\n\n"
                "Isso normalmente indica problema no wrapper do AdbClient.run ou no modo como o comando está sendo montado.\n\n"
                f"Retorno do teste:\n{shell_test or 'sem retorno'}"
            )

        candidates: list[SourceCandidate] = []

        for source_kind, path in self.get_watch_source_path_candidates():
            self.append_unique_candidate(
                candidates=candidates,
                source_kind=source_kind,
                path=path,
            )

        for source_kind, path in self.discover_watch_source_candidates():
            self.append_unique_candidate(
                candidates=candidates,
                source_kind=source_kind,
                path=path,
            )

        chosen_by_kind: dict[str, str] = {}
        checked_paths: list[str] = []

        for source_kind, path in candidates:
            self.append_unique_path(checked_paths, path)

            if source_kind in chosen_by_kind:
                continue

            if self.android_dir_exists(path):
                chosen_by_kind[source_kind] = path

        source_paths: list[str] = []

        for source_kind in ["download", "documents"]:
            path = chosen_by_kind.get(source_kind)

            if path:
                self.append_unique_path(source_paths, path)

        if not source_paths:
            checked_text = "\n".join(
                f"- {path}"
                for path in checked_paths
            )

            debug_text = self.get_storage_debug_text()

            raise RuntimeError(
                "Nenhuma pasta de coleta encontrada no relógio.\n\n"
                "Pastas verificadas:\n"
                f"{checked_text}\n\n"
                "Diagnóstico do armazenamento:\n"
                f"{debug_text}"
            )

        return source_paths

    def get_android_folder_tree(
        self,
        root_path: str,
        max_items: int = 1000,
    ) -> dict:
        root_path = self.normalize_android_path(root_path)
        quoted_root_path = shlex.quote(root_path)

        exists = self.android_dir_exists(root_path)

        dirs_output = self.adb_shell_stdout(
            f"find {quoted_root_path} -mindepth 1 -type d 2>/dev/null"
        )

        files_output = self.adb_shell_stdout(
            f"find {quoted_root_path} -mindepth 1 -type f 2>/dev/null"
        )

        dirs = [
            line.strip().rstrip("/")
            for line in dirs_output.splitlines()
            if line.strip()
        ]

        files = [
            line.strip().rstrip("/")
            for line in files_output.splitlines()
            if line.strip()
        ]

        if dirs or files:
            exists = True

        if not exists:
            return {
                "root_path": root_path,
                "exists": False,
                "file_count": 0,
                "folder_count": 0,
                "total_items": 0,
                "tree_lines": [
                    f"{root_path}/",
                    "    - pasta não encontrada",
                ],
                "tree_text": f"{root_path}/\n    - pasta não encontrada",
            }

        items: list[tuple[str, str]] = []

        for folder_path in dirs:
            items.append((folder_path, "dir"))

        for file_path in files:
            items.append((file_path, "file"))

        def get_relative_parts(android_path: str) -> tuple[str, ...]:
            clean_path = android_path.rstrip("/")

            if clean_path.startswith(root_path):
                relative_path = clean_path[len(root_path):].lstrip("/")
            else:
                relative_path = clean_path

            if not relative_path:
                return tuple()

            return PurePosixPath(relative_path).parts

        items = sorted(
            items,
            key=lambda item: get_relative_parts(item[0]),
        )

        tree_lines = [f"{root_path}/"]

        for android_path, item_type in items[:max_items]:
            parts = get_relative_parts(android_path)

            if not parts:
                continue

            depth = len(parts) - 1
            indent = "    " * depth
            name = parts[-1]

            if item_type == "dir":
                tree_lines.append(f"{indent}- {name}/")
            else:
                tree_lines.append(f"{indent}- {name}")

        if len(items) > max_items:
            tree_lines.append(
                f"... mais {len(items) - max_items} item(ns) oculto(s)."
            )

        return {
            "root_path": root_path,
            "exists": True,
            "file_count": len(files),
            "folder_count": len(dirs),
            "total_items": len(items),
            "tree_lines": tree_lines,
            "tree_text": "\n".join(tree_lines),
        }

    def get_watch_documents_tree(
        self,
        max_items: int = 1000,
        source_paths: list[str] | None = None,
    ) -> dict:
        roots_to_scan = source_paths or self.get_existing_watch_source_paths()

        root_trees = []

        for root_path in roots_to_scan:
            root_tree = self.get_android_folder_tree(
                root_path=root_path,
                max_items=max_items,
            )

            root_trees.append(root_tree)

        tree_lines: list[str] = []

        for root_tree in root_trees:
            if tree_lines:
                tree_lines.append("")

            tree_lines.extend(root_tree["tree_lines"])

        existing_roots = [
            root_tree["root_path"]
            for root_tree in root_trees
            if root_tree["exists"]
        ]

        return {
            "root_path": " + ".join(existing_roots),
            "file_count": sum(root_tree["file_count"] for root_tree in root_trees),
            "folder_count": sum(root_tree["folder_count"] for root_tree in root_trees),
            "total_items": sum(root_tree["total_items"] for root_tree in root_trees),
            "tree_lines": tree_lines,
            "tree_text": "\n".join(tree_lines),
            "root_trees": root_trees,
        }