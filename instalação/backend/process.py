import backend.processes.inclinic_process as inclinic
from collections.abc import Callable

def setup_device(process_type: str, progress_callback: Callable[[str], None] | None = None,) -> list[str] | None:

    if process_type == "InClinic":
        return inclinic.setup()
    else:
        return None

def reset_device(progress_callback: Callable[[str], None] | None = None,) -> None:

    return inclinic.reset()