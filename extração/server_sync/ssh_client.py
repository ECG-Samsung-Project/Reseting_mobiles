from __future__ import annotations

import shlex
import stat
from collections.abc import Callable, Iterator
from pathlib import Path, PurePosixPath
from typing import Any

from .config import ServerSyncConfig


TransferCallback = Callable[[int, int], None] | None


class RemoteHashUnavailable(RuntimeError):
    """Indica que o servidor não conseguiu calcular SHA-256."""


class SshSftpClient:
    def __init__(self, config: ServerSyncConfig) -> None:
        self.config = config
        self._ssh: Any = None
        self._sftp: Any = None

    def __enter__(self) -> "SshSftpClient":
        self.connect()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def connect(self) -> None:
        if self._ssh is not None:
            return

        try:
            import paramiko
        except ImportError as error:
            raise RuntimeError(
                "Paramiko não está instalado. "
                "Execute: pip install -r requirements.txt"
            ) from error

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        client.load_system_host_keys()

        known_hosts = self.config.known_hosts

        if known_hosts is None:
            default_known_hosts = Path.home() / ".ssh" / "known_hosts"

            if default_known_hosts.is_file():
                known_hosts = default_known_hosts

        if known_hosts is not None:
            client.load_host_keys(str(known_hosts))

        connect_arguments: dict[str, object] = {
            "hostname": self.config.host,
            "port": self.config.port,
            "username": self.config.username,
            "timeout": self.config.connect_timeout_seconds,
            "banner_timeout": self.config.connect_timeout_seconds,
            "auth_timeout": self.config.connect_timeout_seconds,
            "allow_agent": (
                False
                if self.config.authentication_method == "password"
                else self.config.allow_agent
            ),
            "look_for_keys": (
                False
                if self.config.authentication_method == "password"
                else self.config.look_for_keys
            ),
        }

        if (
            self.config.password is not None
            and self.config.authentication_method != "key"
        ):
            connect_arguments["password"] = self.config.password

        if self.config.private_key is not None:
            connect_arguments["key_filename"] = str(
                self.config.private_key
            )

        if self.config.private_key_passphrase is not None:
            connect_arguments["passphrase"] = (
                self.config.private_key_passphrase
            )

        try:
            client.connect(**connect_arguments)
            sftp = client.open_sftp()
        except Exception as error:
            client.close()
            raise RuntimeError(
                "Não foi possível conectar ao servidor SSH/SFTP "
                f"{self.config.host}:{self.config.port} como "
                f"{self.config.username}.\n{error}"
            ) from error

        self._ssh = client
        self._sftp = sftp

    def close(self) -> None:
        if self._sftp is not None:
            try:
                self._sftp.close()
            except Exception:
                pass
            finally:
                self._sftp = None

        if self._ssh is not None:
            try:
                self._ssh.close()
            except Exception:
                pass
            finally:
                self._ssh = None

    def iter_files(
        self,
        root: PurePosixPath,
    ) -> Iterator[tuple[PurePosixPath, int]]:
        sftp = self._require_sftp()

        root_attributes = sftp.stat(str(root))

        if not stat.S_ISDIR(root_attributes.st_mode):
            raise RuntimeError(
                f"O caminho remoto não é uma pasta: {root}"
            )

        pending = [root]

        while pending:
            current = pending.pop()

            try:
                attributes = sorted(
                    sftp.listdir_attr(str(current)),
                    key=lambda item: item.filename,
                )
            except Exception as error:
                raise RuntimeError(
                    f"Não foi possível listar a pasta remota:\n{current}\n"
                    f"{error}"
                ) from error

            child_directories: list[PurePosixPath] = []

            for item in attributes:
                name = item.filename

                if (
                    not name
                    or name in {".", ".."}
                    or "/" in name
                    or "\\" in name
                ):
                    raise RuntimeError(
                        "O servidor retornou um nome de arquivo inválido em "
                        f"{current}: {name!r}."
                    )

                child_path = current / name

                if stat.S_ISLNK(item.st_mode):
                    raise RuntimeError(
                        "Links simbólicos não são aceitos no inventário "
                        f"remoto:\n{child_path}"
                    )

                if stat.S_ISDIR(item.st_mode):
                    child_directories.append(child_path)
                    continue

                if stat.S_ISREG(item.st_mode):
                    yield child_path, int(item.st_size)

            pending.extend(reversed(child_directories))

    def directory_exists(
        self,
        remote_directory: PurePosixPath,
    ) -> bool:
        sftp = self._require_sftp()

        try:
            attributes = sftp.stat(str(remote_directory))
        except (FileNotFoundError, OSError) as error:
            if getattr(error, "errno", None) == 2:
                return False

            raise

        if not stat.S_ISDIR(attributes.st_mode):
            raise RuntimeError(
                "Era esperada uma pasta no servidor, mas existe um "
                f"arquivo em:\n{remote_directory}"
            )

        return True

    def stat_size(self, remote_path: PurePosixPath) -> int | None:
        sftp = self._require_sftp()

        try:
            attributes = sftp.stat(str(remote_path))
        except (FileNotFoundError, OSError) as error:
            if getattr(error, "errno", None) == 2:
                return None

            raise

        if stat.S_ISDIR(attributes.st_mode):
            raise RuntimeError(
                f"Era esperado um arquivo, mas há uma pasta em:\n{remote_path}"
            )

        return int(attributes.st_size)

    def ensure_directory(
        self,
        remote_directory: PurePosixPath,
        base_directory: PurePosixPath,
    ) -> None:
        sftp = self._require_sftp()

        try:
            relative = remote_directory.relative_to(base_directory)
        except ValueError as error:
            raise RuntimeError(
                "Tentativa de criar pasta fora do destino permitido:\n"
                f"{remote_directory}"
            ) from error

        base_attributes = sftp.stat(str(base_directory))

        if not stat.S_ISDIR(base_attributes.st_mode):
            raise RuntimeError(
                f"A pasta remota base não existe: {base_directory}"
            )

        current = base_directory

        for part in relative.parts:
            current = current / part

            try:
                attributes = sftp.stat(str(current))
            except (FileNotFoundError, OSError) as error:
                if getattr(error, "errno", None) != 2:
                    raise

                sftp.mkdir(str(current))
                continue

            if not stat.S_ISDIR(attributes.st_mode):
                raise RuntimeError(
                    "Não é possível criar a pasta remota porque existe "
                    f"um arquivo no caminho:\n{current}"
                )

    def upload_file(
        self,
        local_path: Path,
        remote_path: PurePosixPath,
        callback: TransferCallback = None,
    ) -> None:
        sftp = self._require_sftp()
        sftp.put(
            str(local_path),
            str(remote_path),
            callback=callback,
            confirm=True,
        )

    def remote_sha256(self, remote_path: PurePosixPath) -> str:
        ssh = self._require_ssh()
        command = f"sha256sum -- {shlex.quote(str(remote_path))}"

        try:
            _stdin, stdout, stderr = ssh.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            stdout_text = (
                stdout.read()
                .decode("utf-8", errors="replace")
                .strip()
            )
            stderr_text = (
                stderr.read()
                .decode("utf-8", errors="replace")
                .strip()
            )
        except Exception as error:
            raise RemoteHashUnavailable(
                f"SHA-256 remoto indisponível: {error}"
            ) from error

        if exit_status != 0:
            detail = stderr_text or stdout_text or (
                f"código de saída {exit_status}"
            )
            raise RemoteHashUnavailable(
                f"SHA-256 remoto indisponível: {detail}"
            )

        digest = stdout_text.split(maxsplit=1)[0].lower()

        if len(digest) != 64 or any(
            character not in "0123456789abcdef"
            for character in digest
        ):
            raise RemoteHashUnavailable(
                "O servidor retornou um SHA-256 em formato inválido."
            )

        return digest

    def rename_no_overwrite(
        self,
        source: PurePosixPath,
        destination: PurePosixPath,
    ) -> None:
        sftp = self._require_sftp()

        if self.stat_size(destination) is not None:
            raise FileExistsError(
                f"O destino remoto já existe: {destination}"
            )

        sftp.rename(str(source), str(destination))

    def _require_ssh(self) -> Any:
        if self._ssh is None:
            raise RuntimeError("A conexão SSH não está aberta.")

        return self._ssh

    def _require_sftp(self) -> Any:
        if self._sftp is None:
            raise RuntimeError("A conexão SFTP não está aberta.")

        return self._sftp
