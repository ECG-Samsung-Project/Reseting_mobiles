import pytest

pytest.importorskip("PySide6")

from frontend.steps.confirmation_step import mask_email


def test_email_is_masked() -> None:
    assert mask_email("victormonte43@gmail.com") == "vi***********@gmail.com"
