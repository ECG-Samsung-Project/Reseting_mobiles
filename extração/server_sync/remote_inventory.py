from .config import ServerSyncConfig
from .models import FileRecord, RemoteInventory
from .ssh_client import SshSftpClient


class RemoteInventoryScanner:
    def scan(
        self,
        config: ServerSyncConfig,
        client: SshSftpClient,
    ) -> RemoteInventory:
        files: list[FileRecord] = []
        partial_files: list[FileRecord] = []

        for folder in config.folders:
            folder_root = config.remote_raw_root / folder

            if not client.directory_exists(folder_root):
                continue

            for remote_path, size_bytes in client.iter_files(folder_root):
                relative_path = remote_path.relative_to(folder_root)
                record = FileRecord(
                    folder=folder,
                    relative_path=relative_path,
                    size_bytes=size_bytes,
                    remote_path=remote_path,
                )

                if remote_path.name.endswith(".part"):
                    partial_files.append(record)
                else:
                    files.append(record)

        return RemoteInventory(
            files=tuple(sorted(files, key=lambda record: record.key)),
            partial_files=tuple(
                sorted(partial_files, key=lambda record: record.key)
            ),
        )
