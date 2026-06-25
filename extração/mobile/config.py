from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class MobileExtractionConfig:
    adb_path: str = "adb"
    phone_documents_path: str = "/sdcard/Documents"
    phone_raw_ring_path: str = "/sdcard/Documents/RAW_DATA_RING"
    landing_mobile_root: Path = Path(
        r"C:\Users\Victo\Documents\GitHub\datalake\landing\mobile_data"
    )

    @property
    def output_root(self) -> Path:
        run_date = datetime.now().strftime("%Y%m%d")
        return self.landing_mobile_root / run_date