from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class ClinicalFilesConfig:
    datalake_root: Path = Path(
        r"C:\Users\Victo\Documents\GitHub\datalake"
    )

    participants_summary_csv: Path = Path(
        r"C:\Users\Victo\Documents\GitHub\datalake\serving\participants_summary\participants_summary.csv"
    )

    @property
    def run_date(self) -> str:
        return datetime.now().strftime("%Y%m%d")

    @property
    def landing_root(self) -> Path:
        return self.datalake_root / "landing"

    def get_output_root(self, data_type: str) -> Path:
        folder_map = {
            "ecg": "ecg_data",
            "looper": "looper_data",
            "holter": "holter_data",
            "eco": "eco_data",
            "redcap": "redcap_data",
        }

        if data_type not in folder_map:
            raise RuntimeError(f"Tipo de arquivo inválido: {data_type}")

        return self.landing_root / folder_map[data_type] / self.run_date