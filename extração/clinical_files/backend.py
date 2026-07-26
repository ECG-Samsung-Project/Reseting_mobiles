from typing import Callable

from .config import ClinicalFilesConfig
from .file_ingestor import ClinicalFileIngestor


StatusCallback = Callable[[str], None] | None


class ClinicalFilesBackend:
    def __init__(
        self,
        config: ClinicalFilesConfig | None = None,
    ) -> None:
        self.config = config or ClinicalFilesConfig()
        self.ingestor = ClinicalFileIngestor(self.config)

    def ingest_paths(
        self,
        data_type: str,
        patient_id: str,
        input_paths: list[str],
        status_callback: StatusCallback = None,
    ) -> dict:
        def set_status(text: str) -> None:
            if status_callback:
                status_callback(text)

        set_status("Validando arquivos e pastas...")

        result = self.ingestor.ingest_many_paths(
            data_type=data_type,
            patient_id=patient_id,
            input_paths=input_paths,
        )

        set_status("Importação finalizada.")

        return result

    def get_output_preview(self, data_type: str) -> str:
        return str(self.config.get_output_root(data_type))