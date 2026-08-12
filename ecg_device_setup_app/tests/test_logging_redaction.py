from backend.logging_config import redact_sensitive_text


def test_redacts_registered_and_labeled_secrets() -> None:
    text = "senha=abc123 token: xyz senha avulsa abc123"
    result = redact_sensitive_text(text, ["abc123"])

    assert "abc123" not in result
    assert "xyz" not in result
    assert result.count("<redacted>") >= 2
