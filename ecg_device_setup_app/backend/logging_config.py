"""Configuração de logs com mascaramento defensivo de segredos."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from pathlib import Path
from threading import RLock


_LABELED_SECRET = re.compile(
    r"(?i)\b(password|senha|pairing[_ -]?code|token|secret)"
    r"(\s*[=:]\s*)"
    r"(\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)


def redact_sensitive_text(text: str, secrets: Iterable[str] = ()) -> str:
    redacted = text
    for secret in sorted({value for value in secrets if value}, key=len, reverse=True):
        redacted = redacted.replace(secret, "<redacted>")
    return _LABELED_SECRET.sub(r"\1\2<redacted>", redacted)


class SensitiveDataFilter(logging.Filter):
    def __init__(self, secrets: Iterable[str] = ()) -> None:
        super().__init__()
        self._secrets = set(value for value in secrets if value)
        self._lock = RLock()

    def register_secret(self, secret: str) -> None:
        if secret:
            with self._lock:
                self._secrets.add(secret)

    def filter(self, record: logging.LogRecord) -> bool:
        with self._lock:
            secrets = tuple(self._secrets)
        record.msg = redact_sensitive_text(record.getMessage(), secrets)
        record.args = ()
        return True


def configure_session_logging(log_path: Path) -> SensitiveDataFilter:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
    )
    sensitive_filter = SensitiveDataFilter()
    handler.addFilter(sensitive_filter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
    return sensitive_filter
