"""Modelo serializável de sessão, sem campos de senha."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from backend.models.device import DeviceInfo


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SetupSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    participant_id: str
    kit_id: str
    google_email: str
    current_step: str = "CREATED"
    started_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    phone: dict[str, object] | None = None
    watch: dict[str, object] | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def register_phone(self, phone: DeviceInfo) -> None:
        self.phone = phone.to_dict()
        self.updated_at = utc_now()
