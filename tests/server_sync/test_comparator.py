import unittest
from pathlib import Path, PurePosixPath

from server_sync.comparator import InventoryComparator
from server_sync.models import ComparisonStatus, FileRecord


def local_record(path: str, size: int) -> FileRecord:
    relative_path = PurePosixPath(path)
    return FileRecord(
        folder="mobile_fl_data",
        relative_path=relative_path,
        size_bytes=size,
        local_path=Path("C:/local") / Path(*relative_path.parts),
    )


def remote_record(path: str, size: int) -> FileRecord:
    relative_path = PurePosixPath(path)
    return FileRecord(
        folder="mobile_fl_data",
        relative_path=relative_path,
        size_bytes=size,
        remote_path=(
            PurePosixPath("/remote/mobile_fl_data") / relative_path
        ),
    )


class InventoryComparatorTests(unittest.TestCase):
    def test_classifies_all_four_comparison_states(self) -> None:
        report = InventoryComparator.compare(
            local_files=(
                local_record("new.zip", 10),
                local_record("sent.zip", 20),
                local_record("conflict.zip", 30),
            ),
            remote_files=(
                remote_record("sent.zip", 20),
                remote_record("conflict.zip", 31),
                remote_record("remote.zip", 40),
            ),
        )

        statuses = {
            entry.key: entry.status
            for entry in report.entries
        }

        self.assertEqual(
            statuses["mobile_fl_data/new.zip"],
            ComparisonStatus.NEW,
        )
        self.assertEqual(
            statuses["mobile_fl_data/sent.zip"],
            ComparisonStatus.ALREADY_SENT,
        )
        self.assertEqual(
            statuses["mobile_fl_data/conflict.zip"],
            ComparisonStatus.CONFLICT,
        )
        self.assertEqual(
            statuses["mobile_fl_data/remote.zip"],
            ComparisonStatus.REMOTE_ONLY,
        )

    def test_same_filename_in_different_relative_folders_is_distinct(self) -> None:
        report = InventoryComparator.compare(
            local_files=(local_record("a/package.zip", 10),),
            remote_files=(remote_record("b/package.zip", 10),),
        )

        self.assertEqual(report.count(ComparisonStatus.NEW), 1)
        self.assertEqual(report.count(ComparisonStatus.REMOTE_ONLY), 1)

    def test_partial_files_are_not_compared_as_definitive_files(self) -> None:
        partial = remote_record("package.zip.abc.part", 8)
        report = InventoryComparator.compare(
            local_files=(local_record("package.zip", 8),),
            remote_files=(),
            remote_partial_files=(partial,),
        )

        self.assertEqual(report.count(ComparisonStatus.NEW), 1)
        self.assertEqual(report.remote_partial_files, (partial,))


if __name__ == "__main__":
    unittest.main()
