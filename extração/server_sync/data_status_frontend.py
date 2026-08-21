from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .backend import ServerSyncBackend
from .config import CONNECTION_PROFILES
from .data_status import STATUS_FOLDERS, build_participant_status
from .models import RemoteInventory


def create_server_data_status_frame(parent: tk.Widget) -> tk.Frame:
    backend = ServerSyncBackend()
    frame = tk.Frame(parent)

    tk.Label(
        frame,
        text="Status dos dados na raw do servidor",
        font=("Arial", 16, "bold"),
    ).pack(pady=(14, 4))

    tk.Label(
        frame,
        text=(
            "Indica se existe algum arquivo do participante em cada pasta "
            "raw do servidor."
        ),
        font=("Arial", 10),
    ).pack(pady=(0, 10))

    controls = tk.Frame(frame)
    controls.pack(fill="x", padx=16, pady=4)

    tk.Label(
        controls,
        text="Acesso:",
        font=("Arial", 10, "bold"),
    ).pack(side="left", padx=(4, 2))

    profile_label_to_key = {
        label: key for key, label in CONNECTION_PROFILES.items()
    }
    profile_var = tk.StringVar(value=CONNECTION_PROFILES["external"])
    profile_combobox = ttk.Combobox(
        controls,
        textvariable=profile_var,
        values=tuple(CONNECTION_PROFILES.values()),
        state="readonly",
        width=23,
    )
    profile_combobox.pack(side="left", padx=(0, 12))

    refresh_button = tk.Button(
        controls,
        text="Atualizar status",
        font=("Arial", 11, "bold"),
        width=20,
    )
    refresh_button.pack(side="left", padx=4)

    connection_var = tk.StringVar(
        value="Destino selecionado: Externo."
    )
    tk.Label(
        frame,
        textvariable=connection_var,
        font=("Consolas", 9),
        anchor="w",
        justify="left",
        wraplength=1050,
    ).pack(fill="x", padx=20, pady=(4, 2))

    status_var = tk.StringVar(value="Clique em Atualizar status.")
    tk.Label(
        frame,
        textvariable=status_var,
        font=("Arial", 9),
        anchor="w",
    ).pack(fill="x", padx=20, pady=(0, 6))

    table_frame = tk.Frame(frame)
    table_frame.pack(fill="both", expand=True, padx=16, pady=(2, 14))

    folder_columns = tuple(folder for _label, folder in STATUS_FOLDERS)
    columns = ("participant", *folder_columns)
    tree = ttk.Treeview(
        table_frame,
        columns=columns,
        show="headings",
        selectmode="browse",
    )
    tree.heading("participant", text="Participante")
    tree.column(
        "participant",
        width=170,
        minwidth=140,
        anchor="w",
        stretch=True,
    )

    for label, folder in STATUS_FOLDERS:
        tree.heading(folder, text=label)
        tree.column(
            folder,
            width=95,
            minwidth=75,
            anchor="center",
            stretch=True,
        )

    vertical_scrollbar = ttk.Scrollbar(
        table_frame,
        orient="vertical",
        command=tree.yview,
    )
    horizontal_scrollbar = ttk.Scrollbar(
        table_frame,
        orient="horizontal",
        command=tree.xview,
    )
    tree.configure(
        yscrollcommand=vertical_scrollbar.set,
        xscrollcommand=horizontal_scrollbar.set,
    )
    tree.grid(row=0, column=0, sticky="nsew")
    vertical_scrollbar.grid(row=0, column=1, sticky="ns")
    horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
    table_frame.grid_rowconfigure(0, weight=1)
    table_frame.grid_columnconfigure(0, weight=1)

    def set_busy(is_busy: bool) -> None:
        refresh_button.config(state="disabled" if is_busy else "normal")
        profile_combobox.config(
            state="disabled" if is_busy else "readonly"
        )

    def ask_for_server_password(
        host: str,
        username: str,
    ) -> str | None:
        response: dict[str, str | None] = {"password": None}
        finished = threading.Event()

        def show_dialog() -> None:
            try:
                response["password"] = simpledialog.askstring(
                    "Senha SSH",
                    f"Servidor: {host}\nUsuário: {username}",
                    show="*",
                    parent=frame,
                )
            finally:
                finished.set()

        frame.after(0, show_dialog)
        finished.wait()
        return response["password"]

    def render_inventory(inventory: RemoteInventory) -> None:
        tree.delete(*tree.get_children())
        rows = build_participant_status(inventory)

        for row in rows:
            tree.insert(
                "",
                "end",
                values=(
                    row.participant_id,
                    *(
                        "✅" if available else "❌"
                        for available in row.available_by_folder
                    ),
                ),
            )

        summary = backend.get_active_connection_summary()

        if summary:
            connection_var.set(f"Conexão: {summary}")

        status_var.set(f"{len(rows)} participantes encontrados.")

    def handle_refresh() -> None:
        selected_label = profile_var.get()
        selected_profile = profile_label_to_key[selected_label]
        set_busy(True)
        status_var.set("Consultando o servidor...")
        tree.delete(*tree.get_children())

        def worker() -> None:
            try:
                inventory = backend.inspect_remote(
                    status_callback=(
                        lambda text: frame.after(0, status_var.set, text)
                    ),
                    password_prompt=ask_for_server_password,
                    connection_profile=selected_profile,
                )
            except Exception as error:
                error_message = str(error)

                def finish_error() -> None:
                    set_busy(False)
                    status_var.set("Erro ao consultar o servidor.")
                    messagebox.showerror(
                        "Erro ao atualizar status",
                        error_message,
                        parent=frame,
                    )

                frame.after(0, finish_error)
                return

            def finish_success() -> None:
                set_busy(False)
                render_inventory(inventory)

            frame.after(0, finish_success)

        threading.Thread(target=worker, daemon=True).start()

    def handle_profile_change(_event: tk.Event | None = None) -> None:
        tree.delete(*tree.get_children())
        backend.invalidate_comparison()
        connection_var.set(f"Destino selecionado: {profile_var.get()}.")
        status_var.set("Clique em Atualizar status.")

    refresh_button.config(command=handle_refresh)
    profile_combobox.bind("<<ComboboxSelected>>", handle_profile_change)
    return frame
