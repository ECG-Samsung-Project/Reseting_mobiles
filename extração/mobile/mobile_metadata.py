from datetime import datetime
from pathlib import Path

from core.adb_client import AdbClient
from core.android_fs import AndroidFileSystem
from core.android_metadata import get_android_device_metadata
from core.local_summary import get_local_output_summary

from .config import MobileExtractionConfig
from .participant_resolver import MobileParticipantResolver


class MobileMetadataBuilder:
    def __init__(
        self,
        config: MobileExtractionConfig,
        adb: AdbClient,
        android_fs: AndroidFileSystem,
        participant_resolver: MobileParticipantResolver,
    ) -> None:
        self.config = config
        self.adb = adb
        self.android_fs = android_fs
        self.participant_resolver = participant_resolver

    def build_metadata(
        self,
        participant_id: str,
        mobile_name: str,
        staging_folder: Path,
        archive_path: Path,
        output_root: Path,
        device_id: str,
        timestamp: str,
        participant_resolution: dict,
        collection_context: str,
    ) -> dict:
        extracted_at = datetime.now()
        raw_ring_metadata = self.participant_resolver.get_raw_ring_metadata()
        context = self.config.get_collection_context_metadata(collection_context)

        return {
            "data_type": "mobile",
            "source_type": "mobile_data",

            "collection_context": context["name"],
            "collection_context_code": context["code"],
            "collection_context_label": context["label"],
            "landing_folder": context["folder_name"],

            "participant_id": participant_id,
            "id_participant": participant_id,

            "raw_participant_id": participant_resolution["selected_raw_id"],
            "participant_lookup": {
                "raw_ids": participant_resolution["raw_ids"],
                "selected_raw_id": participant_resolution["selected_raw_id"],
                "lookup_key": participant_resolution["lookup_key"],
                "resolved_participant_id": participant_resolution["participant_id"],
                "lookup_source": participant_resolution["lookup_source"],
                "matched_in_csv": participant_resolution["matched_in_csv"],
                "automatic_resolution_error": participant_resolution.get(
                    "automatic_resolution_error"
                ),
            },

            "mobile_name": mobile_name,

            "extraction_name": archive_path.name,
            "package_name": archive_path.name,

            "timestamp": timestamp,
            "collected_date": extracted_at.strftime("%Y-%m-%d"),
            "extracted_at": extracted_at.isoformat(timespec="seconds"),

            "status": "success",

            "warnings": {
                "has_multiple_valid_ids": participant_resolution["has_multiple_valid_ids"],
                "multiple_valid_ids_count": participant_resolution["multiple_valid_ids_count"],
                "multiple_valid_ids_warning": participant_resolution["multiple_valid_ids_warning"],
            },

            "source": {
                "documents_path": self.config.phone_documents_path,
                "raw_ring_path": self.config.phone_raw_ring_path,
                "participants_summary_csv": str(self.config.participants_summary_csv),
            },

            "output": {
                "output_root": str(output_root),
                "output_archive": str(archive_path),
                "archive_format": "zip",
                "metadata_json": "metadata.json",
            },

            "phone": get_android_device_metadata(
                adb=self.adb,
                device_id=device_id,
                device_name=mobile_name,
                name_field="mobile_name",
            ),

            "phone_documents_summary": self.android_fs.get_path_summary(
                self.config.phone_documents_path,
            ),

            "document_folder_summary": self.android_fs.get_folder_summaries(
                self.config.phone_documents_path,
            ),

            "raw_ring_summary": raw_ring_metadata,

            "local_output_summary": get_local_output_summary(staging_folder),
        }
