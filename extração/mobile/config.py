# mobile/config.py

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


@dataclass(frozen=True)
class MobileExtractionConfig:
    COLLECTION_CONTEXTS: ClassVar[dict[str, dict[str, str]]] = {
        "free_living": {
            "code": "fl",
            "label": "Free Living",
            "folder_name": "mobile_fl_data",
        },
        "in_clinic": {
            "code": "ic",
            "label": "In Clinic",
            "folder_name": "mobile_ic_data",
        },
    }

    adb_path: str = "adb"

    phone_documents_path: str = "/sdcard/Documents/"
    phone_raw_ring_path: str = "/sdcard/Documents/RAW_DATA_RING"

    landing_mobile_base_root: Path = Path(
        r"C:\Users\Victo\Documents\GitHub\datalake\landing\raw"
    )

    participants_summary_csv: Path = Path(
        r"C:\Users\Victo\Documents\GitHub\datalake\serving\participants_summary\participants_summary.csv"
    )

    @classmethod
    def normalize_collection_context(cls, collection_context: str) -> str:
        normalized = (
            collection_context
            .strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )

        aliases = {
            "fl": "free_living",
            "freeliving": "free_living",
            "free_living": "free_living",
            "ic": "in_clinic",
            "inclinic": "in_clinic",
            "in_clinic": "in_clinic",
        }

        resolved = aliases.get(normalized)

        if resolved is None:
            valid_options = ", ".join(cls.COLLECTION_CONTEXTS)
            raise RuntimeError(
                "Contexto de coleta inválido. "
                f"Use uma destas opções: {valid_options}."
            )

        return resolved

    @classmethod
    def get_collection_context_metadata(
        cls,
        collection_context: str,
    ) -> dict[str, str]:
        normalized = cls.normalize_collection_context(collection_context)

        return {
            "name": normalized,
            **cls.COLLECTION_CONTEXTS[normalized],
        }

    def get_output_root(self, collection_context: str) -> Path:
        context = self.get_collection_context_metadata(collection_context)

        return (
            self.landing_mobile_base_root
            / context["folder_name"]
        )