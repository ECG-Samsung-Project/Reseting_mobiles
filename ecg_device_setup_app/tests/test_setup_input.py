from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.models.setup_input import SetupInput


def test_password_is_not_persisted_or_exposed() -> None:
    setup_input = SetupInput(
        participant_id="ABC-12-2345",
        kit_id="12",
        google_email="conta@gmail.com",
        google_password="segredo-forte",
    )

    assert "segredo-forte" not in repr(setup_input)
    assert "google_password" not in setup_input.model_dump()
    assert setup_input.persisted_identity() == {
        "participant_id": "ABC-12-2345",
        "kit_id": "12",
        "google_email": "conta@gmail.com",
    }


def test_empty_password_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SetupInput(
            participant_id="ABC-12-2345",
            kit_id="12",
            google_email="conta@gmail.com",
            google_password="",
        )
