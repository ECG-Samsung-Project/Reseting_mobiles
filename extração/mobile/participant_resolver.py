from pathlib import Path

from core.android_fs import AndroidFileSystem

from .participant_id import ParticipantIdParser
from .participant_lookup import ParticipantLookup


class MobileParticipantResolver:
    def __init__(
        self,
        android_fs: AndroidFileSystem,
        raw_ring_path: str,
        participant_lookup: ParticipantLookup,
    ) -> None:
        self.android_fs = android_fs
        self.raw_ring_path = raw_ring_path
        self.participant_lookup = participant_lookup

    def get_raw_ring_file_paths(self) -> list[str]:
        try:
            return self.android_fs.list_files(
                self.raw_ring_path,
                check=True,
            )
        except RuntimeError as error:
            raise RuntimeError(
                f"Não consegui listar os arquivos em {self.raw_ring_path}.\n"
                "Confirme se a pasta RAW_DATA_RING existe dentro de Documents.\n"
                f"Erro:\n{error}"
            )

    def get_raw_participant_ids_from_phone(self) -> list[str]:
        files = self.get_raw_ring_file_paths()
        text = "\n".join(files)

        raw_ids = ParticipantIdParser.extract_valid_ids(text)

        if not raw_ids:
            raise RuntimeError(
                "Não encontrei nenhum ID válido dentro da pasta RAW_DATA_RING.\n"
                "Exemplo esperado:\n"
                "RingSleepSpO2_Id954816620_DevDAE3_NoDev_..."
            )

        return raw_ids

    def resolve_from_phone(self) -> dict:
        raw_ids = self.get_raw_participant_ids_from_phone()
        selected_raw_id = raw_ids[0]

        resolution = self.participant_lookup.resolve(selected_raw_id)

        return {
            "raw_ids": raw_ids,
            "selected_raw_id": selected_raw_id,
            "lookup_key": resolution["lookup_key"],
            "participant_id": resolution["participant_id"],
            "lookup_source": resolution["source"],
            "matched_in_csv": resolution["matched"],
            "has_multiple_valid_ids": len(raw_ids) > 1,
            "multiple_valid_ids_count": len(raw_ids),
            "multiple_valid_ids_warning": (
                "Mais de um ID válido encontrado na RAW_DATA_RING. "
                "A extração foi feita usando o primeiro ID encontrado."
                if len(raw_ids) > 1
                else None
            ),
        }

    def get_participant_id_from_phone(self) -> str:
        resolution = self.resolve_from_phone()
        return resolution["participant_id"]

    def get_raw_ring_metadata(self) -> dict:
        try:
            files = self.get_raw_ring_file_paths()
        except RuntimeError:
            files = []

        text = "\n".join(files)

        valid_ids = ParticipantIdParser.extract_valid_ids(text)
        ignored_ids = ParticipantIdParser.extract_ignored_ids(text)
        all_ids_found = ParticipantIdParser.extract_all_ids(text)

        file_names = [Path(file).name for file in files]

        return {
            "raw_ring_path": self.raw_ring_path,
            "raw_ring_file_count": len(files),

            "ids_found_raw": all_ids_found,
            "ids_valid": valid_ids,
            "ignored_ids": ignored_ids,
            "ignored_rule": "IDs vazios ou com 5 zeros seguidos são ignorados.",

            "selected_raw_id": valid_ids[0] if valid_ids else None,
            "has_multiple_valid_ids": len(valid_ids) > 1,
            "multiple_valid_ids_count": len(valid_ids),
            "multiple_valid_ids_warning": (
                "Mais de um ID válido encontrado na RAW_DATA_RING. "
                "A extração foi feita usando o primeiro ID encontrado."
                if len(valid_ids) > 1
                else None
            ),

            "sample_files": file_names[:10],
        }