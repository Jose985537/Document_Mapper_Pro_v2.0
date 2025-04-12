import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import threading
import logging

# Configuración del logging: se registran eventos en un archivo y en la salida estándar
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mapper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# ─────────────────────────────────────────────────────────────────────────────
# Clase Tooltip para mostrar ayuda emergente en los widgets
# ─────────────────────────────────────────────────────────────────────────────
class Tooltip:
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip = None
        self.id = None
        self.widget.bind("<Enter>", self.schedule)
        self.widget.bind("<Leave>", self.unschedule)

    def schedule(self, event=None):
        self.unschedule()
        self.id = self.widget.after(self.delay, self.show)

    def unschedule(self, event=None):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
        self.hide()

    def show(self):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(self.tooltip, text=self.text, background="#ffffe0",
                          relief="solid", borderwidth=1, padding=(5, 2))
        label.pack()

    def hide(self):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

# ─────────────────────────────────────────────────────────────────────────────
# Clase EnhancedFolderMapper: Implementa la GUI y la lógica de mapeo
# ─────────────────────────────────────────────────────────────────────────────
class EnhancedFolderMapper:
    def __init__(self, root):
        self.root = root
        # Intento de asignar icono personalizado para la ventana
        try:
            self.root.iconbitmap("recursos/Logo.ico")
        except:
            try:
                logo = tk.PhotoImage(file="recursos/Logo.png")
                self.root.iconphoto(True, logo)
            except: 
                pass
        self.root.title("Document Mapper Pro v5.0")
        self.root.geometry("1000x720")
        self.tree_data = {}  # Diccionario que almacena: {ID_del_nodo: {"path": ruta, "selected": estado, "loaded": bool}}
        self.style = ttk.Style()
        self._setup_styles()
        self._create_ui()
        self._setup_bindings()

    # Configuración de estilos de la interfaz (colores, fuentes y temas)
    def _setup_styles(self):
        self.style.theme_use("clam")
        self.style.configure("Primary.TFrame", background="#2B579A")
        self.style.configure("Secondary.TFrame", background="#FFFFFF")
        self.style.configure("Accent.TButton", background="#1C3D6B", foreground="white",
                             font=("Segoe UI", 9, "bold"), borderwidth=0)
        self.style.map("Accent.TButton", background=[("active", "#3A6BB5"), ("disabled", "#CCCCCC")])
        self.style.configure("Treeview", font=("Segoe UI", 9), rowheight=25)
        self.style.map("Treeview", background=[("selected", "#2B579A")], foreground=[("selected", "white")])

    # Construcción de la interfaz principal
    def _create_ui(self):
        # Cinta superior con logotipo y botón de ayuda
        header_frame = ttk.Frame(self.root, style="Primary.TFrame", padding=10)
        header_frame.pack(fill=tk.X)
        ttk.Label(header_frame, text="Document Mapper Pro", font=("Segoe UI Semibold", 16),
                  foreground="white", background="#2B579A").pack(side=tk.LEFT, padx=10)
        ttk.Button(header_frame, text="Ayuda", style="Accent.TButton", command=self.mostrar_ayuda).pack(side=tk.RIGHT, padx=10)

        # Panel principal dividido en controles y área derecha
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        control_frame = ttk.Frame(main_paned, width=280, padding=10)
        self._create_controls(control_frame)

        right_paned = ttk.PanedWindow(main_paned, orient=tk.VERTICAL)
        tree_frame = ttk.Frame(right_paned)
        self._create_treeview(tree_frame)
        preview_frame = ttk.Frame(right_paned)
        self._create_preview(preview_frame)

        right_paned.add(tree_frame, weight=3)
        right_paned.add(preview_frame, weight=1)
        main_paned.add(control_frame, weight=0)
        main_paned.add(right_paned, weight=1)

    # Panel de controles: selección de carpeta, botones de vista y acciones
    def _create_controls(self, parent):
        folder_frame = ttk.LabelFrame(parent, text="CARPETA A ANALIZAR", padding=10)
        folder_frame.pack(fill=tk.X, pady=5)
        self.folder_path = tk.StringVar()
        ttk.Entry(folder_frame, textvariable=self.folder_path, state="readonly").pack(fill=tk.X, pady=5)
        browse_btn = ttk.Button(folder_frame, text="Examinar", style="Accent.TButton", command=self.select_folder)
        browse_btn.pack(fill=tk.X)
        Tooltip(browse_btn, "Seleccionar carpeta raíz para análisis")

        view_frame = ttk.LabelFrame(parent, text="GESTIÓN DE VISTA", padding=10)
        view_frame.pack(fill=tk.X, pady=5)
        btn_grid = ttk.Frame(view_frame)
        btn_grid.pack(fill=tk.X)
        ttk.Button(btn_grid, text="Expandir Todo", style="Accent.TButton", command=self.expand_all).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(btn_grid, text="Colapsar Todo", style="Accent.TButton", command=self.collapse_all).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        selection_frame = ttk.LabelFrame(parent, text="SELECCIÓN", padding=10)
        selection_frame.pack(fill=tk.X, pady=5)
        ttk.Button(selection_frame, text="Seleccionar Todo", style="Accent.TButton",
                   command=lambda: self.toggle_all(True, True)).pack(fill=tk.X)
        ttk.Button(selection_frame, text="Deseleccionar Todo", style="Accent.TButton",
                   command=lambda: self.toggle_all(False, True)).pack(fill=tk.X, pady=5)

        self.generate_btn = ttk.Button(parent, text="Generar Mapa", style="Accent.TButton", command=self.start_mapping)
        self.generate_btn.pack(fill=tk.X, pady=15)
        self.status_label = ttk.Label(parent, text="Estado: Listo", anchor=tk.CENTER, foreground="#107C10")
        self.status_label.pack(fill=tk.X)

    # Creación del TreeView para mostrar la estructura de directorios y archivos
    def _create_treeview(self, parent):
        container = ttk.Frame(parent, padding=5)
        container.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(container, columns=("type", "selected"), show="tree headings", selectmode="none")
        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.column("#0", width=400, anchor=tk.W)
        self.tree.column("type", width=100, anchor=tk.CENTER)
        self.tree.column("selected", width=80, anchor=tk.CENTER)
        self.tree.heading("#0", text="Estructura", anchor=tk.W)
        self.tree.heading("type", text="Tipo")
        self.tree.heading("selected", text="Incluir")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Creación del área de vista previa que muestra el mapeo de la estructura en tiempo real
    def _create_preview(self, parent):
        preview_frame = ttk.Frame(parent, padding=5)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(preview_frame, text="Vista Previa de la Estructura", font=("Segoe UI", 10, "bold"),
                 foreground="#2B579A").pack(anchor=tk.W, pady=5)
        self.preview_text = tk.Text(preview_frame, height=10, state="disabled", font=("Courier New", 9), wrap=tk.NONE)
        text_scroll_y = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview_text.yview)
        text_scroll_x = ttk.Scrollbar(preview_frame, orient="horizontal", command=self.preview_text.xview)
        self.preview_text.configure(yscrollcommand=text_scroll_y.set, xscrollcommand=text_scroll_x.set)
        text_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        text_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.preview_text.pack(fill=tk.BOTH, expand=True)

    # Configuración de bindings globales para atajos de teclado y eventos de mouse
    def _setup_bindings(self):
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-1>", self.on_checkbox_click)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.root.bind("<Control-o>", lambda e: self.select_folder())
        self.root.bind("<F5>", lambda e: self.start_mapping())

    # Función de ayuda que muestra un mensaje informativo con la autoría
    def mostrar_ayuda(self):
        info = (
            "Document Mapper Pro v5.0\n\n"
            "Desarrollado por: José Gabriel Calderón\n"
            "Contacto: https://github.com/Jose985537\n"
             "                   gc5444592@gmail.com\n\n"
            "Funcionalidades:\n"
            " - Mapeo completo de estructuras de directorios\n"
            " - Selección inteligente de elementos\n"
            " - Generación de informes en formato TXT\n\n"
            "© 2025 Todos los derechos reservados"
        )
        messagebox.showinfo("Soporte Técnico", info)

    # Menú contextual (botón derecho) para seleccionar o deseleccionar todo el subdirectorio
    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item and "dir" in self.tree.item(item, "tags"):
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="Seleccionar Subdirectorio Completo", command=lambda: self.toggle_subdirectory(item, True))
            menu.add_command(label="Deseleccionar Subdirectorio Completo", command=lambda: self.toggle_subdirectory(item, False))
            menu.tk_popup(event.x_root, event.y_root)

    def toggle_subdirectory(self, parent_item, state):
        if parent_item in self.tree_data:
            self.tree_data[parent_item]["selected"] = state
            self.tree.set(parent_item, "selected", "☑" if state else "☐")
            self._update_children_state(parent_item, state)
            self._update_preview()

    # Permite seleccionar la carpeta raíz y cargar su estructura completa
    def select_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta raíz")
        if folder:
            try:
                self.folder_path.set(folder)
                self.tree.delete(*self.tree.get_children())
                self.tree_data.clear()
                self.populate_tree("", folder)
                self._update_status("Carpeta cargada exitosamente", "#107C10")
                self._update_preview()
            except Exception as e:
                self._update_status(f"Error: {str(e)}", "#D83B01")

    # Población del TreeView: se insertan elementos de la carpeta sin filtrar extensiones
    def populate_tree(self, parent, path):
        try:
            items = sorted(os.listdir(path), key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
            for item in items:
                full_path = os.path.join(path, item)
                is_dir = os.path.isdir(full_path)
                item_id = self.tree.insert(parent, "end", text=f"  {item}", 
                                        values=("📁 Directorio" if is_dir else "📄 Archivo", "☑"),
                                        tags=("dir" if is_dir else "file"))
                self.tree_data[item_id] = {"path": full_path, "selected": True, "loaded": False}
                if is_dir:
                    # Se agrega un placeholder para carga dinámica
                    self.tree.insert(item_id, "end", text="...")
        except PermissionError:
            self.tree.insert(parent, "end", text="[Acceso denegado]", tags=("error",))
        except Exception as e:
            self.tree.insert(parent, "end", text=f"[Error: {e}]", tags=("error",))

    # Expande recursivamente todos los nodos
    def expand_all(self):
        for item in self.tree.get_children():
            self.tree.item(item, open=True)
            self._expand_children(item)
        self._update_preview()

    def _expand_children(self, parent):
        for child in self.tree.get_children(parent):
            self.tree.item(child, open=True)
            self._expand_children(child)

    # Colapsa todos los nodos del TreeView
    def collapse_all(self):
        for item in self.tree.get_children():
            self.tree.item(item, open=False)
        self._update_preview()

    # Permite marcar o desmarcar todos los elementos, con opción de propagar a hijos
    def toggle_all(self, state, propagate=False):
        for item in self.tree.get_children():
            if item in self.tree_data:
                self.tree_data[item]["selected"] = state
                self.tree.set(item, "selected", "☑" if state else "☐")
                if propagate and "dir" in self.tree.item(item, "tags"):
                    self._update_children_state(item, state)
        self._update_preview()

    def _update_children_state(self, parent, state):
        for child in self.tree.get_children(parent):
            if child in self.tree_data:
                self.tree_data[child]["selected"] = state
                self.tree.set(child, "selected", "☑" if state else "☐")
                if "dir" in self.tree.item(child, "tags"):
                    self._update_children_state(child, state)

    # Al hacer doble clic se carga dinámicamente el contenido de los directorios no cargados
    def on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        data = self.tree_data.get(item)
        if data and os.path.isdir(data["path"]) and not data["loaded"]:
            try:
                self.tree.delete(*self.tree.get_children(item))
                self.populate_tree(item, data["path"])
                self.tree_data[item]["loaded"] = True
                self._update_preview()
            except Exception as e:
                logging.error(f"Error expandiendo directorio: {str(e)}")

    # Cambio de estado de la casilla (checkbox simulado) al hacer clic en la columna "selected"
    def on_checkbox_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            item = self.tree.identify_row(event.y)
            # La columna "selected" es la #2 (dado que "#0" es el árbol y "#1" es 'type')
            if column == "#2" and item in self.tree_data:
                current = self.tree_data[item]["selected"]
                new_state = not current
                self.tree_data[item]["selected"] = new_state
                self.tree.set(item, "selected", "☑" if new_state else "☐")
                self._update_preview()

    # Función para mapear la estructura en formato texto (estilo árbol)
    def mapear_estructura(self, dir_path, prefix=""):
        try:
            items = []
            # Se recorren los elementos en la carpeta (sin filtrar extensiones)
            for item in sorted(os.listdir(dir_path), key=lambda x: (not os.path.isdir(os.path.join(dir_path, x)), x.lower())):
                full_path = os.path.join(dir_path, item)
                # Se verifica el estado de selección mediante tree_data
                selected = any(rec["selected"] for rec in self.tree_data.values() if rec["path"] == full_path) or not any(rec["path"] == full_path for rec in self.tree_data.values())
                if not selected:
                    continue
                is_dir = os.path.isdir(full_path)
                items.append((item, is_dir))
            
            result = []
            for index, (name, is_dir) in enumerate(items):
                is_last = index == len(items) - 1
                line = "└── " if is_last else "├── "
                next_prefix = "    " if is_last else "│   "
                result.append(f"{prefix}{line}{'📁 ' if is_dir else '📄 '}{name}")
                if is_dir:
                    sub_result = self.mapear_estructura(os.path.join(dir_path, name), prefix + next_prefix)
                    if sub_result:
                        result.append(sub_result)
            return "\n".join(result)
        except Exception as e:
            return f"{prefix}[Error: {str(e)}]"

    # Inicia la generación de la estructura en un hilo separado
    def start_mapping(self):
        if not self.folder_path.get():
            self._update_status("¡Seleccione una carpeta primero!", "#D83B01")
            return
        self.generate_btn.config(state=tk.DISABLED)
        threading.Thread(target=self.generate_structure, daemon=True).start()

    # Genera el archivo TXT con la estructura mapeada
    def generate_structure(self):
        try:
            estructura = self.mapear_estructura(self.folder_path.get())
            output_name = f"{os.path.basename(self.folder_path.get())}-estructura.txt"
            output_path = os.path.join(self.folder_path.get(), output_name)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"ESTRUCTURA DE CARPETAS\n{'='*25}\n")
                f.write(f"Ruta: {self.folder_path.get()}\n")
                f.write(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
                f.write(estructura)
            
            self._update_status(f"Archivo generado: {output_path}", "#107C10")
            if messagebox.askyesno("Éxito", "¿Desea abrir el archivo generado?"):
                os.startfile(output_path)
        except Exception as e:
            self._update_status(f"Error: {str(e)}", "#D83B01")
            messagebox.showerror("Error", f"Error generando archivo:\n{str(e)}")
        finally:
            self.root.after(0, lambda: self.generate_btn.config(state=tk.NORMAL))

    # Actualiza la etiqueta de estado
    def _update_status(self, message, color):
        self.status_label.config(text=message, foreground=color)
        self.root.after(5000, lambda: self.status_label.config(text="Estado: Listo", foreground="#107C10"))

    # Actualiza la vista previa en el Text widget
    def _update_preview(self):
        preview = ""
        if self.folder_path.get():
            try:
                preview = self.mapear_estructura(self.folder_path.get())
            except Exception as e:
                preview = f"Error generando vista previa: {str(e)}"
        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert(tk.END, preview)
        self.preview_text.config(state="disabled")

# Función principal para iniciar la aplicación
def main():
    try:
        root = tk.Tk()
        app = EnhancedFolderMapper(root)
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")
        root.mainloop()
    except Exception as e:
        logging.critical(f"Error crítico: {str(e)}")
        messagebox.showerror("Error fatal", f"La aplicación ha fallado:\n{str(e)}")

if __name__ == "__main__":
    main()
