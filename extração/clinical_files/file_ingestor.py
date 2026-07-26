import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from core.destination import build_unique_destination_folder
from core.metadata_writer import write_json_metadata

from .config import ClinicalFilesConfig
from .metadata_builder import ClinicalFileMetadataBuilder
from .patient_id_resolver import ClinicalPatientIdResolver


class ClinicalFileIngestor:
    def __init__(
        self,
        config: ClinicalFilesConfig,
    ) -> None:
        self.config = config
        self.metadata_builder = ClinicalFileMetadataBuilder()
        self.patient_id_resolver = ClinicalPatientIdResolver(
            participants_summary_csv=self.config.participants_summary_csv
        )

    @staticmethod
    def is_zip_file(path: Path) -> bool:
        return path.is_file() and path.suffix.lower() == ".zip"

    @staticmethod
    def safe_extract_zip(
        zip_path: Path,
        destination_folder: Path,
    ) -> list[Path]:
        extracted_files: list[Path] = []

        with zipfile.ZipFile(zip_path, "r") as zip_file:
            for member in zip_file.infolist():
                member_path = destination_folder / member.filename

                resolved_destination = member_path.resolve()
                resolved_root = destination_folder.resolve()

                if not str(resolved_destination).startswith(str(resolved_root)):
                    raise RuntimeError(
                        f"ZIP inseguro detectado: {member.filename}"
                    )

                zip_file.extract(member, destination_folder)

        for item in destination_folder.rglob("*"):
            if item.is_file():
                extracted_files.append(item)

        return extracted_files

    @staticmethod
    def copy_file_to_folder(
        source_file: Path,
        destination_folder: Path,
    ) -> Path:
        destination_file = destination_folder / source_file.name
        shutil.copy2(source_file, destination_file)
        return destination_file

    @staticmethod
    def copy_folder_contents_to_folder(
        source_folder: Path,
        destination_folder: Path,
    ) -> list[Path]:
        saved_files: list[Path] = []

        for item in source_folder.iterdir():
            destination_item = destination_folder / item.name

            if item.is_dir():
                shutil.copytree(item, destination_item)
            else:
                shutil.copy2(item, destination_item)

        for item in destination_folder.rglob("*"):
            if item.is_file():
                saved_files.append(item)

        return saved_files

    def build_package_folder(
        self,
        data_type: str,
        patient_id: str,
    ) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        output_root = self.config.get_output_root(data_type)
        output_root.mkdir(parents=True, exist_ok=True)

        folder_name = f"{patient_id}_{timestamp}"

        return build_unique_destination_folder(
            output_root=output_root,
            folder_name=folder_name,
        )

    def validate_input_paths(
        self,
        input_paths: list[str],
    ) -> list[Path]:
        if not input_paths:
            raise RuntimeError("Selecione pelo menos um arquivo ou pasta.")

        source_paths = [
            Path(path)
            for path in input_paths
        ]

        for path in source_paths:
            if not path.exists():
                raise RuntimeError(f"Caminho não encontrado:\n{path}")

            if not path.is_file() and not path.is_dir():
                raise RuntimeError(f"Caminho inválido:\n{path}")

        return source_paths

    def ingest_one_path(
        self,
        data_type: str,
        patient_id: str,
        source_path: Path,
    ) -> dict:
        patient_resolution = self.patient_id_resolver.resolve_manual_or_from_paths(
            manual_patient_id=patient_id,
            input_paths=[source_path],
        )

        resolved_patient_id = patient_resolution["patient_id"]

        package_folder = self.build_package_folder(
            data_type=data_type,
            patient_id=resolved_patient_id,
        )

        package_folder.mkdir(parents=True, exist_ok=True)

        saved_files: list[Path] = []
        extracted_from_zip = False
        received_folder = False

        try:
            if source_path.is_dir():
                received_folder = True

                saved_files.extend(
                    self.copy_folder_contents_to_folder(
                        source_folder=source_path,
                        destination_folder=package_folder,
                    )
                )

            elif self.is_zip_file(source_path):
                extracted_from_zip = True

                saved_files.extend(
                    self.safe_extract_zip(
                        zip_path=source_path,
                        destination_folder=package_folder,
                    )
                )

            else:
                saved_files.append(
                    self.copy_file_to_folder(
                        source_file=source_path,
                        destination_folder=package_folder,
                    )
                )

            metadata = self.metadata_builder.build_metadata(
                data_type=data_type,
                patient_id=resolved_patient_id,
                package_folder=package_folder,
                original_paths=[source_path],
                saved_files=saved_files,
                extracted_from_zip=extracted_from_zip,
                received_folder=received_folder,
                patient_resolution=patient_resolution,
            )

            metadata_path = write_json_metadata(
                metadata=metadata,
                json_path=package_folder / "metadata.json",
            )

            return {
                "data_type": data_type,
                "patient_id": resolved_patient_id,
                "patient_resolution": patient_resolution,
                "source_path": source_path,
                "package_folder": package_folder,
                "metadata_path": metadata_path,
                "saved_files_count": len(saved_files),
                "extracted_from_zip": extracted_from_zip,
                "received_folder": received_folder,
                "status": "success",
            }

        except Exception:
            shutil.rmtree(package_folder, ignore_errors=True)
            raise

    def ingest_many_paths(
        self,
        data_type: str,
        patient_id: str,
        input_paths: list[str],
    ) -> dict:
        source_paths = self.validate_input_paths(input_paths)

        results = []
        errors = []

        for source_path in source_paths:
            try:
                result = self.ingest_one_path(
                    data_type=data_type,
                    patient_id=patient_id,
                    source_path=source_path,
                )

                results.append(result)

            except Exception as error:
                errors.append(
                    {
                        "source_path": source_path,
                        "error": str(error),
                    }
                )

        return {
            "data_type": data_type,
            "total_inputs": len(source_paths),
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors,
        }