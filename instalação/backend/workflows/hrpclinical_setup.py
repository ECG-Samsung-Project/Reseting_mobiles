import time
from backend.services.ui_automation_service import open_app, tap

def setup():
    open_app("com.hhw.hrpclinical")
    tap(500, 1400) ## Tap on "Select"
    time.sleep(1)
    tap(150, 1250) ## Tap on Documents
    time.sleep(1)
    tap(500, 2140) ## Tap on "Select"
    time.sleep(1)
    tap(900, 2100) ## Tap on "Select"
