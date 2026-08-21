import unittest
from pathlib import PurePosixPath

from server_sync.data_status import STATUS_FOLDERS, build_participant_status
from server_sync.models import FileRecord, RemoteInventory


def remote_file(folder: str, relative_path: str) -> FileRecord:
    return FileRecord(
        folder=folder,
        relative_path=PurePosixPath(relative_path),
        size_bytes=10,
    )


class ParticipantDataStatusTests(unittest.TestCase):
    def test_builds_one_row_per_participant_and_folder_status(self) -> None:
        inventory = RemoteInventory(
            files=(
                remote_file("ecg_data", "EDI-21-2196_exam.zip"),
                remote_file("ecg_data", "HCM-32-3881_exam.zip"),
                remote_file("holter_data", "EDI-21-2196_exam.zip"),
                remote_file("bio_data", "Bioimpedancia_EDI_HCM.xlsx"),
                remote_file("watch_ic_data", "HCM-32-3881_watch.zip"),
            )
        )

        rows = build_participant_status(inventory)

        self.assertEqual(
            [row.participant_id for row in rows],
            ["EDI-21-2196", "HCM-32-3881"],
        )
        folder_indexes = {
            folder: index
            for index, (_label, folder) in enumerate(STATUS_FOLDERS)
        }
        edi, hcm = rows
        self.assertTrue(edi.available_by_folder[folder_indexes["bio_data"]])
        self.assertTrue(edi.available_by_folder[folder_indexes["ecg_data"]])
        self.assertTrue(edi.available_by_folder[folder_indexes["holter_data"]])
        self.assertFalse(edi.available_by_folder[folder_indexes["watch_ic_data"]])
        self.assertTrue(hcm.available_by_folder[folder_indexes["bio_data"]])
        self.assertTrue(hcm.available_by_folder[folder_indexes["watch_ic_data"]])

    def test_ignores_partial_files_and_paths_without_participant_id(self) -> None:
        inventory = RemoteInventory(
            files=(remote_file("ecg_data", "arquivo_sem_id.zip"),),
            partial_files=(
                remote_file("ecg_data", "EDI-21-2196_exam.zip.part"),
            ),
        )

        self.assertEqual(build_participant_status(inventory), ())

    def test_does_not_confuse_participants_with_same_letter_prefix(self) -> None:
        inventory = RemoteInventory(
            files=(
                remote_file("ecg_data", "ZEL-18-5394_exam.zip"),
                remote_file("mobile_fl_data", "ZEL-19-5394_mobile.zip"),
            )
        )

        rows = {
            row.participant_id: row for row in build_participant_status(inventory)
        }
        folder_indexes = {
            folder: index
            for index, (_label, folder) in enumerate(STATUS_FOLDERS)
        }

        self.assertFalse(
            rows["ZEL-18-5394"].available_by_folder[
                folder_indexes["mobile_fl_data"]
            ]
        )
        self.assertFalse(
            rows["ZEL-19-5394"].available_by_folder[
                folder_indexes["ecg_data"]
            ]
        )


if __name__ == "__main__":
    unittest.main()
