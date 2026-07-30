from __future__ import annotations

import logging

from backend.logging_config import SensitiveDataFilter, redact_sensitive_text


def test_labeled_secrets_are_redacted() -> None:
    text = "senha=abc123 pairing_code: 999999 token='token-value'"

    redacted = redact_sensitive_text(text)

    assert "abc123" not in redacted
    assert "999999" not in redacted
    assert "token-value" not in redacted
    assert redacted.count("<redacted>") == 3


def test_registered_password_is_removed_from_formatted_log() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Conta preparada com %s",
        args=("senha-secreta",),
        exc_info=None,
    )
    sensitive_filter = SensitiveDataFilter(["senha-secreta"])

    assert sensitive_filter.filter(record)
    assert "senha-secreta" not in record.getMessage()
    assert "<redacted>" in record.getMessage()
