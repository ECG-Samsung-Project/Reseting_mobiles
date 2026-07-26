import csv
import re
from pathlib import Path


class ClinicalPatientIdResolver:
    patient_id_regex = re.compile(
        r"([A-Z]{2,5}-\d{2,4}-\d{3,5}|Id\d+|\d{6,12})",
        re.IGNORECASE,
    )

    def __init__(self, participants_summary_csv: Path) -> None:
        self.participants_summary_csv = participants_summary_csv
        self._rows: list[dict] | None = None

    @staticmethod
    def normalize_value(value: object) -> str:
        if value is None:
            return ""

        text = str(value).strip()

        if text.endswith(".0"):
            text = text[:-2]

        return text

    @staticmethod
    def remove_id_prefix(value: str) -> str:
        value = value.strip()

        if value.lower().startswith("id"):
            return value[2:]

        return value

    def load_rows(self) -> list[dict]:
        if self._rows is not None:
            return self._rows

        if not self.participants_summary_csv.exists():
            raise RuntimeError(
                f"participants_summary.csv não encontrado:\n{self.participants_summary_csv}"
            )

        with self.participants_summary_csv.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            self._rows = list(reader)

        return self._rows

    def find_candidate_ids_from_text(self, text: str) -> list[str]:
        candidates: list[str] = []

        for match in self.patient_id_regex.findall(text):
            value = match.strip()

            if value not in candidates:
                candidates.append(value)

        return candidates

    def resolve_candidate(self, candidate: str) -> dict | None:
        rows = self.load_rows()

        raw_candidate = candidate.strip()
        candidate_without_prefix = self.remove_id_prefix(raw_candidate)

        for row in rows:
            patient_id = self.normalize_value(row.get("patient_id"))
            segundo_id = self.normalize_value(row.get("segundo_id"))

            if raw_candidate.upper() == patient_id.upper():
                return {
                    "patient_id": patient_id,
                    "raw_candidate": raw_candidate,
                    "matched_column": "patient_id",
                    "matched": True,
                }

            if candidate_without_prefix and candidate_without_prefix == segundo_id:
                return {
                    "patient_id": patient_id,
                    "raw_candidate": raw_candidate,
                    "matched_column": "segundo_id",
                    "matched": True,
                }

        return None

    def resolve_from_text(self, text: str) -> dict:
        candidates = self.find_candidate_ids_from_text(text)

        for candidate in candidates:
            resolved = self.resolve_candidate(candidate)

            if resolved:
                resolved["candidates"] = candidates
                return resolved

        raise RuntimeError(
            "Não consegui identificar um patient_id válido pelo nome do arquivo/pasta.\n\n"
            f"Candidatos encontrados: {candidates or 'nenhum'}\n"
            f"CSV usado: {self.participants_summary_csv}"
        )

    def resolve_manual_or_from_paths(
        self,
        manual_patient_id: str,
        input_paths: list[Path],
    ) -> dict:
        manual_patient_id = manual_patient_id.strip()

        if manual_patient_id:
            resolved = self.resolve_candidate(manual_patient_id)

            if not resolved:
                raise RuntimeError(
                    f"ID informado manualmente não existe no participants_summary.csv:\n{manual_patient_id}"
                )

            resolved["source"] = "manual_input"
            resolved["candidates"] = [manual_patient_id]
            return resolved

        search_text = "\n".join(
            [
                str(path.name)
                for path in input_paths
            ]
        )

        resolved = self.resolve_from_text(search_text)
        resolved["source"] = "input_path_name"

        return resolved