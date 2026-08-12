"""Execução de tarefas de backend fora da thread da interface."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(str)
    finished = Signal()


class CallableWorker(QRunnable):
    """Executa uma função sem argumentos no pool global de threads."""

    def __init__(self, function: Callable[[], Any]) -> None:
        super().__init__()
        self.function = function
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        try:
            result = self.function()
        except Exception as exc:  # convertido em mensagem amigável pelo controlador
            self.signals.error.emit(str(exc) or exc.__class__.__name__)
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()
