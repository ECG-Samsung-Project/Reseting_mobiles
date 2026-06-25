import tkinter as tk
from tkinter import messagebox

try:
    from .backend import WatchBackend
except ImportError:
    from watch.backend import WatchBackend


def create_watch_frame(parent: tk.Widget) -> tk.Frame:
    backend = WatchBackend()

    frame = tk.Frame(parent)

    title_label = tk.Label(
        frame,
        text="Extrair pasta Documents do relógio",
        font=("Arial", 16, "bold"),
    )
    title_label.pack(pady=14)

    description_label = tk.Label(
        frame,
        text="Informe o IP uma vez, depois preencha a porta de pareamento e a porta de conexão.",
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
    watch_number_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")

    watch_number_entry = tk.Entry(
        watch_frame,
        width=12,
        font=("Arial", 11),
    )
    watch_number_entry.grid(row=0, column=1, padx=5, pady=5)

    ip_frame = tk.LabelFrame(
        frame,
        text="Dados do relógio",
        padx=10,
        pady=10,
    )
    ip_frame.pack(pady=8, padx=20, fill="x")

    watch_ip_label = tk.Label(
        ip_frame,
        text="IP do relógio:",
        font=("Arial", 10),
    )
    watch_ip_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

    watch_ip_entry = tk.Entry(
        ip_frame,
        width=25,
        font=("Arial", 10),
    )
    watch_ip_entry.grid(row=0, column=1, padx=5, pady=5)
    watch_ip_entry.insert(0, "30.0.0.218")

    pair_frame = tk.LabelFrame(
        frame,
        text="1. Pareamento",
        padx=10,
        pady=10,
    )
    pair_frame.pack(pady=8, padx=20, fill="x")

    pairing_port_label = tk.Label(
        pair_frame,
        text="Porta de pareamento:",
        font=("Arial", 10),
    )
    pairing_port_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

    pairing_port_entry = tk.Entry(
        pair_frame,
        width=18,
        font=("Arial", 10),
    )
    pairing_port_entry.grid(row=0, column=1, padx=5, pady=5)

    pairing_code_label = tk.Label(
        pair_frame,
        text="Senha:",
        font=("Arial", 10),
    )
    pairing_code_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)

    pairing_code_entry = tk.Entry(
        pair_frame,
        width=18,
        font=("Arial", 10),
    )
    pairing_code_entry.grid(row=1, column=1, padx=5, pady=5)

    connect_frame = tk.LabelFrame(
        frame,
        text="2. Conexão",
        padx=10,
        pady=10,
    )
    connect_frame.pack(pady=8, padx=20, fill="x")

    connect_port_label = tk.Label(
        connect_frame,
        text="Porta de conexão:",
        font=("Arial", 10),
    )
    connect_port_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

    connect_port_entry = tk.Entry(
        connect_frame,
        width=18,
        font=("Arial", 10),
    )
    connect_port_entry.grid(row=0, column=1, padx=5, pady=5)

    status_label = tk.Label(
        frame,
        text="Aguardando...",
        font=("Arial", 10),
    )

    def set_status(text: str) -> None:
        status_label.config(text=text)
        frame.update_idletasks()

    def handle_pair_watch() -> None:
        try:
            pairing_address = backend.get_pairing_address(
                ip=watch_ip_entry.get(),
                pairing_port=pairing_port_entry.get(),
            )

            set_status(f"Pareando em {pairing_address}...")

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
            messagebox.showerror("Erro", str(error))

    def handle_connect_watch() -> None:
        try:
            connect_address = backend.get_connect_address(
                ip=watch_ip_entry.get(),
                connect_port=connect_port_entry.get(),
            )

            set_status(f"Conectando em {connect_address}...")

            backend.check_adb_installed()

            output, target_device_id = backend.connect_watch(
                ip=watch_ip_entry.get(),
                connect_port=connect_port_entry.get(),
            )

            set_status(f"Conectado em {target_device_id}")

            messagebox.showinfo(
                "Conexão",
                f"Resultado da conexão:\n\n{output}\n\n"
                f"Dispositivo alvo definido:\n{target_device_id}",
            )

        except Exception as error:
            set_status("Erro na conexão.")
            messagebox.showerror("Erro", str(error))

    def handle_disconnect_all_devices() -> None:
        try:
            set_status("Desconectando todos os devices...")

            backend.check_adb_installed()

            output = backend.disconnect_all_devices()

            set_status("Todos os devices foram desconectados.")

            messagebox.showinfo(
                "Desconectar",
                f"Resultado:\n\n{output or 'Todos os devices foram desconectados.'}",
            )

        except Exception as error:
            set_status("Erro ao desconectar devices.")
            messagebox.showerror("Erro", str(error))

    def handle_extract_documents() -> None:
        try:
            result = backend.extract_documents(
                watch_number=watch_number_entry.get(),
                ip=watch_ip_entry.get(),
                pairing_port=pairing_port_entry.get(),
                connect_port=connect_port_entry.get(),
                status_callback=set_status,
            )

            messagebox.showinfo(
                "Sucesso",
                "Extração concluída com sucesso.\n\n"
                f"Relógio: {result['watch_name']}\n"
                f"Dispositivo usado: {result['device_id']}\n"
                f"ID usado: {result['selected_id']}\n\n"
                f"Pasta criada:\n{result['output_folder']}\n\n"
                f"JSON criado:\n{result['json_path']}",
            )

        except Exception as error:
            set_status("Erro na extração.")
            messagebox.showerror("Erro", str(error))

    pair_button = tk.Button(
        pair_frame,
        text="Parear relógio",
        font=("Arial", 10),
        width=18,
        command=handle_pair_watch,
    )
    pair_button.grid(row=0, column=2, rowspan=2, padx=10, pady=5)

    connect_button = tk.Button(
        connect_frame,
        text="Conectar relógio",
        font=("Arial", 10),
        width=18,
        command=handle_connect_watch,
    )
    connect_button.grid(row=0, column=2, padx=10, pady=5)

    disconnect_button = tk.Button(
        frame,
        text="Desconectar de todos os devices",
        font=("Arial", 10),
        width=32,
        command=handle_disconnect_all_devices,
    )
    disconnect_button.pack(pady=6)

    extract_button = tk.Button(
        frame,
        text="3. Pegar pasta Documents",
        font=("Arial", 12),
        width=28,
        command=handle_extract_documents,
    )
    extract_button.pack(pady=10)

    status_label.pack(pady=5)

    return frame