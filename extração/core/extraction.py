"""Verified transfers and atomic publication of extraction packages."""

import hashlib
import json
import os
import shlex
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def remote_digest(adb, path: str) -> tuple[int, str]:
    quoted = shlex.quote(path)
    result = adb.run(["shell", f"stat -c %s {quoted} && sha256sum {quoted}"])
    lines = result.stdout.splitlines()
    try:
        size, checksum = int(lines[0]), lines[1].split()[0]
        if len(checksum) != 64 or any(c not in "0123456789abcdefABCDEF" for c in checksum):
            raise ValueError("invalid hash")
        return size, checksum.lower()
    except (ValueError, IndexError) as error:
        raise RuntimeError(f"Não consegui verificar tamanho/SHA-256 de {path}.") from error


def copy_verified(adb, android_fs, source: str, destination: Path) -> list[dict]:
    files = android_fs.list_files(source, check=True)
    destination.mkdir(parents=True, exist_ok=True)
    report = []
    local_paths = set()
    for remote in files:
        relative = PurePosixPath(remote).relative_to(PurePosixPath(source))
        if ".." in relative.parts or any(":" in part or "\\" in part for part in relative.parts):
            raise RuntimeError(f"Caminho inválido no aparelho: {remote}")
        key = relative.as_posix().casefold()
        if key in local_paths:
            raise RuntimeError(f"Caminhos duplicados no Windows: {remote}")
        local_paths.add(key)
        local = destination.joinpath(*relative.parts)
        local.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(3):
            try:
                before = remote_digest(adb, remote)
                if not (local.is_file() and local.stat().st_size == before[0] and digest(local) == before[1]):
                    adb.run(["pull", remote, str(local)])
                after = remote_digest(adb, remote)
                if before != after or local.stat().st_size != after[0] or digest(local) != after[1]:
                    raise RuntimeError(f"Arquivo alterado ou cópia divergente: {remote}")
                report.append({"source": remote, "relative_path": relative.as_posix(), "size_bytes": after[0], "sha256": after[1]})
                break
            except (RuntimeError, OSError) as error:
                if attempt == 2:
                    raise RuntimeError(f"Falha após 3 tentativas: {remote}. Cópia preservada em {destination}. {error}") from error
    if set(android_fs.list_files(source, check=True)) != set(files):
        raise RuntimeError(f"Arquivos adicionados/removidos durante a extração: {source}. Repita com a coleta parada.")
    if report:
        evidence = destination / "_transfer_evidence"
        evidence.mkdir(exist_ok=True)
        name = hashlib.sha256(source.encode("utf-8")).hexdigest() + ".json"
        (evidence / name).write_text(json.dumps({"source_root": source, "files": report}, indent=2), encoding="utf-8")
    return report


def save_active_registration(staging: Path, registration: dict) -> None:
    # Bronze consumes every file named ecg_registration.json. Preserve originals
    # under a different name, so only the selected registration is active.
    originals = []
    for path in staging.rglob("*"):
        if not path.is_file() or path.suffix.lower() != ".json" or "_registration_history" in path.relative_to(staging).parts:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (ValueError, UnicodeError) as error:
            raise RuntimeError(f"JSON inválido no pacote copiado: {path}") from error
        if isinstance(data, dict) and str(data.get("project", "")).strip().upper() == "ECG" and "participant_id" in data and "kit_type" in data:
            originals.append(path)
    if not any(json.loads(path.read_text(encoding="utf-8-sig")) == registration["document"] for path in originals):
        raise RuntimeError("O cadastro selecionado não está na cópia verificada. Ele pode ter mudado durante a extração; repita a operação.")
    history = staging / "_registration_history"
    for index, original in enumerate(originals, 1):
        history.mkdir(exist_ok=True)
        target = history / f"{index:04d}.original.json"
        while target.exists():
            index += 1
            target = history / f"{index:04d}.original.json"
        original.rename(target)
        (history / f"{target.stem}.source.txt").write_text(original.relative_to(staging).as_posix(), encoding="utf-8")
    (staging / "ecg_registration.json").write_text(
        json.dumps(registration["document"], ensure_ascii=False, indent=2), encoding="utf-8",
    )


def create_verified_archive(staging: Path, archive: Path) -> Path:
    archive.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(path for path in staging.rglob("*") if path.is_file() and path != staging / "extraction_manifest.json")
    manifest = [{"path": path.relative_to(staging).as_posix(), "size_bytes": path.stat().st_size, "sha256": digest(path)} for path in files]
    manifest_path = staging / "extraction_manifest.json"
    manifest_path.write_text(json.dumps({"schema_version": 1, "files": manifest}, indent=2), encoding="utf-8")
    handle, temporary = tempfile.mkstemp(prefix=archive.name + ".", suffix=".part", dir=archive.parent)
    os.close(handle)
    temporary = Path(temporary)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zipped:
            for path in [*files, manifest_path]:
                zipped.write(path, path.relative_to(staging).as_posix())
        with zipfile.ZipFile(temporary) as zipped:
            if zipped.testzip() is not None:
                raise RuntimeError("Falha de integridade no ZIP.")
            for entry in manifest:
                with zipped.open(entry["path"]) as stream:
                    if hashlib.file_digest(stream, "sha256").hexdigest() != entry["sha256"]:
                        raise RuntimeError(f"SHA-256 divergente no ZIP: {entry['path']}")
        # Windows rename refuses to overwrite another extraction's destination.
        temporary.rename(archive)
        return archive
    finally:
        temporary.unlink(missing_ok=True)
