from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .backend import ServerSyncBackend
from .config import CONNECTION_PROFILES
from .models import (
    ComparisonEntry,
    ComparisonReport,
    ComparisonStatus,
    UploadBatchResult,
    UploadProgress,
    UploadStatus,
)


STATUS_TITLES = {
    ComparisonStatus.NEW: "Novos",
    ComparisonStatus.ALREADY_SENT: "Já enviados",
    ComparisonStatus.CONFLICT: "Conflitos",
    ComparisonStatus.REMOTE_ONLY: "Somente no servidor",
}

PHASE_LABELS = {
    "preparing": "Preparando",
    "hashing_local": "Calculando SHA-256 local",
    "uploading": "Enviando",
    "validating_size": "Validando tamanho",
    "hashing_remote": "Validando SHA-256 remoto",
    "finalizing": "Finalizando",
    "completed": "Concluído",
    "failed": "Falhou",
}


def format_size(size_bytes: int) -> str:
    size = float(size_bytes)
    units = ("B", "KB", "MB", "GB", "TB")

    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"

            return f"{size:.2f} {unit}"

        size /= 1024

    return f"{size_bytes} B"


def create_server_sync_frame(parent: tk.Widget) -> tk.Frame:
    backend = ServerSyncBackend()
    frame = tk.Frame(parent)

    state: dict[str, object] = {
        "busy": False,
        "report": None,
    }
    selected_keys: set[str] = set()
    new_item_by_key: dict[str, str] = {}
    new_key_by_item: dict[str, str] = {}

    title_label = tk.Label(
        frame,
        text="Enviar arquivos ao servidor",
        font=("Arial", 16, "bold"),
    )
    title_label.pack(pady=(14, 4))

    description_label = tk.Label(
        frame,
        text=(
            "Compara de uma vez todas as fontes configuradas em landing/raw, "
            "incluindo Mobile, Watch, ECG e demais arquivos clínicos. "
            "Nenhum conflito é sobrescrito e nenhum arquivo é apagado."
        ),
        font=("Arial", 10),
        wraplength=900,
    )
    description_label.pack(pady=(0, 8))

    controls_frame = tk.Frame(frame)
    controls_frame.pack(fill="x", padx=16, pady=6)

    profile_label_to_key = {
        label: key for key, label in CONNECTION_PROFILES.items()
    }
    connection_profile_var = tk.StringVar(
        value=CONNECTION_PROFILES["external"]
    )

    profile_label = tk.Label(
        controls_frame,
        text="Acesso:",
        font=("Arial", 10, "bold"),
    )
    profile_label.pack(side="left", padx=(4, 2))

    profile_combobox = ttk.Combobox(
        controls_frame,
        textvariable=connection_profile_var,
        values=tuple(CONNECTION_PROFILES.values()),
        state="readonly",
        width=23,
    )
    profile_combobox.pack(side="left", padx=(0, 12))

    verify_button = tk.Button(
        controls_frame,
        text="Verificar servidor",
        font=("Arial", 11, "bold"),
        width=22,
    )
    verify_button.pack(side="left", padx=4)

    select_all_button = tk.Button(
        controls_frame,
        text="Selecionar todos",
        font=("Arial", 10),
        width=18,
        state="disabled",
    )
    select_all_button.pack(side="left", padx=4)

    deselect_all_button = tk.Button(
        controls_frame,
        text="Desmarcar todos",
        font=("Arial", 10),
        width=18,
        state="disabled",
    )
    deselect_all_button.pack(side="left", padx=4)

    upload_button = tk.Button(
        controls_frame,
        text="Enviar selecionados",
        font=("Arial", 11, "bold"),
        width=22,
        state="disabled",
    )
    upload_button.pack(side="right", padx=4)

    connection_var = tk.StringVar(
        value=(
            "Destino selecionado: Externo. "
            "A configuração será carregada ao verificar."
        )
    )
    connection_label = tk.Label(
        frame,
        textvariable=connection_var,
        font=("Consolas", 9),
        anchor="w",
        justify="left",
        wraplength=1050,
    )
    connection_label.pack(fill="x", padx=20, pady=(2, 6))

    summary_frame = tk.LabelFrame(
        frame,
        text="Resumo da comparação",
        padx=8,
        pady=6,
    )
    summary_frame.pack(fill="x", padx=16, pady=4)

    summary_vars = {
        status: tk.StringVar(value=f"{title}: 0 arquivos — 0 B")
        for status, title in STATUS_TITLES.items()
    }

    for column, status in enumerate(STATUS_TITLES):
        label = tk.Label(
            summary_frame,
            textvariable=summary_vars[status],
            font=("Arial", 9),
            anchor="w",
        )
        label.grid(
            row=0,
            column=column,
            padx=10,
            pady=2,
            sticky="w",
        )
        summary_frame.grid_columnconfigure(column, weight=1)

    selection_var = tk.StringVar(
        value="Selecionados para envio: 0 arquivos — 0 B"
    )
    selection_label = tk.Label(
        summary_frame,
        textvariable=selection_var,
        font=("Arial", 10, "bold"),
        anchor="w",
    )
    selection_label.grid(
        row=1,
        column=0,
        columnspan=4,
        padx=10,
        pady=(5, 0),
        sticky="w",
    )

    partial_var = tk.StringVar(value="")
    partial_label = tk.Label(
        frame,
        textvariable=partial_var,
        font=("Arial", 9),
        fg="#8a5200",
        anchor="w",
        justify="left",
        wraplength=1050,
    )
    partial_label.pack(fill="x", padx=20, pady=(2, 4))

    tables_notebook = ttk.Notebook(frame)
    tables_notebook.pack(
        fill="both",
        expand=True,
        padx=16,
        pady=4,
    )

    trees: dict[ComparisonStatus, ttk.Treeview] = {}
    tab_frames: dict[ComparisonStatus, tk.Frame] = {}

    columns = (
        "selected",
        "folder",
        "relative_path",
        "local_size",
        "remote_size",
    )

    for status, title in STATUS_TITLES.items():
        tab = tk.Frame(tables_notebook)
        tab_frames[status] = tab
        tables_notebook.add(tab, text=title)

        tree = ttk.Treeview(
            tab,
            columns=columns,
            show="headings",
            selectmode="extended",
            height=11,
        )
        trees[status] = tree

        tree.heading(
            "selected",
            text="Enviar" if status == ComparisonStatus.NEW else "",
        )
        tree.heading("folder", text="Pasta")
        tree.heading("relative_path", text="Caminho relativo / arquivo")
        tree.heading("local_size", text="Tamanho local")
        tree.heading("remote_size", text="Tamanho servidor")

        tree.column(
            "selected",
            width=65 if status == ComparisonStatus.NEW else 20,
            minwidth=20,
            anchor="center",
            stretch=False,
        )
        tree.column(
            "folder",
            width=145,
            minwidth=120,
            anchor="w",
            stretch=False,
        )
        tree.column(
            "relative_path",
            width=520,
            minwidth=250,
            anchor="w",
        )
        tree.column(
            "local_size",
            width=120,
            minwidth=100,
            anchor="e",
            stretch=False,
        )
        tree.column(
            "remote_size",
            width=120,
            minwidth=100,
            anchor="e",
            stretch=False,
        )

        vertical_scrollbar = ttk.Scrollbar(
            tab,
            orient="vertical",
            command=tree.yview,
        )
        horizontal_scrollbar = ttk.Scrollbar(
            tab,
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
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)

    progress_frame = tk.Frame(frame)
    progress_frame.pack(fill="x", padx=16, pady=(5, 2))

    overall_progress = ttk.Progressbar(
        progress_frame,
        mode="determinate",
        maximum=100,
    )
    overall_progress.pack(fill="x", pady=2)

    current_progress = ttk.Progressbar(
        progress_frame,
        mode="determinate",
        maximum=100,
    )
    current_progress.pack(fill="x", pady=2)

    status_var = tk.StringVar(value="Aguardando...")
    status_label = tk.Label(
        frame,
        textvariable=status_var,
        font=("Arial", 9),
        anchor="w",
    )
    status_label.pack(fill="x", padx=20, pady=(2, 4))

    result_text = tk.Text(
        frame,
        height=4,
        font=("Consolas", 9),
        wrap="word",
        state="disabled",
    )
    result_text.pack(fill="x", padx=16, pady=(0, 10))

    def set_result_text(text: str) -> None:
        result_text.config(state="normal")
        result_text.delete("1.0", tk.END)
        result_text.insert(tk.END, text)
        result_text.config(state="disabled")

    def report_or_none() -> ComparisonReport | None:
        report = state["report"]
        return report if isinstance(report, ComparisonReport) else None

    def update_action_states() -> None:
        busy = bool(state["busy"])
        report = report_or_none()
        has_new = bool(report and report.new_entries)

        verify_button.config(
            state="disabled" if busy else "normal"
        )
        profile_combobox.config(
            state="disabled" if busy else "readonly"
        )
        selection_state = (
            "normal" if has_new and not busy else "disabled"
        )
        select_all_button.config(state=selection_state)
        deselect_all_button.config(state=selection_state)
        upload_button.config(
            state=(
                "normal"
                if selected_keys and report is not None and not busy
                else "disabled"
            )
        )

    def set_busy(is_busy: bool, indeterminate: bool = False) -> None:
        state["busy"] = is_busy

        if is_busy and indeterminate:
            overall_progress.configure(mode="indeterminate")
            overall_progress.start(12)
            current_progress.configure(mode="indeterminate")
            current_progress.start(12)
        else:
            overall_progress.stop()
            current_progress.stop()
            overall_progress.configure(mode="determinate")
            current_progress.configure(mode="determinate")

            if not is_busy:
                overall_progress["value"] = 0
                current_progress["value"] = 0

        update_action_states()

    def set_status_from_worker(text: str) -> None:
        frame.after(0, lambda: status_var.set(text))

    def ask_for_server_password(
        host: str,
        username: str,
    ) -> str | None:
        response: dict[str, str | None] = {"password": None}
        dialog_finished = threading.Event()

        def show_dialog() -> None:
            try:
                response["password"] = simpledialog.askstring(
                    "Senha SSH",
                    "Informe a senha para acessar o servidor.\n\n"
                    f"Servidor: {host}\n"
                    f"Usuário: {username}\n\n"
                    "A senha será mantida somente na memória e não "
                    "será gravada no .env.",
                    show="*",
                    parent=frame,
                )
            finally:
                dialog_finished.set()

        frame.after(0, show_dialog)
        dialog_finished.wait()

        return response["password"]

    def run_background(
        task,
        on_success,
        error_title: str,
        indeterminate: bool,
        on_error=None,
    ) -> None:
        set_busy(True, indeterminate=indeterminate)

        def worker() -> None:
            try:
                result = task()
            except Exception as error:
                error_message = str(error)

                def finish_error() -> None:
                    set_busy(False)

                    if on_error:
                        on_error()

                    status_var.set("Erro.")
                    messagebox.showerror(
                        error_title,
                        error_message,
                        parent=frame,
                    )

                frame.after(0, finish_error)
                return

            def finish_success() -> None:
                set_busy(False)
                on_success(result)

            frame.after(0, finish_success)

        threading.Thread(target=worker, daemon=True).start()

    def get_entry_values(
        entry: ComparisonEntry,
        selected: bool,
    ) -> tuple[str, str, str, str, str]:
        record = entry.local or entry.remote

        if record is None:
            raise RuntimeError("Entrada de comparação vazia.")

        selected_text = (
            "☑" if selected else "☐"
        ) if entry.status == ComparisonStatus.NEW else ""

        local_size = (
            format_size(entry.local.size_bytes)
            if entry.local is not None
            else "—"
        )
        remote_size = (
            format_size(entry.remote.size_bytes)
            if entry.remote is not None
            else "—"
        )

        return (
            selected_text,
            record.folder,
            record.relative_path.as_posix(),
            local_size,
            remote_size,
        )

    def update_selection_summary() -> None:
        report = report_or_none()

        if report is None:
            selected_size = 0
        else:
            selected_size = sum(
                entry.local.size_bytes
                for entry in report.new_entries
                if entry.key in selected_keys and entry.local is not None
            )

        selection_var.set(
            "Selecionados para envio: "
            f"{len(selected_keys)} arquivos — {format_size(selected_size)}"
        )
        update_action_states()

    def refresh_new_checkmarks() -> None:
        tree = trees[ComparisonStatus.NEW]

        for key, item_id in new_item_by_key.items():
            values = list(tree.item(item_id, "values"))

            if values:
                values[0] = "☑" if key in selected_keys else "☐"
                tree.item(item_id, values=values)

        update_selection_summary()

    def toggle_new_item(item_id: str) -> None:
        key = new_key_by_item.get(item_id)

        if key is None:
            return

        if key in selected_keys:
            selected_keys.remove(key)
        else:
            selected_keys.add(key)

        refresh_new_checkmarks()

    def handle_new_tree_click(event: tk.Event) -> None:
        tree = trees[ComparisonStatus.NEW]

        if tree.identify_region(event.x, event.y) != "cell":
            return

        if tree.identify_column(event.x) != "#1":
            return

        item_id = tree.identify_row(event.y)

        if item_id:
            toggle_new_item(item_id)

    def handle_new_tree_space(_event: tk.Event) -> str:
        tree = trees[ComparisonStatus.NEW]

        for item_id in tree.selection():
            toggle_new_item(item_id)

        return "break"

    trees[ComparisonStatus.NEW].bind(
        "<Button-1>",
        handle_new_tree_click,
        add="+",
    )
    trees[ComparisonStatus.NEW].bind(
        "<space>",
        handle_new_tree_space,
        add="+",
    )

    def render_report(report: ComparisonReport) -> None:
        selected_keys.clear()
        selected_keys.update(entry.key for entry in report.new_entries)
        new_item_by_key.clear()
        new_key_by_item.clear()

        for status, tree in trees.items():
            tree.delete(*tree.get_children())
            entries = report.entries_with_status(status)

            for index, entry in enumerate(entries):
                item_id = f"{status.value}_{index}"
                is_selected = entry.key in selected_keys
                tree.insert(
                    "",
                    "end",
                    iid=item_id,
                    values=get_entry_values(entry, is_selected),
                )

                if status == ComparisonStatus.NEW:
                    new_item_by_key[entry.key] = item_id
                    new_key_by_item[item_id] = entry.key

            title = STATUS_TITLES[status]
            tables_notebook.tab(
                tab_frames[status],
                text=f"{title} ({len(entries)})",
            )
            summary_vars[status].set(
                f"{title}: {len(entries)} arquivos — "
                f"{format_size(report.total_size(status))}"
            )

        if report.remote_partial_files:
            partial_var.set(
                "Aviso: foram encontrados "
                f"{len(report.remote_partial_files)} arquivos .part no "
                "servidor. Eles não entram na comparação e não serão apagados."
            )
        else:
            partial_var.set("")

        connection_summary = backend.get_active_connection_summary()

        if connection_summary:
            connection_var.set(f"Conexão: {connection_summary}")

        update_selection_summary()

    def reset_comparison_view() -> None:
        state["report"] = None
        backend.invalidate_comparison()
        selected_keys.clear()
        new_item_by_key.clear()
        new_key_by_item.clear()

        for status, tree in trees.items():
            tree.delete(*tree.get_children())
            title = STATUS_TITLES[status]
            tables_notebook.tab(tab_frames[status], text=title)
            summary_vars[status].set(f"{title}: 0 arquivos — 0 B")

        partial_var.set("")
        set_result_text("")
        update_selection_summary()

    def handle_profile_change(_event: tk.Event | None = None) -> None:
        reset_comparison_view()
        selected_label = connection_profile_var.get()
        connection_var.set(
            f"Destino selecionado: {selected_label}. "
            "Clique em Verificar servidor."
        )
        status_var.set(
            "Destino alterado. Verifique o servidor antes de enviar."
        )

    def handle_verify() -> None:
        reset_comparison_view()
        selected_label = connection_profile_var.get()
        connection_profile = profile_label_to_key[selected_label]

        def task() -> ComparisonReport:
            return backend.compare_all(
                status_callback=set_status_from_worker,
                password_prompt=ask_for_server_password,
                connection_profile=connection_profile,
            )

        def on_success(report: ComparisonReport) -> None:
            state["report"] = report
            render_report(report)
            status_var.set("Comparação concluída.")

        run_background(
            task=task,
            on_success=on_success,
            error_title="Erro ao verificar servidor",
            indeterminate=True,
        )

    def select_all() -> None:
        report = report_or_none()

        if report is None:
            return

        selected_keys.clear()
        selected_keys.update(entry.key for entry in report.new_entries)
        refresh_new_checkmarks()

    def deselect_all() -> None:
        selected_keys.clear()
        refresh_new_checkmarks()

    def update_upload_progress(progress: UploadProgress) -> None:
        def update() -> None:
            file_fraction = 0.0

            if progress.total_bytes > 0:
                file_fraction = min(
                    progress.transferred_bytes / progress.total_bytes,
                    1.0,
                )

            current_progress["value"] = file_fraction * 100

            if progress.file_count > 0:
                overall_fraction = (
                    (progress.file_index - 1) + file_fraction
                ) / progress.file_count
                overall_progress["value"] = overall_fraction * 100

            phase = PHASE_LABELS.get(progress.phase, progress.phase)
            status_var.set(
                f"{phase} {progress.file_index}/{progress.file_count}: "
                f"{progress.key}"
            )

        frame.after(0, update)

    def format_upload_result(result: UploadBatchResult) -> str:
        lines = [
            (
                "Concluídos: "
                f"{result.count(UploadStatus.SUCCESS)} — "
                f"{format_size(result.successful_bytes)}"
            ),
            (
                "Já existentes no momento do envio: "
                f"{result.count(UploadStatus.SKIPPED_ALREADY_SENT)}"
            ),
            (
                "Conflitos bloqueados: "
                f"{result.count(UploadStatus.BLOCKED_CONFLICT)}"
            ),
            f"Falhas: {result.count(UploadStatus.FAILED)}",
        ]

        noteworthy = [
            item
            for item in result.results
            if (
                item.status != UploadStatus.SUCCESS
                or not item.hash_verified
            )
        ]

        if noteworthy:
            lines.append("")
            lines.append("Detalhes:")

            for item in noteworthy[:12]:
                lines.append(f"- {item.key}: {item.message}")

                if item.temporary_remote_path is not None:
                    lines.append(
                        "  Temporário mantido: "
                        f"{item.temporary_remote_path}"
                    )

            if len(noteworthy) > 12:
                lines.append(
                    f"- ... e mais {len(noteworthy) - 12} resultados."
                )

        return "\n".join(lines)

    def handle_upload() -> None:
        report = report_or_none()

        if report is None:
            messagebox.showerror(
                "Comparação necessária",
                "Verifique o servidor novamente antes de enviar.",
                parent=frame,
            )
            return

        if not selected_keys:
            messagebox.showerror(
                "Nenhum arquivo selecionado",
                "Selecione ao menos um arquivo novo.",
                parent=frame,
            )
            return

        selected_size = sum(
            entry.local.size_bytes
            for entry in report.new_entries
            if entry.key in selected_keys and entry.local is not None
        )

        confirmed = messagebox.askyesno(
            "Confirmar upload",
            "Deseja enviar os arquivos selecionados?\n\n"
            f"Destino: {backend.get_active_connection_summary()}\n"
            f"Quantidade: {len(selected_keys)}\n"
            f"Tamanho total: {format_size(selected_size)}\n\n"
            "Conflitos não serão sobrescritos e nenhum arquivo "
            "será apagado.",
            parent=frame,
        )

        if not confirmed:
            return

        keys_to_upload = tuple(sorted(selected_keys))

        def task() -> UploadBatchResult:
            return backend.upload_selected(
                report=report,
                selected_keys=keys_to_upload,
                progress_callback=update_upload_progress,
                status_callback=set_status_from_worker,
            )

        def on_success(result: UploadBatchResult) -> None:
            state["report"] = None
            selected_keys.clear()
            update_selection_summary()

            result_message = format_upload_result(result)
            set_result_text(result_message)
            status_var.set(
                "Uploads processados. Verifique o servidor novamente "
                "para atualizar a comparação."
            )
            partial_var.set(
                "A comparação anterior foi invalidada após o upload. "
                "Clique em “Verificar servidor” antes de outro envio."
            )

            if result.count(UploadStatus.FAILED):
                messagebox.showwarning(
                    "Upload concluído com falhas",
                    result_message,
                    parent=frame,
                )
            else:
                messagebox.showinfo(
                    "Upload processado",
                    result_message,
                    parent=frame,
                )

        def on_error() -> None:
            state["report"] = None
            selected_keys.clear()
            update_selection_summary()
            partial_var.set(
                "A comparação foi invalidada. Clique em "
                "“Verificar servidor” antes de tentar novamente."
            )

        run_background(
            task=task,
            on_success=on_success,
            error_title="Erro durante o upload",
            indeterminate=False,
            on_error=on_error,
        )

    verify_button.config(command=handle_verify)
    select_all_button.config(command=select_all)
    deselect_all_button.config(command=deselect_all)
    upload_button.config(command=handle_upload)
    profile_combobox.bind("<<ComboboxSelected>>", handle_profile_change)

    return frame
