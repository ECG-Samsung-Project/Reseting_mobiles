from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class WatchExtractionConfig:
    adb_path: str = "adb"

    watch_documents_path: str = "/sdcard/Documents"

    landing_watch_root: Path = Path(
        r"C:\Users\Victo\Documents\GitHub\datalake\landing\watch_data"
    )

    @property
    def output_root(self) -> Path:
        run_date = datetime.now().strftime("%Y%m%d")
        return self.landing_watch_root / run_date