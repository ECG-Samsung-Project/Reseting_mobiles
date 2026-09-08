import time
from backend.services.ui_automation_service import open_app, tap

def setup():
    open_app("com.sec.smartring2")
    tap(750, 1300)
    time.sleep(2)
