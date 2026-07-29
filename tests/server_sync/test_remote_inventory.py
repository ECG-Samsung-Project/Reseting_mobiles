import unittest
from pathlib import Path, PurePosixPath

from server_sync.config import ServerSyncConfig
from server_sync.remote_inventory import RemoteInventoryScanner


class FakeInventoryClient:
    def directory_exists(self, folder_root: PurePosixPath) -> bool:
        return folder_root.name == "mobile_fl_data"

    def iter_files(self, folder_root: PurePosixPath):
        if folder_root.name == "mobile_fl_data":
            yield folder_root / "package.zip", 100
            yield folder_root / "package.zip.abc.part", 50


class RemoteInventoryScannerTests(unittest.TestCase):
    def test_separates_partial_files_from_definitive_inventory(self) -> None:
        config = ServerSyncConfig(
            host="example.test",
            username="collector",
            local_raw_root=Path("C:/local"),
            remote_raw_root=PurePosixPath("/remote/raw"),
        )

        inventory = RemoteInventoryScanner().scan(
            config,
            FakeInventoryClient(),  # type: ignore[arg-type]
        )

        self.assertEqual(len(inventory.files), 1)
        self.assertEqual(inventory.files[0].key, "mobile_fl_data/package.zip")
        self.assertEqual(len(inventory.partial_files), 1)
        self.assertTrue(
            inventory.partial_files[0].relative_path.name.endswith(".part")
        )

    def test_missing_remote_folders_are_treated_as_empty(self) -> None:
        config = ServerSyncConfig(
            host="example.test",
            username="collector",
            local_raw_root=Path("C:/local"),
            remote_raw_root=PurePosixPath("/remote/raw"),
        )

        inventory = RemoteInventoryScanner().scan(
            config,
            FakeInventoryClient(),  # type: ignore[arg-type]
        )

        self.assertEqual(
            tuple(record.key for record in inventory.files),
            ("mobile_fl_data/package.zip",),
        )


if __name__ == "__main__":
    unittest.main()
