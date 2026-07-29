import tempfile
import unittest
from pathlib import Path

from server_sync.config import DEFAULT_SYNC_FOLDERS, ServerSyncConfig


class ServerSyncConfigTests(unittest.TestCase):
    def make_values(self, local_root: Path) -> dict[str, str]:
        return {
            "ECG_SYNC_HOST": "example.test",
            "ECG_SYNC_PORT": "2222",
            "ECG_SYNC_USER": "collector",
            "ECG_SYNC_LOCAL_RAW_ROOT": str(local_root),
            "ECG_SYNC_REMOTE_RAW_ROOT": (
                "/mnt/ecg-dados/datalake/landing/raw"
            ),
            "ECG_SYNC_VERIFY_SHA256": "true",
        }

    def test_loads_and_validates_expected_values(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            local_root = Path(temporary).resolve()
            config = ServerSyncConfig.from_mapping(
                self.make_values(local_root)
            )

        self.assertEqual(config.host, "example.test")
        self.assertEqual(config.port, 2222)
        self.assertEqual(config.username, "collector")
        self.assertEqual(config.folders, DEFAULT_SYNC_FOLDERS)
        self.assertIn("ecg_data", config.folders)
        self.assertIn("blood_test_data", config.folders)
        self.assertEqual(len(config.folders), 11)
        self.assertEqual(config.authentication_method, "auto")
        self.assertTrue(config.verify_sha256)
        self.assertNotIn("password", config.safe_connection_summary())

    def test_rejects_relative_remote_root(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            values = self.make_values(Path(temporary).resolve())
            values["ECG_SYNC_REMOTE_RAW_ROOT"] = "landing/raw"

            with self.assertRaisesRegex(
                RuntimeError,
                "caminho Linux absoluto",
            ):
                ServerSyncConfig.from_mapping(values)

    def test_rejects_nested_sync_folder(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            values = self.make_values(Path(temporary).resolve())
            values["ECG_SYNC_FOLDERS"] = "mobile_fl_data/outra"

            with self.assertRaisesRegex(
                RuntimeError,
                "apenas um nome de pasta",
            ):
                ServerSyncConfig.from_mapping(values)

    def test_accepts_password_authentication_without_stored_password(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            values = self.make_values(Path(temporary).resolve())
            values["ECG_SYNC_AUTH_METHOD"] = "password"
            values["ECG_SYNC_PASSWORD"] = ""
            config = ServerSyncConfig.from_mapping(values)

        self.assertEqual(config.authentication_method, "password")
        self.assertIsNone(config.password)

    def test_rejects_unknown_authentication_method(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            values = self.make_values(Path(temporary).resolve())
            values["ECG_SYNC_AUTH_METHOD"] = "magic"

            with self.assertRaisesRegex(
                RuntimeError,
                "auto, password ou key",
            ):
                ServerSyncConfig.from_mapping(values)


if __name__ == "__main__":
    unittest.main()
