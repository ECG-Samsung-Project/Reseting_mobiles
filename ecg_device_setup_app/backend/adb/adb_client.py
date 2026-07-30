"""Cliente ADB único para todo o backend."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from backend.adb.adb_command import AdbCommandResult
from backend.exceptions import (
    AdbCancelledError,
    AdbCommandError,
    AdbNotFoundError,
    AdbTimeoutError,
)


LOGGER = logging.getLogger(__name__)
PopenFactory = Callable[..., subprocess.Popen[str]]


class AdbClient:
    """Executa o ADB sem shell, com timeout, seleção explícita e cancelamento."""

    def __init__(
        self,
        adb_path: str | Path | None = None,
        *,
        default_timeout_seconds: float = 60,
        popen_factory: PopenFactory | None = None,
    ) -> None:
        if default_timeout_seconds <= 0:
            raise ValueError("O timeout padrão deve ser maior que zero.")
        self._configured_path = str(adb_path) if adb_path is not None else None
        self.default_timeout_seconds = float(default_timeout_seconds)
        self._popen_factory = popen_factory or subprocess.Popen
        self._resolved_path: str | None = None

    @property
    def executable(self) -> str:
        if self._resolved_path is None:
            self._resolved_path = self._locate_executable()
        return self._resolved_path

    def _locate_executable(self) -> str:
        configured = self._configured_path
        if configured:
            expanded = os.path.expandvars(os.path.expanduser(configured))
            is_explicit_path = (
                Path(expanded).is_absolute()
                or os.sep in expanded
                or (os.altsep is not None and os.altsep in expanded)
            )
            if is_explicit_path:
                candidate = Path(expanded)
                if candidate.is_file():
                    return str(candidate.resolve())
                raise AdbNotFoundError(
                    f"ADB não encontrado no caminho configurado: {candidate}"
                )
            discovered = shutil.which(expanded)
        else:
            discovered = shutil.which("adb")

        if discovered:
            return discovered
        raise AdbNotFoundError(
            "ADB não encontrado. Instale o Android Platform Tools ou configure "
            "o caminho do adb.exe."
        )

    def run(
        self,
        arguments: Sequence[str | Path],
        *,
        device_id: str | None = None,
        timeout_seconds: float | None = None,
        stdin_text: str | None = None,
        sensitive_values: Sequence[str] = (),
        cancellation_event: threading.Event | None = None,
        check: bool = True,
    ) -> AdbCommandResult:
        """Executa um comando.

        Os argumentos são sempre uma sequência, nunca uma string de shell.
        Dados sensíveis devem ser enviados por ``stdin_text`` quando possível.
        """

        if isinstance(arguments, (str, bytes)) or not arguments:
            raise ValueError("arguments deve ser uma sequência não vazia.")
        normalized_arguments = [str(argument) for argument in arguments]
        if any("\x00" in argument for argument in normalized_arguments):
            raise ValueError("Argumentos ADB não podem conter byte nulo.")
        if device_id is not None and not device_id.strip():
            raise ValueError("device_id não pode ser vazio.")

        timeout = (
            self.default_timeout_seconds
            if timeout_seconds is None
            else float(timeout_seconds)
        )
        if timeout <= 0:
            raise ValueError("timeout_seconds deve ser maior que zero.")

        command = [self.executable]
        if device_id is not None:
            command.extend(["-s", device_id])
        command.extend(normalized_arguments)
        safe_command = self._redact_command(command, sensitive_values)

        LOGGER.debug("Executando ADB: %s", safe_command)
        started_at = time.monotonic()
        try:
            process = self._popen_factory(
                command,
                stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                creationflags=self._creation_flags(),
            )
        except FileNotFoundError as exc:
            self._resolved_path = None
            raise AdbNotFoundError(
                "O executável ADB deixou de estar disponível."
            ) from exc
        except OSError as exc:
            raise AdbCommandError("Não foi possível iniciar o processo ADB.") from exc

        try:
            stdout, stderr = self._communicate(
                process=process,
                stdin_text=stdin_text,
                timeout_seconds=timeout,
                cancellation_event=cancellation_event,
            )
        except (AdbTimeoutError, AdbCancelledError):
            self._stop_process(process)
            raise

        duration = time.monotonic() - started_at
        result = AdbCommandResult(
            command=tuple(safe_command),
            stdout=(stdout or "").strip(),
            stderr=(stderr or "").strip(),
            return_code=process.returncode if process.returncode is not None else -1,
            duration_seconds=duration,
        )
        if check and not result.succeeded:
            detail = result.stderr or result.stdout or "sem detalhes"
            raise AdbCommandError(
                f"O comando ADB falhou com código {result.return_code}: {detail}"
            )
        return result

    def version(self) -> AdbCommandResult:
        return self.run(["version"], check=True)

    def get_property(
        self,
        property_name: str,
        *,
        device_id: str,
        timeout_seconds: float = 15,
    ) -> str:
        if not property_name or any(char.isspace() for char in property_name):
            raise ValueError("Nome de propriedade Android inválido.")
        return self.run(
            ["shell", "getprop", property_name],
            device_id=device_id,
            timeout_seconds=timeout_seconds,
        ).stdout

    @staticmethod
    def _redact_command(
        command: Sequence[str], sensitive_values: Sequence[str]
    ) -> list[str]:
        secrets = {value for value in sensitive_values if value}
        return ["<redacted>" if argument in secrets else argument for argument in command]

    @staticmethod
    def _creation_flags() -> int:
        if os.name == "nt":
            return int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return 0

    @staticmethod
    def _communicate(
        *,
        process: subprocess.Popen[str],
        stdin_text: str | None,
        timeout_seconds: float,
        cancellation_event: threading.Event | None,
    ) -> tuple[str, str]:
        if cancellation_event is None:
            try:
                return process.communicate(input=stdin_text, timeout=timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                raise AdbTimeoutError(
                    f"O comando ADB excedeu {timeout_seconds:g} segundos."
                ) from exc

        deadline = time.monotonic() + timeout_seconds
        pending_input = stdin_text
        while True:
            if cancellation_event.is_set():
                raise AdbCancelledError("O comando ADB foi cancelado.")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AdbTimeoutError(
                    f"O comando ADB excedeu {timeout_seconds:g} segundos."
                )
            try:
                return process.communicate(
                    input=pending_input,
                    timeout=min(0.2, remaining),
                )
            except subprocess.TimeoutExpired:
                pending_input = None

    @staticmethod
    def _stop_process(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
