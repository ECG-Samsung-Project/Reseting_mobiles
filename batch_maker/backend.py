import csv
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


PATIENT_ID_REGEX = re.compile(
    r"([A-Z]{2,5}-\d{2,4}-\d{3,5}|Id\d+|\d{6,12})",
    re.IGNORECASE,
)


@dataclass
class SourceConfig:
    name: str
    root: Path
    recursive: bool = True
    scope: str = "patient"


class BatchMakerBackend:
    def __init__(self) -> None:
        self.app_root = Path(__file__).resolve().parent
        self.config_path = self.app_root / "data_sources.json"
        self.output_root = self.app_root / "output"

        self.config = self.load_or_create_config()
        self.output_root.mkdir(parents=True, exist_ok=True)

    def load_or_create_config(self) -> dict:
        if not self.config_path.exists():
            default_config = {
                "participants_summary_csv": (
                    r"C:\Users\Victo\Documents\GitHub\datalake"
                    r"\serving\participants_summary\participants_summary.csv"
                ),
                "output_root": "output",
                "sources": [
                    {
                        "name": "mobile_landing",
                        "root": (
                            r"C:\Users\Victo\Documents\GitHub\datalake"
                            r"\landing\mobile_data"
                        ),
                        "recursive": True,
                        "scope": "patient",
                    },
                    {
                        "name": "watch_landing",
                        "root": (
                            r"C:\Users\Victo\Documents\GitHub\datalake"
                            r"\landing\watch_data"
                        ),
                        "recursive": True,
                        "scope": "patient",
                    },
                    {
                        "name": "ecg_landing",
                        "root": (
                            r"C:\Users\Victo\Documents\GitHub\datalake"
                            r"\landing\ecg_data"
                        ),
                        "recursive": True,
                        "scope": "patient",
                    },
                    {
                        "name": "looper_landing",
                        "root": (
                            r"C:\Users\Victo\Documents\GitHub\datalake"
                            r"\landing\looper_data"
                        ),
                        "recursive": True,
                        "scope": "patient",
                    },
                    {
                        "name": "holter_landing",
                        "root": (
                            r"C:\Users\Victo\Documents\GitHub\datalake"
                            r"\landing\holter_data"
                        ),
                        "recursive": True,
                        "scope": "patient",
                    },
                    {
                        "name": "eco_landing",
                        "root": (
                            r"C:\Users\Victo\Documents\GitHub\datalake"
                            r"\landing\eco_data"
                        ),
                        "recursive": True,
                        "scope": "patient",
                    },
                    {
                        "name": "redcap_silver",
                        "root": (
                            r"C:\Users\Victo\Documents\GitHub\datalake"
                            r"\silver\redcap_data\redcap_data.parquet"
                        ),
                        "recursive": False,
                        "scope": "global",
                    },
                ],
            }

            with self.config_path.open("w", encoding="utf-8") as file:
                json.dump(default_config, file, ensure_ascii=False, indent=4)

            return default_config

        with self.config_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def reload_config(self) -> None:
        self.config = self.load_or_create_config()

        configured_output = self.config.get("output_root", "output")
        output_path = Path(configured_output)

        if not output_path.is_absolute():
            output_path = self.app_root / output_path

        self.output_root = output_path
        self.output_root.mkdir(parents=True, exist_ok=True)

    def get_sources(self) -> list[SourceConfig]:
        sources: list[SourceConfig] = []

        for item in self.config.get("sources", []):
            name = str(item["name"]).strip()
            root = Path(item["root"])
            recursive = bool(item.get("recursive", True))
            scope = str(item.get("scope", "patient")).strip().lower()

            if not name:
                continue

            if scope not in {"patient", "global"}:
                raise RuntimeError(
                    f"Scope inválido na fonte {name}: {scope}. "
                    "Use 'patient' ou 'global'."
                )

            sources.append(
                SourceConfig(
                    name=name,
                    root=root,
                    recursive=recursive,
                    scope=scope,
                )
            )

        return sources

    def get_participants_summary_path(self) -> Path | None:
        value = self.config.get("participants_summary_csv")

        if not value:
            return None

        return Path(value)

    @staticmethod
    def normalize_value(value: object) -> str:
        if value is None:
            return ""

        text = str(value).strip()

        if text.endswith(".0"):
            text = text[:-2]

        return text

    @staticmethod
    def normalize_lookup_key(value: str) -> str:
        value = str(value).strip()

        if value.lower().startswith("id"):
            value = value[2:]

        if value.endswith(".0"):
            value = value[:-2]

        return value.upper()

    def load_participant_index(self) -> dict:
        csv_path = self.get_participants_summary_path()

        patient_ids: list[str] = []
        alias_to_patient_id: dict[str, str] = {}
        patient_aliases: dict[str, list[str]] = {}

        if not csv_path or not csv_path.exists():
            return {
                "patient_ids": patient_ids,
                "alias_to_patient_id": alias_to_patient_id,
                "patient_aliases": patient_aliases,
            }

        with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                patient_id = self.normalize_value(row.get("patient_id"))
                segundo_id = self.normalize_value(row.get("segundo_id"))

                if not patient_id:
                    continue

                if patient_id not in patient_ids:
                    patient_ids.append(patient_id)

                patient_aliases.setdefault(patient_id, [])

                aliases = [
                    patient_id,
                    patient_id.upper(),
                ]

                if segundo_id:
                    aliases.extend(
                        [
                            segundo_id,
                            f"Id{segundo_id}",
                            f"id{segundo_id}",
                        ]
                    )

                for alias in aliases:
                    lookup_key = self.normalize_lookup_key(alias)

                    if not lookup_key:
                        continue

                    alias_to_patient_id[lookup_key] = patient_id

                    if alias not in patient_aliases[patient_id]:
                        patient_aliases[patient_id].append(alias)

        return {
            "patient_ids": patient_ids,
            "alias_to_patient_id": alias_to_patient_id,
            "patient_aliases": patient_aliases,
        }

    def extract_candidates_from_text(self, text: str) -> list[str]:
        candidates: list[str] = []

        for match in PATIENT_ID_REGEX.findall(text):
            value = match.strip()

            if value and value not in candidates:
                candidates.append(value)

        return candidates

    def resolve_candidate_to_patient_id(
        self,
        candidate: str,
        alias_to_patient_id: dict[str, str],
    ) -> str | None:
        lookup_key = self.normalize_lookup_key(candidate)

        if lookup_key in alias_to_patient_id:
            return alias_to_patient_id[lookup_key]

        candidate_clean = candidate.strip()

        has_patient_id_shape = bool(
            re.match(
                r"^[A-Z]{2,5}-\d{2,4}-\d{3,5}$",
                candidate_clean,
                re.IGNORECASE,
            )
        )

        if has_patient_id_shape:
            return candidate_clean.upper()

        return None

    def get_global_source_paths(self, source: SourceConfig) -> list[Path]:
        if source.scope != "global":
            return []

        if not source.root.exists():
            return []

        if source.root.is_file():
            return [source.root]

        if source.root.is_dir():
            iterator = source.root.rglob("*") if source.recursive else source.root.glob("*")

            return [
                path
                for path in iterator
                if path.is_file()
            ]

        return []

    @staticmethod
    def prune_nested_paths(paths: list[Path]) -> list[Path]:
        sorted_paths = sorted(
            paths,
            key=lambda item: len(item.parts),
        )

        pruned: list[Path] = []

        for path in sorted_paths:
            resolved_path = path.resolve()

            is_child_of_existing = False

            for existing in pruned:
                resolved_existing = existing.resolve()

                try:
                    resolved_path.relative_to(resolved_existing)
                    is_child_of_existing = True
                    break
                except ValueError:
                    pass

            if not is_child_of_existing:
                pruned.append(path)

        return pruned

    def scan_source_paths(
        self,
        source: SourceConfig,
        alias_to_patient_id: dict[str, str],
    ) -> dict[str, list[Path]]:
        result: dict[str, list[Path]] = {}

        if source.scope == "global":
            return result

        if not source.root.exists():
            return result

        iterator = source.root.rglob("*") if source.recursive else source.root.glob("*")

        for path in iterator:
            search_text = str(path.relative_to(source.root))
            candidates = self.extract_candidates_from_text(search_text)

            for candidate in candidates:
                patient_id = self.resolve_candidate_to_patient_id(
                    candidate=candidate,
                    alias_to_patient_id=alias_to_patient_id,
                )

                if not patient_id:
                    continue

                result.setdefault(patient_id, [])

                if path not in result[patient_id]:
                    result[patient_id].append(path)

        for patient_id, paths in result.items():
            result[patient_id] = self.prune_nested_paths(paths)

        return result

    def build_inventory(self) -> dict:
        self.reload_config()

        sources = self.get_sources()
        participant_index = self.load_participant_index()

        known_patient_ids = participant_index["patient_ids"]
        alias_to_patient_id = participant_index["alias_to_patient_id"]
        patient_aliases = participant_index["patient_aliases"]

        source_maps: dict[str, dict[str, list[Path]]] = {}
        global_source_maps: dict[str, list[Path]] = {}
        discovered_ids: list[str] = []

        for source in sources:
            if source.scope == "global":
                global_source_maps[source.name] = self.get_global_source_paths(source)
                source_maps[source.name] = {}
                continue

            source_map = self.scan_source_paths(
                source=source,
                alias_to_patient_id=alias_to_patient_id,
            )

            source_maps[source.name] = source_map

            for patient_id in source_map:
                if patient_id not in discovered_ids:
                    discovered_ids.append(patient_id)

        all_patient_ids: list[str] = []

        for patient_id in known_patient_ids + discovered_ids:
            if patient_id not in all_patient_ids:
                all_patient_ids.append(patient_id)

        rows = []

        for patient_id in sorted(all_patient_ids):
            row = {
                "patient_id": patient_id,
                "aliases": patient_aliases.get(patient_id, []),
                "sources": {},
                "total_found": 0,
                "has_any_data": False,
            }

            for source in sources:
                if source.scope == "global":
                    paths = global_source_maps.get(source.name, [])
                    count = len(paths)

                    row["sources"][source.name] = {
                        "count": count,
                        "status": "GLOBAL OK" if count > 0 else "GLOBAL MISSING",
                        "paths": [str(path) for path in paths],
                        "scope": "global",
                    }

                    continue

                paths = source_maps.get(source.name, {}).get(patient_id, [])
                count = len(paths)

                row["sources"][source.name] = {
                    "count": count,
                    "status": "OK" if count > 0 else "MISSING",
                    "paths": [str(path) for path in paths],
                    "scope": "patient",
                }

                row["total_found"] += count

            row["has_any_data"] = row["total_found"] > 0
            rows.append(row)

        return {
            "sources": [source.name for source in sources],
            "rows": rows,
            "config_path": str(self.config_path),
            "output_root": str(self.output_root),
            "participants_summary_csv": str(self.get_participants_summary_path()),
            "known_patient_count": len(known_patient_ids),
            "discovered_patient_count": len(discovered_ids),
        }

    @staticmethod
    def add_path_to_zip(
        zip_file: zipfile.ZipFile,
        source_path: Path,
        arc_root: Path,
    ) -> int:
        files_added = 0

        if source_path.is_file():
            zip_file.write(
                source_path,
                arcname=str(arc_root / source_path.name),
            )
            return 1

        if source_path.is_dir():
            for item in source_path.rglob("*"):
                if item.is_file():
                    relative_path = item.relative_to(source_path)

                    zip_file.write(
                        item,
                        arcname=str(arc_root / source_path.name / relative_path),
                    )

                    files_added += 1

        return files_added

    def add_global_sources_to_zip(
        self,
        zip_file: zipfile.ZipFile,
        inventory: dict,
    ) -> tuple[int, dict]:
        included_files = 0
        global_manifest = {}

        if not inventory["rows"]:
            return included_files, global_manifest

        first_row = inventory["rows"][0]

        for source_name, source_info in first_row["sources"].items():
            if source_info.get("scope") != "global":
                continue

            paths = [
                Path(path)
                for path in source_info.get("paths", [])
            ]

            global_manifest[source_name] = {
                "count": len(paths),
                "paths": [str(path) for path in paths],
                "scope": "global",
            }

            for path in paths:
                if not path.exists():
                    continue

                added = self.add_path_to_zip(
                    zip_file=zip_file,
                    source_path=path,
                    arc_root=Path("_global") / source_name,
                )

                included_files += added

        return included_files, global_manifest

    def make_zip_for_patients(
        self,
        selected_patient_ids: list[str],
        inventory: dict | None = None,
    ) -> dict:
        if not selected_patient_ids:
            raise RuntimeError("Selecione pelo menos um paciente.")

        if inventory is None:
            inventory = self.build_inventory()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = self.output_root / f"samsung_batch_{timestamp}.zip"

        rows_by_patient = {
            row["patient_id"]: row
            for row in inventory["rows"]
        }

        included_files = 0
        included_patients = []

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            global_files_count, global_manifest = self.add_global_sources_to_zip(
                zip_file=zip_file,
                inventory=inventory,
            )

            included_files += global_files_count

            manifest = {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "selected_patient_ids": selected_patient_ids,
                "sources": inventory["sources"],
                "global_sources": global_manifest,
                "patients": [],
            }

            for patient_id in selected_patient_ids:
                row = rows_by_patient.get(patient_id)

                if not row:
                    continue

                patient_has_file = False

                patient_manifest = {
                    "patient_id": patient_id,
                    "aliases": row.get("aliases", []),
                    "sources": {},
                }

                for source_name, source_info in row["sources"].items():
                    if source_info.get("scope") == "global":
                        continue

                    paths = [
                        Path(path)
                        for path in source_info.get("paths", [])
                    ]

                    patient_manifest["sources"][source_name] = {
                        "count": len(paths),
                        "paths": [str(path) for path in paths],
                        "scope": "patient",
                    }

                    for path in paths:
                        if not path.exists():
                            continue

                        added = self.add_path_to_zip(
                            zip_file=zip_file,
                            source_path=path,
                            arc_root=Path(patient_id) / source_name,
                        )

                        if added > 0:
                            included_files += added
                            patient_has_file = True

                if patient_has_file:
                    included_patients.append(patient_id)

                manifest["patients"].append(patient_manifest)

            zip_file.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=4),
            )

        if included_files == 0:
            zip_path.unlink(missing_ok=True)
            raise RuntimeError(
                "Nenhum arquivo encontrado para os pacientes selecionados."
            )

        return {
            "zip_path": zip_path,
            "included_files": included_files,
            "included_patients": included_patients,
            "included_patient_count": len(included_patients),
        }