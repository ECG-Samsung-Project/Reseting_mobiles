import re


class ParticipantIdParser:
    id_regex = re.compile(r"(Id\d+)", re.IGNORECASE)

    @classmethod
    def normalize(cls, value: str) -> str:
        value = value.strip()
        return "Id" + value[2:]

    @classmethod
    def is_valid(cls, participant_id: str) -> bool:
        normalized = cls.normalize(participant_id)
        digits = normalized[2:]

        if not digits:
            return False

        if "00000" in digits:
            return False

        return True

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