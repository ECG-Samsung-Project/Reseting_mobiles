"""Modelos compartilhados pelo backend."""

from backend.models.application import (
    ApplicationCatalog,
    ApplicationDefinition,
    DeviceTarget,
)
from backend.models.device import DeviceInfo, DeviceKind
from backend.models.operation_result import OperationResult, OperationStatus
from backend.models.setup_input import SetupInput, safe_path_component
from backend.models.setup_session import SetupSession

__all__ = [
    "ApplicationCatalog",
    "ApplicationDefinition",
    "DeviceInfo",
    "DeviceKind",
    "DeviceTarget",
    "OperationResult",
    "OperationStatus",
    "SetupInput",
    "SetupSession",
    "safe_path_component",
]
