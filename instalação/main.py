import tkinter as tk
from tkinter import messagebox

from backend.process import setup_device, reset_device


root = tk.Tk()

root.title("Instalador de Apps")
root.geometry("650x350")
root.resizable(False, False)


title_label = tk.Label(
    root,
    text="Instalar apps e conceder permissões",
    font=("Arial", 16, "bold"),
)
title_label.pack(pady=20)


description_label = tk.Label(
    root,
    text=(
        "Instala os APKs do celular usando ADB e tenta conceder permissões "
        "runtime declaradas pelos apps."
    ),
    font=("Arial", 10),
    wraplength=560,
)
description_label.pack(pady=5)


status_label = tk.Label(
    root,
    text="Aguardando...",
    font=("Arial", 10),
)
status_label.pack(pady=5)


def update_status(message: str):
    status_label.config(text=message)
    root.update_idletasks()


def start_installation():
    try:
        final_log = setup_device(
            progress_callback=update_status
        )

        messagebox.showinfo(
            "Sucesso",
            "Processo concluído:\n\n" + "\n\n".join(final_log),
        )

    except Exception as error:
        update_status("Erro na instalação.")
        messagebox.showerror(
            "Erro",
            str(error),
        )

def start_reseting_device():
    try:
        reset_device(progress_callback=update_status)
        messagebox.showinfo(
            "Sucesso",
            "Celular reiniciado em modo de recuperação.",
        )
    except Exception as error:
        update_status("Erro ao resetar o celular.")
        messagebox.showerror(
            "Erro",
            str(error),
        )

reset_button = tk.Button(
    root,
    text="Resetar celular",
    font=("Arial", 12),
    width=25,
    command=start_reseting_device,
)
reset_button.pack(pady=20)

install_button = tk.Button(
    root,
    text="Instalar apps",
    font=("Arial", 12),
    width=25,
    command=start_installation,
)
install_button.pack(pady=20)


root.mainloop()