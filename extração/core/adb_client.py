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

    def run(self, args: list[str], check: bool = True) -> AdbCommandResult:
        try:
            result = subprocess.run(
                [self.adb_path, *args],
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
            command = " ".join([self.adb_path, *args])
            raise RuntimeError(
                f"Erro ao executar comando ADB.\n\n"
                f"Comando: {command}\n"
                f"Erro:\n{command_result.stderr or command_result.stdout}"
            )

        return command_result

    def shell(self, args: list[str], check: bool = True) -> str:
        return self.run(["shell", *args], check=check).stdout

    def list_files(self, phone_path: str, check: bool = True) -> list[str]:
        output = self.shell(["find", phone_path, "-type", "f"], check=check)

        return [
            line.strip()
            for line in output.splitlines()
            if line.strip()
        ]

    def list_dirs(self, phone_path: str, check: bool = False) -> list[str]:
        output = self.shell(["find", phone_path, "-type", "d"], check=check)

        return [
            line.strip()
            for line in output.splitlines()
            if line.strip()
        ]

    def get_path_size_kb(self, phone_path: str) -> int | None:
        result = self.run(["shell", "du", "-sk", phone_path], check=False)

        if result.returncode != 0 or not result.stdout:
            return None

        first_part = result.stdout.split()[0]

        if not first_part.isdigit():
            return None

        return int(first_part)

    def get_property(self, prop_name: str) -> str | None:
        result = self.run(["shell", "getprop", prop_name], check=False)

        if result.returncode != 0:
            return None

        return result.stdout or None