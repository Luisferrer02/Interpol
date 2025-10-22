import json
import tkinter as tk
from tkinter import messagebox
from urllib.request import urlopen
from PIL import Image, ImageTk
import io
import os

INPUT_PATH = r"players.txt"
OUTPUT_PATH = r"players_labeled.json"

# Cargar datos
with open(INPUT_PATH, "r", encoding="utf-8-sig") as f:
    players = json.load(f)

# Cargar datos previos si existen
if os.path.exists(OUTPUT_PATH):
    with open(OUTPUT_PATH, "r", encoding="utf-8-sig") as f:
        labeled = json.load(f)
    labeled_ids = {p["Name"]: p for p in labeled}
else:
    labeled = []
    labeled_ids = {}

# Filtrar jugadores aún no clasificados
players = [p for p in players if "Status" not in p and p["Name"] not in labeled_ids]

index = 0

def show_player():
    global index
    if index >= len(players):
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(labeled, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("Fin", f"Completado. Guardado en:\n{OUTPUT_PATH}")
        root.destroy()
        return

    player = players[index]
    label_name.config(text=f"{player['Name']} - {player['Team']}")
    try:
        image_bytes = urlopen(player["Photo"]).read()
        img = Image.open(io.BytesIO(image_bytes))
        img = img.resize((200, 200))
        photo = ImageTk.PhotoImage(img)
        label_photo.config(image=photo, text="")
        label_photo.image = photo
    except Exception:
        label_photo.config(image="", text="(sin imagen)")

def mark(status):
    global index
    player = players[index]
    player["Status"] = status
    labeled.append(player)
    index += 1
    # Guardar progreso incremental
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(labeled, f, ensure_ascii=False, indent=2)
    show_player()

root = tk.Tk()
root.title("Clasificador de Jugadores")

label_name = tk.Label(root, text="", font=("Arial", 14))
label_name.pack(pady=10)

label_photo = tk.Label(root)
label_photo.pack(pady=10)

frame_buttons = tk.Frame(root)
frame_buttons.pack(pady=20)

btn_bufon = tk.Button(frame_buttons, text="Bufón", width=10, bg="#ff6666", command=lambda: mark("bufon"))
btn_bufon.grid(row=0, column=0, padx=10)

btn_leyenda = tk.Button(frame_buttons, text="Leyenda", width=10, bg="#66cc66", command=lambda: mark("leyenda"))
btn_leyenda.grid(row=0, column=1, padx=10)

btn_camiseta = tk.Button(frame_buttons, text="Camiseta", width=10, bg="#6699ff", command=lambda: mark("camiseta"))
btn_camiseta.grid(row=0, column=2, padx=10)

show_player()
root.mainloop()
