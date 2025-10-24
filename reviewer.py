import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import json
import io
import requests
import os
import threading

# --- CONFIGURACIÓN ---
DATA_FILE = "players_labeled.json"  # lectura y escritura directa


def load_data():
    if not os.path.exists(DATA_FILE):
        messagebox.showerror("Error", f"No se encontró {DATA_FILE}")
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Normalizar claves: algunos ficheros usan "Status" con mayúscula.
    for p in data:
        # preferir 'status' en minúsculas en toda la aplicación
        if "status" not in p and "Status" in p:
            p["status"] = p.pop("Status")

    return data


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class ReviewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Player Review")
        self.root.geometry("540x640")

        self.data = load_data()
        self.filtered = []
        self.index = 0
        # image cache to avoid re-downloading repeatedly
        self._image_cache = {}
        # batching saves to avoid costly disk I/O on every change
        self._unsaved_changes = 0
        self._save_threshold = 5
        self._dirty = False

        self.mode_var = tk.StringVar(value="unreviewed")
        self.hide_tag = tk.BooleanVar(value=False)
        self.filters = {
            "bufon": tk.BooleanVar(value=False),
            "leyenda": tk.BooleanVar(value=False),
            "camiseta": tk.BooleanVar(value=False)
        }

        self.setup_mode_screen()

    # --- PANTALLA DE MODO ---
    def setup_mode_screen(self):
        self.clear_screen()
        tk.Label(self.root, text="Selecciona modo de revisión", font=("Arial", 14, "bold")).pack(pady=20)

        tk.Radiobutton(self.root, text="Revisar nuevos", variable=self.mode_var, value="unreviewed").pack(anchor="w", padx=40)
        tk.Radiobutton(self.root, text="Ver revisados", variable=self.mode_var, value="reviewed").pack(anchor="w", padx=40)

        tk.Button(self.root, text="Continuar", command=self.setup_filter_screen).pack(pady=30)

    # --- PANTALLA DE FILTROS ---
    def setup_filter_screen(self):
        self.clear_screen()
        mode = self.mode_var.get()

        tk.Label(self.root, text=f"Modo: {mode}", font=("Arial", 12, "bold")).pack(pady=10)
        tk.Label(self.root, text="Filtrar por etiquetas:").pack()

        for label, var in self.filters.items():
            tk.Checkbutton(self.root, text=label.capitalize(), variable=var).pack(anchor="w", padx=40)

        tk.Checkbutton(self.root, text="Ocultar etiquetas actuales", variable=self.hide_tag).pack(pady=10)
        tk.Button(self.root, text="Iniciar revisión", command=self.start_review).pack(pady=20)
        tk.Button(self.root, text="Volver", command=self.setup_mode_screen).pack(pady=5)

    # --- CARGAR DATOS SEGÚN FILTROS ---
    def start_review(self):
        mode = self.mode_var.get()
        active_filters = [k for k, v in self.filters.items() if v.get()]

        if mode == "reviewed":
            self.filtered = [p for p in self.data if "confirmed" in p]
        else:
            self.filtered = [p for p in self.data if "confirmed" not in p]

        if active_filters:
            self.filtered = [p for p in self.filtered if p.get("status") in active_filters]

        if not self.filtered:
            messagebox.showinfo("Sin datos", "No hay jugadores que coincidan con los filtros.")
            return

        self.index = 0
        self.show_player()

    # --- MOSTRAR UN JUGADOR ---
    def show_player(self):
        self.clear_screen()

        if not self.filtered:
            messagebox.showinfo("Sin jugadores", "No hay jugadores para mostrar.")
            self.setup_mode_screen()
            return

        player = self.filtered[self.index]

        tk.Label(self.root, text=f"{player['Name']}", font=("Arial", 16, "bold")).pack(pady=5)
        tk.Label(self.root, text=f"Equipo: {player['Team']}", font=("Arial", 12)).pack(pady=5)

        if not self.hide_tag.get():
            status = player.get("status", "Sin etiqueta")
            tk.Label(self.root, text=f"Etiqueta actual: {status}", fg="blue", font=("Arial", 11, "italic")).pack(pady=3)

        if "confirmed" in player:
            conf_color = "green" if player["confirmed"] else "red"
            conf_text = f"Confirmado: {player['confirmed']}"
            tk.Label(self.root, text=conf_text, fg=conf_color).pack()

        img_label = tk.Label(self.root)
        img_label.pack(pady=10)
        # non-blocking photo load with cache
        self.display_photo(player.get("Photo"), img_label)

        # Botones de etiquetado
        tk.Button(self.root, text="Bufón", width=12, command=lambda: self.update_label("bufon")).pack(pady=3)
        tk.Button(self.root, text="Leyenda", width=12, command=lambda: self.update_label("leyenda")).pack(pady=3)
        tk.Button(self.root, text="Camiseta", width=12, command=lambda: self.update_label("camiseta")).pack(pady=3)

        # Navegación
        tk.Frame(self.root, height=20).pack()
        nav = tk.Frame(self.root)
        nav.pack(pady=5)
        tk.Button(nav, text="← Anterior", width=12, command=self.prev_player).grid(row=0, column=0, padx=5)
        tk.Button(nav, text="Siguiente →", width=12, command=self.next_player).grid(row=0, column=1, padx=5)
        tk.Button(self.root, text="Volver al menú", command=self.setup_mode_screen).pack(pady=10)

        tk.Label(self.root, text=f"Jugador {self.index + 1} de {len(self.filtered)}", font=("Arial", 9)).pack(pady=5)

    # --- DESCARGA Y MUESTRA DE FOTO ---
    def display_photo(self, url, label):
        # If no URL provided, show placeholder
        if not url:
            label.config(text="[Foto no disponible]")
            return

        # use cached PhotoImage if available
        if url in self._image_cache:
            photo = self._image_cache[url]
            label.config(image=photo)
            label.image = photo
            return

        # show temporary text and download image in background thread
        label.config(text="Cargando foto...")

        def _fetch():
            try:
                resp = requests.get(url, timeout=5)
                img = Image.open(io.BytesIO(resp.content))
                img = img.resize((200, 200))
                photo = ImageTk.PhotoImage(img)
                # store in cache and set on main thread
                self._image_cache[url] = photo
                def _set():
                    label.config(image=photo, text="")
                    label.image = photo
                self.root.after(0, _set)
            except Exception:
                def _err():
                    label.config(text="[Foto no disponible]")
                self.root.after(0, _err)

        threading.Thread(target=_fetch, daemon=True).start()

    # --- ACTUALIZAR ETIQUETA ---
    def update_label(self, new_label):
        player = self.filtered[self.index]
        current_label = player.get("status")

        # Do NOT change or add a 'status' field in the JSON
        # Only set 'confirmed' when the player already had a status
        if current_label:
            if current_label == new_label:
                player["confirmed"] = True
            else:
                # had a different label, mark as mismatch
                player["confirmed"] = False
            # mark dirty and occasionally flush to disk to avoid IO spikes
            self._dirty = True
            self._unsaved_changes += 1
            if self._unsaved_changes >= self._save_threshold:
                save_data(self.data)
                self._unsaved_changes = 0
                self._dirty = False

        # if current_label is None/empty, user pressed a label for an untagged player:
        # do NOT add any 'confirmed' field (per spec)

        # move to next player without writing to disk on every click
        self.next_player()

    # --- NAVEGACIÓN ENTRE JUGADORES ---
    def next_player(self):
        if self.index < len(self.filtered) - 1:
            self.index += 1
            self.show_player()
        else:
            messagebox.showinfo("Fin", "No hay más jugadores.")
            # Save any pending changes when finishing
            if self._dirty or self._unsaved_changes > 0:
                save_data(self.data)
                self._unsaved_changes = 0
                self._dirty = False

    def prev_player(self):
        if self.index > 0:
            self.index -= 1
            self.show_player()
        else:
            messagebox.showinfo("Inicio", "Este es el primer jugador.")

    # --- LIMPIAR PANTALLA ---
    def clear_screen(self):
        for w in self.root.winfo_children():
            w.destroy()

    def on_close(self):
        # ensure pending changes are saved
        if self._dirty or self._unsaved_changes > 0:
            save_data(self.data)
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ReviewApp(root)
    # save pending changes on normal window close
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
