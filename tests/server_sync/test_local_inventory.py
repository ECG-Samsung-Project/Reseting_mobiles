import tempfile
import unittest
from pathlib import Path, PurePosixPath

from server_sync.config import DEFAULT_SYNC_FOLDERS, ServerSyncConfig
from server_sync.local_inventory import LocalInventoryScanner


class LocalInventoryScannerTests(unittest.TestCase):
    def make_config(self, local_root: Path) -> ServerSyncConfig:
        return ServerSyncConfig(
            host="example.test",
            username="collector",
            local_raw_root=local_root,
            remote_raw_root=PurePosixPath(
                "/mnt/ecg-dados/datalake/landing/raw"
            ),
        )

    def test_scans_all_folders_with_relative_paths_and_sizes(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            local_root = Path(temporary).resolve()

            for folder in DEFAULT_SYNC_FOLDERS:
                (local_root / folder).mkdir()

            nested = (
                local_root
                / "mobile_fl_data"
                / "participante"
                / "pacote.zip"
            )
            nested.parent.mkdir()
            nested.write_bytes(b"123456")

            records = LocalInventoryScanner().scan(
                self.make_config(local_root)
            )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].folder, "mobile_fl_data")
        self.assertEqual(
            records[0].relative_path,
            PurePosixPath("participante/pacote.zip"),
        )
        self.assertEqual(records[0].size_bytes, 6)

    def test_missing_expected_folder_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            local_root = Path(temporary).resolve()
            (local_root / "mobile_fl_data").mkdir()

            with self.assertRaisesRegex(
                RuntimeError,
                "Pasta local esperada",
            ):
                LocalInventoryScanner().scan(
                    self.make_config(local_root)
                )


if __name__ == "__main__":
    unittest.main()
