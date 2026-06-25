import tkinter as tk
from tkinter import messagebox

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
            "Conecte o celular via USB, autorize a depuração e informe "
            "o número do mobile."
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

    status_label = tk.Label(
        frame,
        text="Aguardando...",
        font=("Arial", 10),
    )

    result_text = tk.Text(
        frame,
        height=10,
        width=72,
        font=("Consolas", 9),
        wrap="word",
        state="disabled",
    )

    def set_status(text: str) -> None:
        status_label.config(text=text)
        frame.update_idletasks()

    def set_result_text(text: str) -> None:
        result_text.config(state="normal")
        result_text.delete("1.0", tk.END)
        result_text.insert(tk.END, text)
        result_text.config(state="disabled")

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
        else:
            lines.append("Id do participante encontrado: Não encontrado")

            if result["participant_id_error"]:
                first_error_line = result["participant_id_error"].splitlines()[0]
                lines.append(f"Aviso: {first_error_line}")

        return "\n".join(lines)

    def handle_check_device() -> None:
        try:
            result = backend.inspect_phone_documents(
                status_callback=set_status,
            )

            set_result_text(format_inspection_result(result))
            set_status(f"Celular encontrado: {result['device_id']}")

        except Exception as error:
            set_status("Erro ao verificar celular.")
            set_result_text("")
            messagebox.showerror("Erro", str(error))

    def handle_extract_documents() -> None:
        try:
            result = backend.extract_documents(
                mobile_number=mobile_number_entry.get(),
                status_callback=set_status,
            )

            messagebox.showinfo(
                "Sucesso",
                "Extração concluída com sucesso.\n\n"
                f"Mobile: {result['mobile_name']}\n"
                f"Dispositivo usado: {result['device_id']}\n"
                f"Participante: {result['participant_id']}\n\n"
                f"Pasta criada:\n{result['output_folder']}\n\n"
                f"JSON criado:\n{result['json_path']}",
            )

        except Exception as error:
            set_status("Erro na extração.")
            messagebox.showerror("Erro", str(error))

    check_button = tk.Button(
        frame,
        text="Verificar celular",
        font=("Arial", 10),
        width=24,
        command=handle_check_device,
    )
    check_button.pack(pady=8)

    extract_button = tk.Button(
        frame,
        text="Pegar pasta Documents",
        font=("Arial", 12),
        width=28,
        command=handle_extract_documents,
    )
    extract_button.pack(pady=10)

    status_label.pack(pady=5)

    result_text.pack(pady=8)

    output_label = tk.Label(
        frame,
        text=f"Destino: {backend.output_root}",
        font=("Arial", 9),
        wraplength=620,
        justify="center",
    )
    output_label.pack(pady=10)

    return frame