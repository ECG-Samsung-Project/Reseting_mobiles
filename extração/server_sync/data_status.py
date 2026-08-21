from __future__ import annotations

import re
from dataclasses import dataclass

from .models import RemoteInventory


STATUS_FOLDERS = (
    ("Bio", "bio_data"),
    ("ECG", "ecg_data"),
    ("Holter", "holter_data"),
    ("Looper", "looper_data"),
    ("Mobile FL", "mobile_fl_data"),
    ("Mobile IC", "mobile_ic_data"),
    ("Watch FL", "watch_fl_data"),
    ("Watch IC", "watch_ic_data"),
)

PARTICIPANT_ID_PATTERN = re.compile(
    r"(?<![A-Z0-9])([A-Z]{3}-\d{2}-\d{4})(?![A-Z0-9])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParticipantDataStatus:
    participant_id: str
    available_by_folder: tuple[bool, ...]


def build_participant_status(
    inventory: RemoteInventory,
) -> tuple[ParticipantDataStatus, ...]:
    paths_by_folder = {
        folder: tuple(
            record.relative_path.as_posix().upper()
            for record in inventory.files
            if record.folder == folder
        )
        for _label, folder in STATUS_FOLDERS
    }

    participant_ids = {
        match.group(1).upper()
        for paths in paths_by_folder.values()
        for path in paths
        for match in PARTICIPANT_ID_PATTERN.finditer(path)
    }

    rows: list[ParticipantDataStatus] = []

    for participant_id in sorted(participant_ids):
        short_id = participant_id.split("-", maxsplit=1)[0]
        short_id_pattern = re.compile(
            rf"(?<![A-Z0-9]){re.escape(short_id)}(?![A-Z0-9])"
        )
        availability = tuple(
            any(
                _path_matches_participant(
                    path,
                    participant_id,
                    short_id_pattern,
                )
                for path in paths_by_folder[folder]
            )
            for _label, folder in STATUS_FOLDERS
        )
        rows.append(
            ParticipantDataStatus(
                participant_id=participant_id,
                available_by_folder=availability,
            )
        )

    return tuple(rows)


def _path_matches_participant(
    path: str,
    participant_id: str,
    short_id_pattern: re.Pattern[str],
) -> bool:
    full_ids = {
        match.group(1).upper()
        for match in PARTICIPANT_ID_PATTERN.finditer(path)
    }

    if full_ids:
        return participant_id in full_ids

    return short_id_pattern.search(path) is not None
