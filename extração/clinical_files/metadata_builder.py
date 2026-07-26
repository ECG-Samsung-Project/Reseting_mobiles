from datetime import datetime
from pathlib import Path


class ClinicalFileMetadataBuilder:
    def build_metadata(
        self,
        data_type: str,
        patient_id: str,
        package_folder: Path,
        original_paths: list[Path],
        saved_files: list[Path],
        extracted_from_zip: bool,
        received_folder: bool,
        patient_resolution: dict,
    ) -> dict:
        extracted_at = datetime.now()

        return {
            "data_type": data_type,
            "source_type": f"{data_type}_data",

            "patient_id": patient_id,

            "patient_lookup": {
                "source": patient_resolution["source"],
                "raw_candidate": patient_resolution["raw_candidate"],
                "matched_column": patient_resolution["matched_column"],
                "candidates": patient_resolution.get("candidates", []),
                "matched": patient_resolution["matched"],
            },

            "package_name": package_folder.name,
            "extraction_name": package_folder.name,

            "collected_date": extracted_at.strftime("%Y-%m-%d"),
            "extracted_at": extracted_at.isoformat(timespec="seconds"),

            "status": "success",

            "input": {
                "original_paths": [
                    str(path)
                    for path in original_paths
                ],
                "original_names": [
                    path.name
                    for path in original_paths
                ],
                "has_zip": extracted_from_zip,
                "has_folder": received_folder,
            },

            "output": {
                "output_folder": str(package_folder),
                "metadata_json": str(package_folder / "metadata.json"),
                "saved_files_count": len(saved_files),
                "saved_files": [
                    str(path.relative_to(package_folder))
                    for path in saved_files
                    if path.is_file()
                ],
            },
        }