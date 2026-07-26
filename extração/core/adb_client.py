import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class AdbCommandResult:
    stdout: str
    stderr: str
    returncode: int


class AdbClient:
    def __init__(self, adb_path: str = "adb") -> None:
        self.adb_path = adb_path
        self.target_device_id: str | None = None

    def run(
        self,
        args: list[str],
        check: bool = True,
        input_text: str | None = None,
    ) -> AdbCommandResult:
        commands_without_device = {
            "version",
            "devices",
            "pair",
            "connect",
            "disconnect",
            "kill-server",
            "start-server",
        }

        if (
            self.target_device_id
            and args
            and args[0] not in commands_without_device
        ):
            command = [self.adb_path, "-s", self.target_device_id, *args]
        else:
            command = [self.adb_path, *args]

        try:
            result = subprocess.run(
                command,
                input=input_text,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError:
            raise RuntimeError(
                "ADB não encontrado. Instale o Android Platform Tools "
                "ou coloque o adb no PATH do Windows."
            )

        command_result = AdbCommandResult(
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip(),
            returncode=result.returncode,
        )

        if check and command_result.returncode != 0:
            raise RuntimeError(
                "Erro ao executar comando ADB.\n\n"
                f"Comando: {' '.join(command)}\n"
                f"Erro:\n{command_result.stderr or command_result.stdout}"
            )

        return command_result

    def shell(self, args: list[str], check: bool = True) -> str:
        return self.run(["shell", *args], check=check).stdout

    def list_files(self, android_path: str, check: bool = True) -> list[str]:
        result = self.run(
            ["shell", "find", android_path, "-type", "f"],
            check=False,
        )

        if check and result.returncode != 0:
            raise RuntimeError(
                f"Não consegui listar os arquivos em {android_path}.\n"
                f"Erro:\n{result.stderr or result.stdout}"
            )

        if result.returncode != 0:
            return []

        return [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]

    def list_dirs(self, android_path: str, check: bool = False) -> list[str]:
        result = self.run(
            ["shell", "find", android_path, "-type", "d"],
            check=False,
        )

        if check and result.returncode != 0:
            raise RuntimeError(
                f"Não consegui listar as pastas em {android_path}.\n"
                f"Erro:\n{result.stderr or result.stdout}"
            )

        if result.returncode != 0:
            return []

        return [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]

    def get_path_size_kb(self, android_path: str) -> int | None:
        result = self.run(
            ["shell", "du", "-sk", android_path],
            check=False,
        )

        if result.returncode != 0 or not result.stdout:
            return None

        first_part = result.stdout.split()[0]

        if not first_part.isdigit():
            return None

        return int(first_part)

    def get_property(self, prop_name: str) -> str | None:
        result = self.run(
            ["shell", "getprop", prop_name],
            check=False,
        )

        if result.returncode != 0:
            return None

        return result.stdout or None