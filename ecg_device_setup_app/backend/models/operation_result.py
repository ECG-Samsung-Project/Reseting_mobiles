"""Resultado uniforme de operações do backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class OperationStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    WARNING = "WARNING"
    CANCELLED = "CANCELLED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


@dataclass(frozen=True, slots=True)
class OperationResult:
    status: OperationStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.status is OperationStatus.SUCCESS

    @classmethod
    def success(
        cls, message: str, details: dict[str, Any] | None = None
    ) -> OperationResult:
        return cls(OperationStatus.SUCCESS, message, details or {})

    @classmethod
    def failure(
        cls, message: str, details: dict[str, Any] | None = None
    ) -> OperationResult:
        return cls(OperationStatus.FAILURE, message, details or {})
