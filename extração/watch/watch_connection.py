from core.adb_client import AdbClient


class WatchConnectionManager:
    def __init__(self, adb: AdbClient) -> None:
        self.adb = adb

    @staticmethod
    def validate_ip(ip: str) -> str:
        ip = ip.strip()

        if not ip:
            raise RuntimeError("Informe o IP do relógio.")

        if ":" in ip:
            raise RuntimeError(
                "Informe apenas o IP, sem porta.\n\n"
                "Exemplo correto: 30.0.0.218\n"
                "Exemplo errado: 30.0.0.218:34347"
            )

        return ip

    @staticmethod
    def validate_port(port: str, field_name: str) -> str:
        port = port.strip()

        if not port:
            raise RuntimeError(f"Informe a {field_name}.")

        if not port.isdigit():
            raise RuntimeError(f"A {field_name} deve conter apenas números.")

        port_number = int(port)

        if port_number < 1 or port_number > 65535:
            raise RuntimeError(f"A {field_name} deve estar entre 1 e 65535.")

        return port

    @staticmethod
    def build_address(ip: str, port: str) -> str:
        return f"{ip}:{port}"

    @staticmethod
    def get_optional_address(ip: str, port: str) -> str | None:
        ip = ip.strip()
        port = port.strip()

        if not ip or not port:
            return None

        return f"{ip}:{port}"

    def get_pairing_address(self, ip: str, pairing_port: str) -> str:
        ip = self.validate_ip(ip)
        pairing_port = self.validate_port(
            pairing_port,
            "porta de pareamento",
        )

        return self.build_address(ip, pairing_port)

    def get_connect_address(self, ip: str, connect_port: str) -> str:
        ip = self.validate_ip(ip)
        connect_port = self.validate_port(
            connect_port,
            "porta de conexão",
        )

        return self.build_address(ip, connect_port)

    def check_adb_installed(self) -> None:
        self.adb.run(["version"])

    def get_connected_devices(self) -> list[str]:
        result = self.adb.run(["devices"])

        devices = []

        for line in result.stdout.splitlines()[1:]:
            line = line.strip()

            if not line:
                continue

            if "\tdevice" in line:
                device_id = line.split("\t")[0]
                devices.append(device_id)

            elif "\tunauthorized" in line:
                raise RuntimeError(
                    "Dispositivo conectado, mas não autorizado.\n\n"
                    "Olhe a tela do relógio e aceite a depuração USB/Wi-Fi."
                )

            elif "\toffline" in line:
                raise RuntimeError(
                    "Dispositivo aparece como offline.\n\n"
                    "Desconecte e conecte novamente, ou reinicie o ADB."
                )

        return devices

    def get_target_device_id(
        self,
        devices: list[str],
        connect_address: str,
    ) -> str:
        if connect_address in devices:
            return connect_address

        if self.adb.target_device_id and self.adb.target_device_id in devices:
            return self.adb.target_device_id

        if len(devices) == 1:
            return devices[0]

        raise RuntimeError(
            "Mais de um dispositivo conectado, e não consegui identificar o relógio alvo.\n\n"
            f"Dispositivos encontrados:\n{devices}\n\n"
            "Confira se o IP e a porta de conexão estão exatamente iguais ao que aparece no adb devices.\n"
            "Exemplo: 30.0.0.218:34347"
        )

    def pair_watch(
        self,
        ip: str,
        pairing_port: str,
        pairing_code: str,
    ) -> str:
        pairing_address = self.get_pairing_address(ip, pairing_port)
        pairing_code = pairing_code.strip()

        if not pairing_code:
            raise RuntimeError("Informe a senha/código de pareamento.")

        result = self.adb.run(
            ["pair", pairing_address],
            input_text=f"{pairing_code}\n",
        )

        return result.stdout

    def connect_watch(
        self,
        ip: str,
        connect_port: str,
    ) -> tuple[str, str]:
        connect_address = self.get_connect_address(ip, connect_port)

        result = self.adb.run(["connect", connect_address])

        self.adb.target_device_id = connect_address

        return result.stdout, self.adb.target_device_id

    def disconnect_all_devices(self) -> str:
        result = self.adb.run(["disconnect"])
        self.adb.target_device_id = None

        return result.stdout