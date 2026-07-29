# watch/frontend.py

import tkinter as tk
from tkinter import messagebox, simpledialog

from core.scrollable_frame import create_scrollable_frame

try:
    from .backend import WatchBackend
except ImportError:
    from watch.backend import WatchBackend


def create_watch_frame(parent: tk.Widget) -> tk.Frame:
    backend = WatchBackend()

    outer_frame, frame = create_scrollable_frame(parent)

    title_label = tk.Label(
        frame,
        text="Extrair dados do relógio",
        font=("Arial", 16, "bold"),
    )
    title_label.pack(pady=14)

    description_label = tk.Label(
        frame,
        text=(
            "Informe o IP uma vez, depois preencha a porta de "
            "pareamento e a porta de conexão."
        ),
        font=("Arial", 10),
        wraplength=550,
    )
    description_label.pack(pady=4)

    watch_frame = tk.Frame(frame)
    watch_frame.pack(pady=8)

    watch_number_label = tk.Label(
        watch_frame,
        text="Número do relógio:",
        font=("Arial", 10),
    )
    watch_number_label.grid(
        row=0,
        column=0,
        padx=5,
        pady=5,
        sticky="e",
    )

    watch_number_entry = tk.Entry(
        watch_frame,
        width=12,
        font=("Arial", 11),
    )
    watch_number_entry.grid(
        row=0,
        column=1,
        padx=5,
        pady=5,
    )

    collection_context_frame = tk.LabelFrame(
        frame,
        text="Contexto da coleta",
        padx=10,
        pady=8,
    )
    collection_context_frame.pack(
        pady=8,
        padx=20,
        fill="x",
    )

    collection_context_var = tk.StringVar(value="")

    free_living_radio = tk.Radiobutton(
        collection_context_frame,
        text="Free Living",
        variable=collection_context_var,
        value="free_living",
        font=("Arial", 10),
    )
    free_living_radio.grid(
        row=0,
        column=0,
        padx=18,
        pady=4,
    )

    in_clinic_radio = tk.Radiobutton(
        collection_context_frame,
        text="In Clinic",
        variable=collection_context_var,
        value="in_clinic",
        font=("Arial", 10),
    )
    in_clinic_radio.grid(
        row=0,
        column=1,
        padx=18,
        pady=4,
    )

    output_label = tk.Label(
        collection_context_frame,
        text="Destino: selecione Free Living ou In Clinic",
        font=("Arial", 9),
        wraplength=650,
        justify="center",
    )
    output_label.grid(
        row=1,
        column=0,
        columnspan=2,
        padx=5,
        pady=6,
    )

    def update_output_label(*_args) -> None:
        collection_context = collection_context_var.get()

        if not collection_context:
            output_label.config(
                text="Destino: selecione Free Living ou In Clinic"
            )
            return

        output_root = backend.config.get_output_root(
            collection_context
        )

        output_label.config(
            text=f"Destino: {output_root}"
        )

    collection_context_var.trace_add(
        "write",
        update_output_label,
    )

    ip_frame = tk.LabelFrame(
        frame,
        text="Dados do relógio",
        padx=10,
        pady=10,
    )
    ip_frame.pack(
        pady=8,
        padx=20,
        fill="x",
    )

    watch_ip_label = tk.Label(
        ip_frame,
        text="IP do relógio:",
        font=("Arial", 10),
    )
    watch_ip_label.grid(
        row=0,
        column=0,
        sticky="w",
        padx=5,
        pady=5,
    )

    watch_ip_entry = tk.Entry(
        ip_frame,
        width=25,
        font=("Arial", 10),
    )
    watch_ip_entry.grid(
        row=0,
        column=1,
        padx=5,
        pady=5,
    )
    watch_ip_entry.insert(
        0,
        "30.0.0.218",
    )

    pair_frame = tk.LabelFrame(
        frame,
        text="1. Pareamento",
        padx=10,
        pady=10,
    )
    pair_frame.pack(
        pady=8,
        padx=20,
        fill="x",
    )

    pairing_port_label = tk.Label(
        pair_frame,
        text="Porta de pareamento:",
        font=("Arial", 10),
    )
    pairing_port_label.grid(
        row=0,
        column=0,
        sticky="w",
        padx=5,
        pady=5,
    )

    pairing_port_entry = tk.Entry(
        pair_frame,
        width=18,
        font=("Arial", 10),
    )
    pairing_port_entry.grid(
        row=0,
        column=1,
        padx=5,
        pady=5,
    )

    pairing_code_label = tk.Label(
        pair_frame,
        text="Senha:",
        font=("Arial", 10),
    )
    pairing_code_label.grid(
        row=1,
        column=0,
        sticky="w",
        padx=5,
        pady=5,
    )

    pairing_code_entry = tk.Entry(
        pair_frame,
        width=18,
        font=("Arial", 10),
    )
    pairing_code_entry.grid(
        row=1,
        column=1,
        padx=5,
        pady=5,
    )

    connect_frame = tk.LabelFrame(
        frame,
        text="2. Conexão",
        padx=10,
        pady=10,
    )
    connect_frame.pack(
        pady=8,
        padx=20,
        fill="x",
    )

    connect_port_label = tk.Label(
        connect_frame,
        text="Porta de conexão:",
        font=("Arial", 10),
    )
    connect_port_label.grid(
        row=0,
        column=0,
        sticky="w",
        padx=5,
        pady=5,
    )

    connect_port_entry = tk.Entry(
        connect_frame,
        width=18,
        font=("Arial", 10),
    )
    connect_port_entry.grid(
        row=0,
        column=1,
        padx=5,
        pady=5,
    )

    status_label = tk.Label(
        frame,
        text="Aguardando...",
        font=("Arial", 10),
    )

    def set_status(text: str) -> None:
        status_label.config(text=text)
        frame.update_idletasks()

    def set_result_text(text: str) -> None:
        result_text.config(state="normal")
        result_text.delete("1.0", tk.END)
        result_text.insert(tk.END, text)
        result_text.config(state="disabled")

    def ask_for_watch_id(
        reason: str,
        suggested_id: str | None,
    ) -> str | None:
        detected_text = (
            f"\nID sugerido: {suggested_id}\n"
            if suggested_id
            else "\nNenhum ID válido foi encontrado nos arquivos.\n"
        )

        return simpledialog.askstring(
            "Informar ID do participante",
            "Não consegui identificar o participante automaticamente.\n\n"
            f"Motivo: {reason.splitlines()[0]}\n"
            f"{detected_text}\n"
            "Informe o ID no formato ABC-12-3456 para continuar:",
            initialvalue=suggested_id or "",
            parent=frame,
        )

    def format_watch_inspection_result(
        result: dict,
    ) -> str:
        source_names = {
            "watch_files": "arquivos do relógio",
            "manual_input": "informado manualmente",
        }

        id_resolution_source = result.get(
            "id_resolution_source"
        )

        id_source = source_names.get(
            id_resolution_source,
            id_resolution_source or "não informado",
        )

        lines = [
            f"Dispositivo: {result['device_id']}",
            f"ID do participante: {result['selected_id']}",
            f"Origem do ID: {id_source}",
            "",
            f"Pastas verificadas: {result['documents_path']}",
            f"Pastas: {result['folder_count']}",
            f"Arquivos: {result['file_count']}",
            "",
            result["tree_text"],
        ]

        return "\n".join(lines)

    def handle_inspect_watch_documents() -> None:
        try:
            result = backend.inspect_watch_documents(
                ip=watch_ip_entry.get(),
                connect_port=connect_port_entry.get(),
                status_callback=set_status,
                watch_id_prompt=ask_for_watch_id,
            )

            set_result_text(
                format_watch_inspection_result(result)
            )

            set_status(
                f"Varredura concluída: "
                f"{result['selected_id']}"
            )

        except Exception as error:
            set_status("Erro na varredura.")

            messagebox.showerror(
                "Erro",
                str(error),
            )

    def handle_pair_watch() -> None:
        try:
            pairing_address = backend.get_pairing_address(
                ip=watch_ip_entry.get(),
                pairing_port=pairing_port_entry.get(),
            )

            set_status(
                f"Pareando em {pairing_address}..."
            )

            backend.check_adb_installed()

            output = backend.pair_watch(
                ip=watch_ip_entry.get(),
                pairing_port=pairing_port_entry.get(),
                pairing_code=pairing_code_entry.get(),
            )

            set_status("Pareamento concluído.")

            messagebox.showinfo(
                "Pareamento",
                f"Resultado do pareamento:\n\n{output}",
            )

        except Exception as error:
            set_status("Erro no pareamento.")

            messagebox.showerror(
                "Erro",
                str(error),
            )

    def handle_connect_watch() -> None:
        try:
            connect_address = backend.get_connect_address(
                ip=watch_ip_entry.get(),
                connect_port=connect_port_entry.get(),
            )

            set_status(
                f"Conectando em {connect_address}..."
            )

            backend.check_adb_installed()

            output, target_device_id = backend.connect_watch(
                ip=watch_ip_entry.get(),
                connect_port=connect_port_entry.get(),
            )

            set_status(
                f"Conectado em {target_device_id}"
            )

            messagebox.showinfo(
                "Conexão",
                f"Resultado da conexão:\n\n{output}\n\n"
                f"Dispositivo alvo definido:\n"
                f"{target_device_id}",
            )

            result = backend.inspect_watch_documents(
                ip=watch_ip_entry.get(),
                connect_port=connect_port_entry.get(),
                status_callback=set_status,
                watch_id_prompt=ask_for_watch_id,
            )

            set_result_text(
                format_watch_inspection_result(result)
            )

        except Exception as error:
            set_status("Erro na conexão.")

            messagebox.showerror(
                "Erro",
                str(error),
            )

    def handle_disconnect_all_devices() -> None:
        try:
            set_status(
                "Desconectando todos os devices..."
            )

            backend.check_adb_installed()

            output = backend.disconnect_all_devices()

            set_status(
                "Todos os devices foram desconectados."
            )

            messagebox.showinfo(
                "Desconectar",
                "Resultado:\n\n"
                f"{output or 'Todos os devices foram desconectados.'}",
            )

        except Exception as error:
            set_status(
                "Erro ao desconectar devices."
            )

            messagebox.showerror(
                "Erro",
                str(error),
            )

    def handle_extract_documents() -> None:
        collection_context = collection_context_var.get()

        if not collection_context:
            messagebox.showerror(
                "Contexto não informado",
                "Selecione Free Living ou In Clinic antes de extrair.",
                parent=frame,
            )
            return

        try:
            result = backend.extract_documents(
                watch_number=watch_number_entry.get(),
                ip=watch_ip_entry.get(),
                pairing_port=pairing_port_entry.get(),
                connect_port=connect_port_entry.get(),
                collection_context=collection_context,
                status_callback=set_status,
                watch_id_prompt=ask_for_watch_id,
            )

            set_status("Extração concluída.")

            id_source = (
                "informado manualmente"
                if result.get("id_resolution_source")
                == "manual_input"
                else "encontrado nos arquivos"
            )

            messagebox.showinfo(
                "Sucesso",
                "Extração concluída com sucesso.\n\n"
                f"Relógio: {result['watch_name']}\n"
                f"Dispositivo usado: {result['device_id']}\n"
                f"Participante: {result['selected_id']}\n"
                f"Origem do ID: {id_source}\n"
                f"Contexto: "
                f"{result['collection_context_label']}\n\n"
                f"Arquivo ZIP criado:\n"
                f"{result['output_archive']}\n\n"
                f"Metadados incluídos no ZIP: "
                f"{result['metadata_file']}",
            )

        except Exception as error:
            set_status("Erro na extração.")

            messagebox.showerror(
                "Erro",
                str(error),
            )

    pair_button = tk.Button(
        pair_frame,
        text="Parear relógio",
        font=("Arial", 10),
        width=18,
        command=handle_pair_watch,
    )
    pair_button.grid(
        row=0,
        column=2,
        rowspan=2,
        padx=10,
        pady=5,
    )

    connect_button = tk.Button(
        connect_frame,
        text="Conectar relógio",
        font=("Arial", 10),
        width=18,
        command=handle_connect_watch,
    )
    connect_button.grid(
        row=0,
        column=2,
        padx=10,
        pady=5,
    )

    disconnect_button = tk.Button(
        frame,
        text="Desconectar de todos os devices",
        font=("Arial", 10),
        width=32,
        command=handle_disconnect_all_devices,
    )
    disconnect_button.pack(pady=6)

    inspect_button = tk.Button(
        frame,
        text="Verificar dados do relógio",
        font=("Arial", 10),
        width=32,
        command=handle_inspect_watch_documents,
    )
    inspect_button.pack(pady=6)

    extract_button = tk.Button(
        frame,
        text="3. Extrair e compactar",
        font=("Arial", 12),
        width=28,
        command=handle_extract_documents,
    )
    extract_button.pack(pady=10)

    status_label.pack(pady=5)

    result_text = tk.Text(
        frame,
        height=12,
        width=78,
        font=("Consolas", 9),
        wrap="none",
        state="disabled",
    )
    result_text.pack(pady=8)

    return outer_frame