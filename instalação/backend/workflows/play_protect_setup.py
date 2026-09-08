import time

from backend.services.ui_automation_service import get_screen_xml, tap, input_text, open_settings


def pause_play_protect():
    # 1 - Abrir Configurações
    open_settings()

    # 2 - Lupa
    tap(982, 782)
    time.sleep(0.5)

    # 3 - Pesquisar "Play Protect"
    input_text("Play Protect")

    time.sleep(1)

    # 4 - App Play Protect
    tap(150, 700)
    time.sleep(1)

    # 5 - Google Play Protect
    tap(200, 900)
    time.sleep(1)

    # 6 - Engrenagem
    tap(1000, 160)
    time.sleep(1)

    if is_play_protect_enabled():

        # 7 - Verificar apps
        tap(191, 596)
        time.sleep(1)

        # 8 - Pausar por 24h
        tap(280, 1400)

        time.sleep(1)   

    else:
        print("Já está pausado, não é necessário pausar novamente.")



def is_play_protect_enabled() -> bool:
    xml = get_screen_xml()

    for line in xml.split("<node"):
        if "Verificar apps" in line:
            return 'checked="true"' in line

    raise RuntimeError(
        "Não foi possível identificar o estado do Play Protect."
    )