import tkinter as tk
from tkinter import ttk

from watch.frontend import create_watch_frame
from mobile.frontend import create_mobile_frame


def run_app() -> None:
    root = tk.Tk()
    root.title("Extração")
    root.geometry("720x620")
    root.resizable(False, False)

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

    watch_frame = create_watch_frame(notebook)
    mobile_frame = create_mobile_frame(notebook)

    notebook.add(watch_frame, text="Watch")
    notebook.add(mobile_frame, text="Mobile")

    root.mainloop()


if __name__ == "__main__":
    run_app()