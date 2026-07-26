import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

try:
    from .backend import ClinicalFilesBackend
except ImportError:
    from clinical_files.backend import ClinicalFilesBackend


def create_clinical_files_frame(parent: tk.Widget) -> tk.Frame:
    backend = ClinicalFilesBackend()

    selected_paths: list[str] = []

    frame = tk.Frame(parent)

    title_label = tk.Label(
        frame,
        text="Importar arquivos clínicos",
        font=("Arial", 16, "bold"),
    )
    title_label.pack(pady=14)

    description_label = tk.Label(
        frame,
        text=(
            "Selecione arquivos ou uma pasta. Se o ID do paciente ficar vazio, "
            "o sistema tenta identificar pelo nome do arquivo/pasta usando o participants_summary.csv."
        ),
        font=("Arial", 10),
        wraplength=680,
        justify="center",
    )
    description_label.pack(pady=4)

    form_frame = tk.Frame(frame)
    form_frame.pack(pady=10)

    data_type_label = tk.Label(
        form_frame,
        text="Tipo:",
        font=("Arial", 10),
    )
    data_type_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")

    data_type_combo = ttk.Combobox(
        form_frame,
        values=[
            "ecg",
            "looper",
            "holter",
            "eco",
            "redcap",
        ],
        width=18,
        state="readonly",
    )
    data_type_combo.grid(row=0, column=1, padx=5, pady=5)
    data_type_combo.set("ecg")

    patient_id_label = tk.Label(
        form_frame,
        text="ID do paciente:",
        font=("Arial", 10),
    )
    patient_id_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")

    patient_id_entry = tk.Entry(
        form_frame,
        width=22,
        font=("Arial", 10),
    )
    patient_id_entry.grid(row=1, column=1, padx=5, pady=5)

    optional_label = tk.Label(
        form_frame,
        text="opcional",
        font=("Arial", 9),
    )
    optional_label.grid(row=1, column=2, padx=5, pady=5, sticky="w")

    output_label = tk.Label(
        frame,
        text=f"Destino: {backend.get_output_preview('ecg')}",
        font=("Arial", 9),
        wraplength=700,
        justify="center",
    )
    output_label.pack(pady=5)

    def update_output_preview(event=None) -> None:
        data_type = data_type_combo.get()
        output_label.config(
            text=f"Destino: {backend.get_output_preview(data_type)}"
        )

    data_type_combo.bind("<<ComboboxSelected>>", update_output_preview)

    paths_text = tk.Text(
        frame,
        height=8,
        width=84,
        font=("Consolas", 9),
        wrap="none",
        state="disabled",
    )
    paths_text.pack(pady=8)

    status_label = tk.Label(
        frame,
        text="Aguardando...",
        font=("Arial", 10),
    )
    status_label.pack(pady=5)

    progress_bar = ttk.Progressbar(
        frame,
        mode="indeterminate",
        length=320,
    )
    progress_bar.pack(pady=4)
    progress_bar.stop()

    button_frame = tk.Frame(frame)
    button_frame.pack(pady=10)

    select_files_button = tk.Button(
        button_frame,
        text="Selecionar arquivos",
        font=("Arial", 10),
        width=22,
    )
    select_files_button.grid(row=0, column=0, padx=6, pady=4)

    select_folder_button = tk.Button(
        button_frame,
        text="Selecionar pasta",
        font=("Arial", 10),
        width=22,
    )
    select_folder_button.grid(row=0, column=1, padx=6, pady=4)

    import_button = tk.Button(
        button_frame,
        text="Importar para landing",
        font=("Arial", 10),
        width=22,
    )
    import_button.grid(row=0, column=2, padx=6, pady=4)

    clear_button = tk.Button(
        button_frame,
        text="Limpar seleção",
        font=("Arial", 10),
        width=22,
    )
    clear_button.grid(row=1, column=1, padx=6, pady=8)

    def set_status(text: str) -> None:
        frame.after(
            0,
            lambda: status_label.config(text=text),
        )

    def set_busy(is_busy: bool) -> None:
        def update_state() -> None:
            state = "disabled" if is_busy else "normal"

            select_files_button.config(state=state)
            select_folder_button.config(state=state)
            import_button.config(state=state)
            clear_button.config(state=state)
            patient_id_entry.config(state=state)
            data_type_combo.config(state="disabled" if is_busy else "readonly")

            if is_busy:
                progress_bar.start(10)
            else:
                progress_bar.stop()

        frame.after(0, update_state)

    def update_paths_text() -> None:
        paths_text.config(state="normal")
        paths_text.delete("1.0", tk.END)

        if not selected_paths:
            paths_text.insert(tk.END, "Nenhum arquivo ou pasta selecionado.")
        else:
            for path in selected_paths:
                paths_text.insert(tk.END, f"{path}\n")

        paths_text.config(state="disabled")

    def handle_select_files() -> None:
        nonlocal selected_paths

        paths = filedialog.askopenfilenames(
            title="Selecione arquivos clínicos",
            filetypes=[
                (
                    "Arquivos suportados",
                    "*.zip *.csv *.json *.txt *.xml *.pdf *.dcm *.dat *.dbf *.ams *.int *.asc *.rep *.xcm",
                ),
                ("Todos os arquivos", "*.*"),
            ],
        )

        if not paths:
            return

        selected_paths = list(paths)
        update_paths_text()
        status_label.config(text=f"{len(selected_paths)} arquivo(s) selecionado(s).")

    def handle_select_folder() -> None:
        nonlocal selected_paths

        path = filedialog.askdirectory(
            title="Selecione uma pasta clínica",
        )

        if not path:
            return

        if path not in selected_paths:
            selected_paths.append(path)

        update_paths_text()
        status_label.config(text=f"{len(selected_paths)} item(ns) selecionado(s).")

    def handle_clear_selection() -> None:
        nonlocal selected_paths

        selected_paths = []
        update_paths_text()
        status_label.config(text="Seleção limpa.")

    def handle_import_paths() -> None:
        data_type = data_type_combo.get()
        patient_id = patient_id_entry.get()
        paths_to_import = selected_paths.copy()

        def task() -> dict:
            return backend.ingest_paths(
                data_type=data_type,
                patient_id=patient_id,
                input_paths=paths_to_import,
                status_callback=set_status,
            )

        def worker() -> None:
            set_busy(True)

            try:
                result = task()

                def show_success() -> None:
                    status_label.config(text="Importação concluída.")

                    success_lines = []

                    for item in result["results"]:
                        source_path = Path(item["source_path"])

                        success_lines.append(
                            f"- {item['patient_id']} | {source_path.name} | {item['package_folder']}"
                        )

                    error_lines = []

                    for item in result["errors"]:
                        source_path = Path(item["source_path"])

                        error_lines.append(
                            f"- {source_path.name}: {item['error']}"
                        )

                    message = (
                        "Importação finalizada.\n\n"
                        f"Tipo: {result['data_type']}\n"
                        f"Inputs recebidos: {result['total_inputs']}\n"
                        f"Sucessos: {result['success_count']}\n"
                        f"Erros: {result['error_count']}\n\n"
                    )

                    if success_lines:
                        message += "Salvos:\n"
                        message += "\n".join(success_lines[:10])
                        message += "\n\n"

                        if len(success_lines) > 10:
                            message += f"... e mais {len(success_lines) - 10} itens.\n\n"

                    if error_lines:
                        message += "Erros:\n"
                        message += "\n".join(error_lines[:10])

                        if len(error_lines) > 10:
                            message += f"\n... e mais {len(error_lines) - 10} erros."

                    messagebox.showinfo(
                        "Resultado da importação",
                        message,
                    )

                frame.after(0, show_success)

            except Exception as error:
                error_message = str(error)

                def show_error() -> None:
                    status_label.config(text="Erro na importação.")
                    messagebox.showerror("Erro", error_message)

                frame.after(0, show_error)

            finally:
                set_busy(False)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    select_files_button.config(command=handle_select_files)
    select_folder_button.config(command=handle_select_folder)
    import_button.config(command=handle_import_paths)
    clear_button.config(command=handle_clear_selection)

    update_paths_text()

    return frame