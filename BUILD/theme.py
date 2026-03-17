import os
from db import *
import tkinter as tk
from tkinter import ttk
from settings import THEME_FILE
import json

THEME = None
THEMES = None
THEMELIST = None

def load_themes(settings):
    global THEMES, THEME, THEMELIST
    if not os.path.exists(THEME_FILE):
        raise RuntimeError("themes.json missing.")
    with open(THEME_FILE, 'r') as f:
        THEMES = json.load(f)
    THEMELIST = THEMES.keys()
    THEME = THEMES[settings.get("theme", "Deep Blue")]

def set_theme(name):
    global THEME
    THEME = THEMES[name]

def apply_ttk_theme(root):
    style = ttk.Style(root)

    style.theme_use("default")

    style.configure(
        "Dragonbooru.TCombobox",
        fieldbackground=THEME["bg_highlight"],
        background=THEME["accent"],
        foreground=THEME["text_primary"],
        arrowcolor=THEME["text_primary"]
    )

    style.map(
        "Dragonbooru.TCombobox",
        fieldbackground=[("readonly", THEME["bg_highlight"])],
        selectbackground=[("readonly", THEME["selected"])],
        selectforeground=[("readonly", THEME["text_primary_selected"])]
    )

class ThemedCombobox(ttk.Combobox):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("style", "Dragonbooru.TCombobox")
        super().__init__(*args, **kwargs)

class ThemedFrame(tk.Frame):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("bg", THEME["bg"])
        super().__init__(*args, **kwargs)

class ThemedLabel(tk.Label):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("bg", THEME["bg"])
        kwargs.setdefault("fg", THEME["text_primary"])
        super().__init__(*args, **kwargs)

class ThemedButton(tk.Button):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("bg", THEME["accent"])
        kwargs.setdefault("fg", THEME["text_primary"])
        kwargs.setdefault("activebackground", THEME["selected"])
        kwargs.setdefault("activeforeground", THEME["text_primary_selected"])
        kwargs.setdefault("relief", "flat")
        kwargs.setdefault("borderwidth", 0)
        super().__init__(*args, **kwargs)

class ThemedEntry(tk.Entry):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("bg", THEME["bg_highlight"])
        kwargs.setdefault("fg", THEME["text_primary"])
        kwargs.setdefault("insertbackground", THEME["text_primary"])
        kwargs.setdefault("relief", "flat")
        super().__init__(*args, **kwargs)

class ThemedListbox(tk.Listbox):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("bg", THEME["bg_highlight"])
        kwargs.setdefault("fg", THEME["text_primary"])
        kwargs.setdefault("selectbackground", THEME["selected"])
        kwargs.setdefault("selectforeground", THEME["text_primary_selected"])
        kwargs.setdefault("relief", "flat")
        super().__init__(*args, **kwargs)

class ThemedCanvas(tk.Canvas):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("bg", THEME["bg"])
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(*args, **kwargs)

class ThemedSpinbox(tk.Spinbox):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("bg", THEME["bg_highlight"])
        kwargs.setdefault("fg", THEME["text_primary"])
        kwargs.setdefault("insertbackground", THEME["text_primary"])
        kwargs.setdefault("buttonbackground", THEME["accent"])
        kwargs.setdefault("activebackground", THEME["selected"])
        kwargs.setdefault("relief", "flat")
        super().__init__(*args, **kwargs)

# Apply automatically
tk.Frame = ThemedFrame
tk.Label = ThemedLabel
tk.Button = ThemedButton
tk.Entry = ThemedEntry
tk.Listbox = ThemedListbox
tk.Canvas = ThemedCanvas
tk.Spinbox = ThemedSpinbox
ttk.Combobox = ThemedCombobox
