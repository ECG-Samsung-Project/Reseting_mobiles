# mobile/frontend.py

import threading
import tkinter as tk
from tkinter import messagebox, simpledialog
from tkinter import ttk

try:
    from .backend import MobileBackend
except ImportError:
    from mobile.backend import MobileBackend


def create_mobile_frame(parent: tk.Widget) -> tk.Frame:
    backend = MobileBackend()

    frame = tk.Frame(parent)

    title_label = tk.Label(
        frame,
        text="Extrair pasta Documents do celular",
        font=("Arial", 16, "bold"),
    )
    title_label.pack(pady=14)

    description_label = tk.Label(
        frame,
        text=(
            "Conecte o celular via USB, autorize a depuração, informe "
            "o número do mobile e selecione o contexto da coleta."
        ),
        font=("Arial", 10),
        wraplength=550,
    )
    description_label.pack(pady=4)

    mobile_frame = tk.Frame(frame)
    mobile_frame.pack(pady=12)

    mobile_number_label = tk.Label(
        mobile_frame,
        text="Número do mobile:",
        font=("Arial", 10),
    )
    mobile_number_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")

    mobile_number_entry = tk.Entry(
        mobile_frame,
        width=12,
        font=("Arial", 11),
    )
    mobile_number_entry.grid(row=0, column=1, padx=5, pady=5)

    collection_context_frame = tk.LabelFrame(
        frame,
        text="Contexto da coleta",
        font=("Arial", 10),
        padx=12,
        pady=8,
    )
    collection_context_frame.pack(pady=6)

    collection_context_var = tk.StringVar(value="")

    free_living_radio = tk.Radiobutton(
        collection_context_frame,
        text="Free Living",
        variable=collection_context_var,
        value="free_living",
        font=("Arial", 10),
    )
    free_living_radio.grid(row=0, column=0, padx=12, pady=4)

    in_clinic_radio = tk.Radiobutton(
        collection_context_frame,
        text="In Clinic",
        variable=collection_context_var,
        value="in_clinic",
        font=("Arial", 10),
    )
    in_clinic_radio.grid(row=0, column=1, padx=12, pady=4)

    check_button = tk.Button(
        frame,
        text="Verificar celular",
        font=("Arial", 10),
        width=24,
    )
    check_button.pack(pady=8)

    extract_button = tk.Button(
        frame,
        text="Pegar pasta Documents",
        font=("Arial", 12),
        width=28,
    )
    extract_button.pack(pady=10)

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

    result_text = tk.Text(
        frame,
        height=10,
        width=72,
        font=("Consolas", 9),
        wrap="word",
        state="disabled",
    )
    result_text.pack(pady=8)

    output_label = tk.Label(
        frame,
        text="Destino: selecione Free Living ou In Clinic",
        font=("Arial", 9),
        wraplength=620,
        justify="center",
    )
    output_label.pack(pady=10)

    def update_output_label(*_args) -> None:
        collection_context = collection_context_var.get()

        if not collection_context:
            output_label.config(
                text="Destino: selecione Free Living ou In Clinic"
            )
            return

        output_root = backend.get_output_root(collection_context)
        output_label.config(text=f"Destino: {output_root}")

    collection_context_var.trace_add("write", update_output_label)

    def set_status(text: str) -> None:
        frame.after(
            0,
            lambda: status_label.config(text=text),
        )

    def set_result_text(text: str) -> None:
        def update_text() -> None:
            result_text.config(state="normal")
            result_text.delete("1.0", tk.END)
            result_text.insert(tk.END, text)
            result_text.config(state="disabled")

        frame.after(0, update_text)

    def set_busy(is_busy: bool) -> None:
        def update_busy_state() -> None:
            state = "disabled" if is_busy else "normal"

            check_button.config(state=state)
            extract_button.config(state=state)
            mobile_number_entry.config(state=state)
            free_living_radio.config(state=state)
            in_clinic_radio.config(state=state)

            if is_busy:
                progress_bar.start(10)
            else:
                progress_bar.stop()

        frame.after(0, update_busy_state)

    def ask_for_participant_id(
        reason: str,
        suggested_id: str | None,
    ) -> str | None:
        response: dict[str, str | None] = {"participant_id": None}
        dialog_finished = threading.Event()

        def show_dialog() -> None:
            try:
                detected_id_text = (
                    f"\nID encontrado no celular: {suggested_id}\n"
                    if suggested_id
                    else "\nNenhum ID válido foi encontrado no celular.\n"
                )
                response["participant_id"] = simpledialog.askstring(
                    "Informar ID do participante",
                    "Não consegui identificar o participante automaticamente.\n\n"
                    f"Motivo: {reason.splitlines()[0]}\n"
                    f"{detected_id_text}\n"
                    "Confirme ou digite o ID correto para continuar:",
                    initialvalue=suggested_id or "",
                    parent=frame,
                )
            finally:
                dialog_finished.set()

        frame.after(0, show_dialog)
        dialog_finished.wait()

        return response["participant_id"]

    def run_background(
        task,
        on_success,
        on_error_title: str = "Erro",
    ) -> None:
        def worker() -> None:
            set_busy(True)

            try:
                result = task()
                frame.after(0, lambda: on_success(result))

            except Exception as error:
                error_message = str(error)

                def show_error() -> None:
                    status_label.config(text="Erro.")
                    messagebox.showerror(on_error_title, error_message)

                frame.after(0, show_error)

            finally:
                set_busy(False)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def format_inspection_result(result: dict) -> str:
        lines = [
            f"Celular encontrado: {result['device_id']}",
            "",
            f"Pastas em {result['documents_path']}:",
        ]

        if not result["folders"]:
            lines.append("Nenhuma pasta encontrada.")
        else:
            for folder in result["folders"]:
                lines.append(
                    f"{folder['folder_name']} -> {folder['file_count']} FILES"
                )

        lines.append("")

        if result["participant_id"]:
            lines.append(
                f"Id do participante encontrado: {result['participant_id']}"
            )

            if (
                result.get("participant_raw_id")
                and result["participant_raw_id"] != result["participant_id"]
            ):
                lines.append(
                    f"ID bruto no celular: {result['participant_raw_id']}"
                )

            if result.get("participant_lookup_source"):
                source_names = {
                    "manual_input": "informado manualmente",
                    "participants_summary_csv": "CSV de participantes",
                    "raw_alphanumeric_id": "ID alfanumérico do celular",
                }
                source = source_names.get(
                    result["participant_lookup_source"],
                    result["participant_lookup_source"],
                )
                lines.append(
                    f"Origem do ID: {source}"
                )
        else:
            lines.append("Id do participante encontrado: Não encontrado")

            if result["participant_id_error"]:
                first_error_line = result["participant_id_error"].splitlines()[0]
                lines.append(f"Aviso: {first_error_line}")

        return "\n".join(lines)

    def handle_check_device() -> None:
        def task() -> dict:
            return backend.inspect_phone_documents(
                status_callback=set_status,
                participant_id_prompt=ask_for_participant_id,
            )

        def on_success(result: dict) -> None:
            set_result_text(format_inspection_result(result))
            status_label.config(text=f"Celular encontrado: {result['device_id']}")

        run_background(
            task=task,
            on_success=on_success,
            on_error_title="Erro ao verificar celular",
        )

    def handle_extract_documents() -> None:
        mobile_number = mobile_number_entry.get()
        collection_context = collection_context_var.get()

        if not collection_context:
            messagebox.showerror(
                "Contexto não informado",
                "Selecione Free Living ou In Clinic antes de extrair.",
                parent=frame,
            )
            return

        def task() -> dict:
            return backend.extract_documents(
                mobile_number=mobile_number,
                collection_context=collection_context,
                status_callback=set_status,
                participant_id_prompt=ask_for_participant_id,
            )

        def on_success(result: dict) -> None:
            status_label.config(text="Extração concluída.")

            raw_id_line = (
                f"ID bruto no celular: {result['raw_participant_id']}\n"
                if result.get("raw_participant_id")
                else ""
            )
            messagebox.showinfo(
                "Sucesso",
                "Extração concluída com sucesso.\n\n"
                f"Mobile: {result['mobile_name']}\n"
                f"Dispositivo usado: {result['device_id']}\n"
                f"Participante: {result['participant_id']}\n"
                f"Contexto: {result['collection_context_label']} "
                f"({result['collection_context_code']})\n"
                f"Pasta de landing: {result['landing_folder']}\n"
                f"{raw_id_line}\n"
                f"Arquivo de saída:\n{result['output_archive']}\n\n"
                f"JSON criado:\n{result['output_root']}/metadata.json",
            )

        run_background(
            task=task,
            on_success=on_success,
            on_error_title="Erro na extração",
        )

    check_button.config(command=handle_check_device)
    extract_button.config(command=handle_extract_documents)

    return frame
