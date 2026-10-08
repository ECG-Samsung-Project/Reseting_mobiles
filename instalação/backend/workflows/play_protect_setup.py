import msvcrt
import time

from backend.services.ui_automation_service import get_screen_xml, tap, input_text, open_settings
import xml.etree.ElementTree as ET

DEBUG = True

def debug_step(message: str):
    if not DEBUG:
        return

    print(f"{message}")
    print("Enter = continuar | Esc = cancelar")

    while True:
        key = msvcrt.getch()

        if key == b"\r":  # Enter
            return

        if key == b"\x1b":  # Esc
            raise KeyboardInterrupt("Processo cancelado pelo usuário.")

def pause_play_protect():
    # 1 - Abrir Configurações
    debug_step("Abrindo Configurações...")
    open_settings()

    # 2 - Lupa
    debug_step("Clicando na lupa de pesquisa...")
    tap(982, 782)
    time.sleep(1)
    debug_step("Aguardando a interface de pesquisa abrir...")

    # 3 - Pesquisar "Play Protect"
    debug_step("Pesquisando 'Play Protect'...")
    input_text("Play Protect")

    time.sleep(1)

    # 4 - App Play Protect
    debug_step("Abrindo app Play Protect...")
    tap(150, 700)
    time.sleep(1)

    # 5 - Google Play Protect
    debug_step("Abrindo Google Play Protect...")
    tap(200, 900)
    time.sleep(1)

    # 6 - Engrenagem
    debug_step("Abrindo configurações do Play Protect...")
    tap(1000, 160)
    time.sleep(1)

    debug_step("Verificando se o Play Protect está ativado...")
    if is_play_protect_enabled():

        debug_step("Play Protect está ativado. Tentando pausar...")
        # 7 - Verificar apps
        tap(191, 596)
        time.sleep(1)

        # 8 - Pausar por 24h
        debug_step("Pausando Play Protect por 24h...")
        tap(280, 1400)

        time.sleep(1)   
        debug_step("Play Protect pausado.")

    else:
        debug_step("Já está pausado, não é necessário pausar novamente.")


def is_play_protect_enabled() -> bool:
    xml = get_screen_xml()
    root = ET.fromstring(xml)

    for node in root.iter("node"):
        if node.attrib.get("clickable") != "true":
            continue

        has_play_protect = False
        switch = None

        for child in node.iter("node"):
            text = child.attrib.get("text", "")

            if "Verificar apps com o Play Protect" in text:
                has_play_protect = True

            if child.attrib.get("class") == "android.widget.Switch":
                switch = child

        if has_play_protect and switch is not None:
            return switch.attrib.get("checked") == "true"

    raise RuntimeError(
        "Não foi possível identificar o estado do Play Protect."
    )