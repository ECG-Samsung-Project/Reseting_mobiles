import hashlib
import tempfile
import unittest
from pathlib import Path, PurePosixPath

from server_sync.config import ServerSyncConfig
from server_sync.models import (
    ComparisonEntry,
    ComparisonStatus,
    FileRecord,
    UploadStatus,
)
from server_sync.ssh_client import RemoteHashUnavailable
from server_sync.upload_service import UploadService


class FakeSftpClient:
    def __init__(
        self,
        remote_hash_mismatch: bool = False,
        remote_hash_unavailable: bool = False,
    ) -> None:
        self.files: dict[PurePosixPath, bytes] = {}
        self.remote_hash_mismatch = remote_hash_mismatch
        self.remote_hash_unavailable = remote_hash_unavailable
        self.renames: list[tuple[PurePosixPath, PurePosixPath]] = []

    def stat_size(self, remote_path: PurePosixPath) -> int | None:
        content = self.files.get(remote_path)
        return len(content) if content is not None else None

    def ensure_directory(
        self,
        remote_directory: PurePosixPath,
        base_directory: PurePosixPath,
    ) -> None:
        remote_directory.relative_to(base_directory)

    def upload_file(
        self,
        local_path: Path,
        remote_path: PurePosixPath,
        callback=None,
    ) -> None:
        content = local_path.read_bytes()
        self.files[remote_path] = content

        if callback:
            callback(len(content), len(content))

    def remote_sha256(self, remote_path: PurePosixPath) -> str:
        if self.remote_hash_unavailable:
            raise RemoteHashUnavailable("sha256sum indisponível")

        if self.remote_hash_mismatch:
            return "0" * 64

        return hashlib.sha256(self.files[remote_path]).hexdigest()

    def rename_no_overwrite(
        self,
        source: PurePosixPath,
        destination: PurePosixPath,
    ) -> None:
        if destination in self.files:
            raise FileExistsError(destination)

        self.files[destination] = self.files.pop(source)
        self.renames.append((source, destination))


class UploadServiceTests(unittest.TestCase):
    def make_config(self, local_root: Path) -> ServerSyncConfig:
        return ServerSyncConfig(
            host="example.test",
            username="collector",
            local_raw_root=local_root,
            remote_raw_root=PurePosixPath(
                "/mnt/ecg-dados/datalake/landing/raw"
            ),
            verify_sha256=True,
        )

    def make_entry(self, local_path: Path) -> ComparisonEntry:
        return ComparisonEntry(
            status=ComparisonStatus.NEW,
            local=FileRecord(
                folder="mobile_fl_data",
                relative_path=PurePosixPath(local_path.name),
                size_bytes=local_path.stat().st_size,
                local_path=local_path,
            ),
            remote=None,
        )

    def test_uploads_part_validates_hash_and_renames(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            local_root = Path(temporary).resolve()
            local_path = local_root / "package.zip"
            local_path.write_bytes(b"safe payload")
            client = FakeSftpClient()
            service = UploadService(
                self.make_config(local_root),
                client,  # type: ignore[arg-type]
            )

            batch = service.upload((self.make_entry(local_path),))

        result = batch.results[0]
        final_path = PurePosixPath(
            "/mnt/ecg-dados/datalake/landing/raw/"
            "mobile_fl_data/package.zip"
        )
        self.assertEqual(result.status, UploadStatus.SUCCESS)
        self.assertTrue(result.hash_verified)
        self.assertIn(final_path, client.files)
        self.assertEqual(len(client.renames), 1)
        self.assertTrue(str(client.renames[0][0]).endswith(".part"))

    def test_hash_mismatch_keeps_part_and_does_not_rename(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            local_root = Path(temporary).resolve()
            local_path = local_root / "package.zip"
            local_path.write_bytes(b"safe payload")
            client = FakeSftpClient(remote_hash_mismatch=True)
            service = UploadService(
                self.make_config(local_root),
                client,  # type: ignore[arg-type]
            )

            batch = service.upload((self.make_entry(local_path),))

        result = batch.results[0]
        self.assertEqual(result.status, UploadStatus.FAILED)
        self.assertEqual(client.renames, [])
        self.assertIsNotNone(result.temporary_remote_path)
        self.assertIn(result.temporary_remote_path, client.files)

    def test_hash_unavailable_uses_size_validation_and_finishes(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            local_root = Path(temporary).resolve()
            local_path = local_root / "package.zip"
            local_path.write_bytes(b"safe payload")
            client = FakeSftpClient(remote_hash_unavailable=True)
            service = UploadService(
                self.make_config(local_root),
                client,  # type: ignore[arg-type]
            )

            batch = service.upload((self.make_entry(local_path),))

        result = batch.results[0]
        self.assertEqual(result.status, UploadStatus.SUCCESS)
        self.assertFalse(result.hash_verified)
        self.assertIn("validação de tamanho", result.message)

    def test_existing_different_size_blocks_upload(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            local_root = Path(temporary).resolve()
            local_path = local_root / "package.zip"
            local_path.write_bytes(b"local payload")
            client = FakeSftpClient()
            final_path = PurePosixPath(
                "/mnt/ecg-dados/datalake/landing/raw/"
                "mobile_fl_data/package.zip"
            )
            client.files[final_path] = b"different"
            service = UploadService(
                self.make_config(local_root),
                client,  # type: ignore[arg-type]
            )

            batch = service.upload((self.make_entry(local_path),))

        result = batch.results[0]
        self.assertEqual(result.status, UploadStatus.BLOCKED_CONFLICT)
        self.assertEqual(client.files[final_path], b"different")
        self.assertEqual(client.renames, [])


if __name__ == "__main__":
    unittest.main()
