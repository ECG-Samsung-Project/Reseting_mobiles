# mobile/participant_id.py

import re


class ParticipantIdParser:
    id_regex = re.compile(r"(Id[A-Za-z0-9-]+)", re.IGNORECASE)

    @classmethod
    def normalize(cls, value: str) -> str:
        value = value.strip()

        if value.lower().startswith("id"):
            return "Id" + value[2:]

        return value

    @classmethod
    def remove_id_prefix(cls, value: str) -> str:
        value = cls.normalize(value)

        if value.lower().startswith("id"):
            return value[2:]

        return value

    @classmethod
    def is_valid(cls, participant_id: str) -> bool:
        normalized = cls.normalize(participant_id)
        value_without_prefix = cls.remove_id_prefix(normalized)

        if not value_without_prefix:
            return False

        if "00000" in value_without_prefix:
            return False

        return True

    @classmethod
    def is_numeric_id(cls, participant_id: str) -> bool:
        value_without_prefix = cls.remove_id_prefix(participant_id)
        return value_without_prefix.isdigit()

    @classmethod
    def extract_valid_ids(cls, text: str) -> list[str]:
        ids: list[str] = []

        for match in cls.id_regex.findall(text):
            participant_id = cls.normalize(match)

            if not cls.is_valid(participant_id):
                continue

            if participant_id not in ids:
                ids.append(participant_id)

        return ids

    @classmethod
    def extract_ignored_ids(cls, text: str) -> list[str]:
        ids: list[str] = []

        for match in cls.id_regex.findall(text):
            participant_id = cls.normalize(match)

            if cls.is_valid(participant_id):
                continue

            if participant_id not in ids:
                ids.append(participant_id)

        return ids

    @classmethod
    def extract_all_ids(cls, text: str) -> list[str]:
        return [
            cls.normalize(match)
            for match in cls.id_regex.findall(text)
        ]