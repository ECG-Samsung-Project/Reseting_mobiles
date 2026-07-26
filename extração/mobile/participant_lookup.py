# mobile/participant_lookup.py

import csv
from pathlib import Path

from .participant_id import ParticipantIdParser


class ParticipantLookup:
    def __init__(self, csv_path: Path) -> None:
        self.csv_path = csv_path

    @staticmethod
    def normalize_csv_value(value: object) -> str:
        if value is None:
            return ""

        text = str(value).strip()

        if text.endswith(".0"):
            text = text[:-2]

        return text

    def load_rows(self) -> list[dict]:
        if not self.csv_path.exists():
            raise RuntimeError(
                f"CSV de participantes não encontrado:\n{self.csv_path}"
            )

        with self.csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            return list(reader)

    def resolve(self, raw_id: str) -> dict:
        clean_id = ParticipantIdParser.remove_id_prefix(raw_id)

        if not clean_id:
            raise RuntimeError("ID bruto vazio. A humanidade insiste em testar limites.")

        if not clean_id.isdigit():
            return {
                "raw_id": raw_id,
                "lookup_key": clean_id,
                "participant_id": clean_id,
                "source": "raw_alphanumeric_id",
                "matched": False,
            }

        rows = self.load_rows()

        for row in rows:
            segundo_id = self.normalize_csv_value(row.get("segundo_id"))

            if segundo_id != clean_id:
                continue

            patient_id = self.normalize_csv_value(row.get("patient_id"))

            if not patient_id:
                raise RuntimeError(
                    f"Encontrei segundo_id {clean_id}, mas patient_id está vazio no CSV."
                )

            return {
                "raw_id": raw_id,
                "lookup_key": clean_id,
                "participant_id": patient_id,
                "source": "participants_summary_csv",
                "matched": True,
            }

        raise RuntimeError(
            f"ID numérico encontrado no celular, mas não achei no CSV.\n\n"
            f"ID bruto: {raw_id}\n"
            f"Chave procurada em segundo_id: {clean_id}\n"
            f"CSV: {self.csv_path}"
        )