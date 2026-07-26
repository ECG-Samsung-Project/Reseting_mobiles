import re


class WatchIdParser:
    id_regex = re.compile(r"([A-Z]{3}-\d{2}-\d{4})", re.IGNORECASE)

    @classmethod
    def normalize(cls, value: str) -> str:
        return value.strip().upper()

    @classmethod
    def extract_ids(cls, text: str) -> list[str]:
        ids: list[str] = []

        for match in cls.id_regex.findall(text):
            watch_id = cls.normalize(match)

            if watch_id not in ids:
                ids.append(watch_id)

        return ids