from backend.services.adb_service import run_command

def ensure_connected_devices() -> None:
    devices = get_connected_devices()
    
    if not devices:
        raise RuntimeError(
            "Nenhum celular conectado via ADB.\n\n"
            "Confira cabo USB, modo desenvolvedor, depuração USB e autorização."
        )

    if len(devices) > 1:
        raise RuntimeError(
            "Mais de um dispositivo conectado.\n\n"
            "Deixe conectado apenas o celular alvo."
        )
    
    return devices[0]

def get_connected_devices() -> list[str]:
    output = run_command(["adb", "devices"])

    devices = []

    for line in output.splitlines()[1:]:
        line = line.strip()

        if not line:
            continue

        if "\tdevice" in line:
            devices.append(line.split("\t")[0])

        elif "\tunauthorized" in line:
            raise RuntimeError(
                "Celular conectado, mas não autorizado.\n\n"
                "Aceite a depuração USB na tela do celular."
            )

        elif "\toffline" in line:
            raise RuntimeError(
                "Celular aparece como offline.\n\n"
                "Desconecte e conecte o cabo USB novamente."
            )

    return devices