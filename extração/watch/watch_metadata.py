from datetime import datetime
from pathlib import Path

from core.adb_client import AdbClient
from core.android_fs import AndroidFileSystem
from core.android_metadata import get_android_device_metadata
from core.local_summary import get_local_output_summary

from .config import WatchExtractionConfig
from .watch_connection import WatchConnectionManager


class WatchMetadataBuilder:
    def __init__(
        self,
        config: WatchExtractionConfig,
        adb: AdbClient,
        android_fs: AndroidFileSystem,
        connection_manager: WatchConnectionManager,
    ) -> None:
        self.config = config
        self.adb = adb
        self.android_fs = android_fs
        self.connection_manager = connection_manager

    def build_metadata(
        self,
        selected_id: str,
        id_metadata: dict,
        watch_name: str,
        destination_folder: Path,
        device_id: str,
        timestamp: str,
        connection: dict,
    ) -> dict:
        extracted_at = datetime.now()

        return {
            "data_type": "watch",
            "source_type": "watch_data",

            "watch_id": selected_id,
            "selected_id": selected_id,

            "watch_name": watch_name,

            "connection": {
                "ip": connection["ip"],
                "pairing_port": connection["pairing_port"] or None,
                "connect_port": connection["connect_port"] or None,
                "pairing_address": self.connection_manager.get_optional_address(
                    connection["ip"],
                    connection["pairing_port"],
                ),
                "connect_address": self.connection_manager.get_optional_address(
                    connection["ip"],
                    connection["connect_port"],
                ),
                "target_device_id": self.adb.target_device_id,
            },

            "extraction_name": destination_folder.name,
            "package_name": destination_folder.name,

            "timestamp": timestamp,
            "collected_date": extracted_at.strftime("%Y-%m-%d"),
            "extracted_at": extracted_at.isoformat(timespec="seconds"),

            "status": "success",

            "warnings": {
                "has_valid_id": id_metadata["has_valid_id"],
                "has_multiple_valid_ids": id_metadata["has_multiple_valid_ids"],
                "multiple_valid_ids_count": id_metadata["multiple_valid_ids_count"],
                "multiple_valid_ids_warning": id_metadata["multiple_valid_ids_warning"],
            },

            "source": {
                "documents_path": self.config.watch_documents_path,
            },

            "output": {
                "output_root": str(self.config.output_root),
                "output_folder": str(destination_folder),
                "metadata_json": str(destination_folder / "metadata.json"),
            },

            "watch": get_android_device_metadata(
                adb=self.adb,
                device_id=device_id,
                device_name=watch_name,
                name_field="watch_name",
            ),

            "id_summary": id_metadata,

            "watch_documents_summary": self.android_fs.get_path_summary(
                self.config.watch_documents_path,
            ),

            "document_folder_summary": self.android_fs.get_folder_summaries(
                self.config.watch_documents_path,
            ),

            "local_output_summary": get_local_output_summary(destination_folder),
        }