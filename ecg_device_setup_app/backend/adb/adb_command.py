"""Representação imutável de uma execução do ADB."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdbCommandResult:
    command: tuple[str, ...]
    stdout: str
    stderr: str
    return_code: int
    duration_seconds: float

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0
