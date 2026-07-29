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

    def get_source_summaries(
        self,
        source_paths: list[str],
    ) -> list[dict]:
        summaries: list[dict] = []

        for source_path in source_paths:
            source_summary: dict = {
                "source_path": source_path,
            }

            try:
                source_summary["path_summary"] = (
                    self.android_fs.get_path_summary(source_path)
                )
            except Exception as error:
                source_summary["path_summary_error"] = str(error)

            try:
                source_summary["folder_summary"] = (
                    self.android_fs.get_folder_summaries(source_path)
                )
            except Exception as error:
                source_summary["folder_summary_error"] = str(error)

            summaries.append(source_summary)

        return summaries

    def build_metadata(
        self,
        selected_id: str,
        id_metadata: dict,
        watch_name: str,
        staging_folder: Path,
        archive_path: Path,
        output_root: Path,
        device_id: str,
        timestamp: str,
        connection: dict,
        collection_context: str,
        source_paths: list[str],
        copied_sources: list[str],
    ) -> dict:
        extracted_at = datetime.now()
        collection_metadata = self.config.get_collection_context_metadata(
            collection_context
        )

        return {
            "data_type": "watch",
            "source_type": "watch_data",

            "collection_context": collection_context,
            "collection_context_code": collection_metadata["code"],
            "collection_context_label": collection_metadata["label"],
            "landing_folder": collection_metadata["folder_name"],

            "participant_id": selected_id,
            "id_participant": selected_id,
            "watch_id": selected_id,
            "selected_id": selected_id,

            "id_resolution": {
                "selected_id": selected_id,
                "resolution_source": id_metadata.get("resolution_source"),
                "automatic_id_found": id_metadata.get(
                    "automatic_id_found",
                    False,
                ),
                "source_path": id_metadata.get("source_path"),
                "warning": id_metadata.get("warning"),
            },

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

            "extraction_name": archive_path.stem,
            "package_name": archive_path.stem,

            "timestamp": timestamp,
            "collected_date": extracted_at.strftime("%Y-%m-%d"),
            "extracted_at": extracted_at.isoformat(timespec="seconds"),

            "status": "success",

            "warnings": {
                "has_valid_id": id_metadata.get("has_valid_id", False),
                "automatic_id_found": id_metadata.get(
                    "automatic_id_found",
                    False,
                ),
                "has_multiple_valid_ids": id_metadata.get(
                    "has_multiple_valid_ids",
                    False,
                ),
                "multiple_valid_ids_count": id_metadata.get(
                    "multiple_valid_ids_count",
                    0,
                ),
                "multiple_valid_ids_warning": id_metadata.get(
                    "multiple_valid_ids_warning"
                ),
                "id_resolution_warning": id_metadata.get("warning"),
            },

            "source": {
                "configured_documents_path": self.config.watch_documents_path,
                "source_paths_checked": source_paths,
                "source_paths_copied": copied_sources,
            },

            "output": {
                "output_root": str(output_root),
                "output_archive": str(archive_path),
                "archive_format": "zip",
                "metadata_json": "metadata.json",
            },

            "watch": get_android_device_metadata(
                adb=self.adb,
                device_id=device_id,
                device_name=watch_name,
                name_field="watch_name",
            ),

            "id_summary": id_metadata,

            "watch_source_summaries": self.get_source_summaries(
                source_paths
            ),

            "local_output_summary": get_local_output_summary(
                staging_folder
            ),
        }