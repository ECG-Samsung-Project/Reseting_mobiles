import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from tkinter import ttk

try:
    from .backend import BatchMakerBackend
except ImportError:
    from backend import BatchMakerBackend


def create_batch_maker_frame(parent: tk.Widget) -> tk.Frame:
    backend = BatchMakerBackend()
    current_inventory: dict | None = None

    frame = tk.Frame(parent)

    title_label = tk.Label(
        frame,
        text="Montador de envio para Samsung",
        font=("Arial", 16, "bold"),
    )
    title_label.pack(pady=12)

    description_label = tk.Label(
        frame,
        text=(
            "Mapeia os dados disponíveis por paciente e monta um ZIP apenas "
            "com os pacientes selecionados."
        ),
        font=("Arial", 10),
        wraplength=760,
        justify="center",
    )
    description_label.pack(pady=4)

    info_label = tk.Label(
        frame,
        text=f"Config: {backend.config_path}",
        font=("Arial", 9),
        wraplength=760,
        justify="center",
    )
    info_label.pack(pady=4)

    status_label = tk.Label(
        frame,
        text="Aguardando mapeamento...",
        font=("Arial", 10),
    )
    status_label.pack(pady=5)

    progress_bar = ttk.Progressbar(
        frame,
        mode="indeterminate",
        length=360,
    )
    progress_bar.pack(pady=4)
    progress_bar.stop()

    table_frame = tk.Frame(frame)
    table_frame.pack(fill="both", expand=True, padx=10, pady=8)

    tree_scroll_y = ttk.Scrollbar(table_frame, orient="vertical")
    tree_scroll_y.pack(side="right", fill="y")

    tree_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal")
    tree_scroll_x.pack(side="bottom", fill="x")

    tree = ttk.Treeview(
        table_frame,
        show="headings",
        selectmode="extended",
        yscrollcommand=tree_scroll_y.set,
        xscrollcommand=tree_scroll_x.set,
        height=17,
    )

    tree.pack(fill="both", expand=True)

    tree_scroll_y.config(command=tree.yview)
    tree_scroll_x.config(command=tree.xview)

    button_frame = tk.Frame(frame)
    button_frame.pack(pady=10)

    map_button = tk.Button(
        button_frame,
        text="Mapear dados",
        font=("Arial", 10),
        width=22,
    )
    map_button.grid(row=0, column=0, padx=6)

    zip_button = tk.Button(
        button_frame,
        text="Montar ZIP selecionados",
        font=("Arial", 10),
        width=26,
    )
    zip_button.grid(row=0, column=1, padx=6)

    clear_button = tk.Button(
        button_frame,
        text="Limpar seleção",
        font=("Arial", 10),
        width=20,
    )
    clear_button.grid(row=0, column=2, padx=6)

    def set_status(text: str) -> None:
        frame.after(
            0,
            lambda: status_label.config(text=text),
        )

    def set_busy(is_busy: bool) -> None:
        def update_state() -> None:
            state = "disabled" if is_busy else "normal"

            map_button.config(state=state)
            zip_button.config(state=state)
            clear_button.config(state=state)

            if is_busy:
                progress_bar.start(10)
            else:
                progress_bar.stop()

        frame.after(0, update_state)

    def configure_table_columns(source_names: list[str]) -> None:
        columns = ["patient_id", "total_found", *source_names]

        tree["columns"] = columns

        tree.heading("patient_id", text="patient_id")
        tree.column("patient_id", width=150, anchor="center", stretch=False)

        tree.heading("total_found", text="total")
        tree.column("total_found", width=70, anchor="center", stretch=False)

        for source_name in source_names:
            tree.heading(source_name, text=source_name)
            tree.column(source_name, width=130, anchor="center", stretch=False)

    def fill_table(inventory: dict) -> None:
        tree.delete(*tree.get_children())

        source_names = inventory["sources"]
        configure_table_columns(source_names)

        for row in inventory["rows"]:
            values = [
                row["patient_id"],
                row["total_found"],
            ]

            for source_name in source_names:
                source_info = row["sources"][source_name]
                count = source_info["count"]

                if count > 0:
                    values.append(f"OK ({count})")
                else:
                    values.append("MISSING")

            tree.insert(
                "",
                "end",
                iid=row["patient_id"],
                values=values,
            )

    def handle_map_data() -> None:
        nonlocal current_inventory

        def task() -> dict:
            set_status("Mapeando dados...")
            return backend.build_inventory()

        def worker() -> None:
            set_busy(True)

            try:
                inventory = task()
                current_inventory = inventory

                def show_result() -> None:
                    fill_table(inventory)

                    status_label.config(
                        text=(
                            f"Mapeamento concluído. "
                            f"{len(inventory['rows'])} paciente(s) encontrado(s)."
                        )
                    )

                    info_label.config(
                        text=(
                            f"Config: {inventory['config_path']} | "
                            f"Output: {inventory['output_root']}"
                        )
                    )

                frame.after(0, show_result)

            except Exception as error:
                error_message = str(error)

                def show_error() -> None:
                    status_label.config(text="Erro no mapeamento.")
                    messagebox.showerror("Erro", error_message)

                frame.after(0, show_error)

            finally:
                set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    def get_selected_patient_ids() -> list[str]:
        return list(tree.selection())

    def handle_make_zip() -> None:
        selected_patient_ids = get_selected_patient_ids()

        def task() -> dict:
            set_status("Montando ZIP...")
            return backend.make_zip_for_patients(
                selected_patient_ids=selected_patient_ids,
                inventory=current_inventory,
            )

        def worker() -> None:
            set_busy(True)

            try:
                result = task()

                def show_result() -> None:
                    status_label.config(text="ZIP criado com sucesso.")

                    messagebox.showinfo(
                        "ZIP criado",
                        "Arquivo ZIP criado com sucesso.\n\n"
                        f"Pacientes incluídos: {result['included_patient_count']}\n"
                        f"Arquivos incluídos: {result['included_files']}\n\n"
                        f"ZIP:\n{result['zip_path']}",
                    )

                frame.after(0, show_result)

            except Exception as error:
                error_message = str(error)

                def show_error() -> None:
                    status_label.config(text="Erro ao montar ZIP.")
                    messagebox.showerror("Erro", error_message)

                frame.after(0, show_error)

            finally:
                set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    def handle_clear_selection() -> None:
        for item in tree.selection():
            tree.selection_remove(item)

        status_label.config(text="Seleção limpa.")

    map_button.config(command=handle_map_data)
    zip_button.config(command=handle_make_zip)
    clear_button.config(command=handle_clear_selection)

    return frame


def run_app() -> None:
    root = tk.Tk()
    root.title("Batch Maker Samsung")
    root.geometry("920x680")
    root.resizable(True, True)

    frame = create_batch_maker_frame(root)
    frame.pack(fill="both", expand=True)

    root.mainloop()