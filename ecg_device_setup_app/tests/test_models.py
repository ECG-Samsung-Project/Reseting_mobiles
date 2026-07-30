from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.models.setup_input import SetupInput, safe_path_component


def test_password_is_masked_and_excluded_from_serialization() -> None:
    setup_input = SetupInput(
        participant_id="EDI-21-2196",
        kit_id="KIT-03",
        google_email="ecg_p21@uea.edu.br",
        google_password="segredo-super-secreto",
    )

    assert "segredo-super-secreto" not in repr(setup_input)
    assert "segredo-super-secreto" not in setup_input.model_dump_json()
    assert "google_password" not in setup_input.model_dump()
    assert setup_input.persisted_identity() == {
        "participant_id": "EDI-21-2196",
        "kit_id": "KIT-03",
        "google_email": "ecg_p21@uea.edu.br",
    }


def test_participant_is_converted_to_safe_folder_component() -> None:
    setup_input = SetupInput(
        participant_id="  EDI 21/2196  ",
        kit_id="KIT:03",
        google_email="ecg_p21@uea.edu.br",
        google_password="senha",
    )

    assert setup_input.participant_folder_name == "EDI-21-2196"
    assert setup_input.kit_folder_name == "KIT-03"


@pytest.mark.parametrize("value", ["", "   ", ".", "..", "///", "CON", "LPT1.txt"])
def test_empty_or_unsafe_identifier_is_rejected(value: str) -> None:
    with pytest.raises((ValueError, ValidationError)):
        safe_path_component(value)
