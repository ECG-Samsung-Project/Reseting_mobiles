"""Resolve ECG registrations by content rather than Android filenames."""

import json
import re
import shlex
from datetime import datetime, timezone

from core.android_fs import AndroidFileSystem


class RegistrationError(RuntimeError):
    """A registration exists but cannot safely identify the current kit."""


class RegistrationResolver:
    DEFAULT_ROOTS = ("/sdcard/Documents", "/sdcard/Download", "/sdcard/Downloads")

    def __init__(self, android_fs: AndroidFileSystem) -> None:
        self.android_fs = android_fs

    def resolve(self, source_paths: list[str] | None = None) -> dict | None:
        files = set()
        try:
            roots = dict.fromkeys(source_paths if source_paths is not None else self.android_fs.existing_source_paths())
            for root in roots:
                files.update(self.android_fs.list_files(root.rstrip("/"), check=True))
        except RuntimeError as error:
            raise RegistrationError(f"Busca de cadastro incompleta; verifique a conexão e as permissões. {error}") from error

        candidates = []
        for path in sorted(files):
            if not path.lower().endswith(".json"):
                continue
            result = self.android_fs.adb.run(
                ["shell", f"cat -- {shlex.quote(path)}"], check=False,
            )
            if result.returncode != 0:
                raise RegistrationError(f"Não consegui ler o JSON de identificação: {path}")
            try:
                data = json.loads(result.stdout.lstrip("\ufeff"))
            except (ValueError, TypeError) as error:
                raise RegistrationError(f"JSON ilegível; não é seguro assumir um cadastro antigo: {path}. Corrija ou remova este arquivo da pasta de coleta.") from error
            if not isinstance(data, dict):
                continue
            if str(data.get("project", "")).strip().upper() != "ECG":
                continue
            if "participant_id" not in data or "kit_type" not in data:
                raise RegistrationError(f"Cadastro ECG incompleto: {path}")

            participant_id = str(data["participant_id"]).strip().upper()
            kit_type = str(data["kit_type"]).strip().upper()
            if not re.fullmatch(r"[A-Z]{3}-\d{2}-\d{4}", participant_id) or kit_type not in {"IC", "FL"}:
                raise RegistrationError(f"Cadastro ECG inválido (participant_id/kit_type): {path}")
            configured_at = data.get("configured_at")
            if data.get("schema_version") not in (1, 2):
                raise RegistrationError(f"Versão do cadastro ECG não suportada: {path}")
            try:
                configured_date = (
                    datetime.fromisoformat(configured_at.replace("Z", "+00:00"))
                    if configured_at else datetime.min
                )
                if configured_date.tzinfo is None:
                    configured_date = configured_date.replace(tzinfo=timezone.utc)
                configured_date = configured_date.astimezone(timezone.utc)
            except (ValueError, TypeError, AttributeError, OverflowError) as error:
                raise RegistrationError(f"configured_at inválido no cadastro ECG: {path}") from error
            candidates.append((configured_date, {
                "participant_id": participant_id,
                "kit_type": kit_type,
                "collection_context": "in_clinic" if kit_type == "IC" else "free_living",
                "configured_at": configured_at,
                "source_path": path,
                "document": data,
            }))

        if not candidates:
            return None
        newest = max(date for date, _ in candidates)
        current = [registration for date, registration in candidates if date == newest]
        if len({(item["participant_id"], item["kit_type"]) for item in current}) > 1:
            paths = ", ".join(item["source_path"] for item in current)
            raise RegistrationError(f"Cadastros ECG conflitantes na mesma data: {paths}. Corrija os cadastros antes de extrair.")
        return current[0]
