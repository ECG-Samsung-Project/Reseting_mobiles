import tkinter as tk
from tkinter import ttk


def create_scrollable_frame(parent: tk.Widget) -> tuple[tk.Frame, tk.Frame]:
    outer_frame = tk.Frame(parent)

    canvas = tk.Canvas(
        outer_frame,
        highlightthickness=0,
    )

    vertical_scrollbar = ttk.Scrollbar(
        outer_frame,
        orient="vertical",
        command=canvas.yview,
    )

    horizontal_scrollbar = ttk.Scrollbar(
        outer_frame,
        orient="horizontal",
        command=canvas.xview,
    )

    content_frame = tk.Frame(canvas)

    content_window = canvas.create_window(
        (0, 0),
        window=content_frame,
        anchor="nw",
    )

    canvas.configure(
        yscrollcommand=vertical_scrollbar.set,
        xscrollcommand=horizontal_scrollbar.set,
    )

    canvas.grid(row=0, column=0, sticky="nsew")
    vertical_scrollbar.grid(row=0, column=1, sticky="ns")
    horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

    outer_frame.grid_rowconfigure(0, weight=1)
    outer_frame.grid_columnconfigure(0, weight=1)

    def update_scroll_region(event=None) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))

    def update_content_width(event) -> None:
        canvas.itemconfig(content_window, width=max(event.width, content_frame.winfo_reqwidth()))

    def on_mousewheel(event) -> None:
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    content_frame.bind("<Configure>", update_scroll_region)
    canvas.bind("<Configure>", update_content_width)

    canvas.bind_all("<MouseWheel>", on_mousewheel)

    return outer_frame, content_frame