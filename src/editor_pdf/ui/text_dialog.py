"""Diálogo modal para escribir texto y elegir su estilo."""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import colorchooser, messagebox, ttk

from ..core import FAMILIES, Align, TextStyle
from ..core.fonts import hex_to_rgb, rgb_to_hex

ALIGN_LABELS = {"Izquierda": Align.LEFT, "Centro": Align.CENTER,
                "Derecha": Align.RIGHT, "Justificado": Align.JUSTIFY}


@dataclass(frozen=True)
class TextInput:
    text: str
    style: TextStyle
    align: Align


class TextDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, title: str, style: TextStyle, text: str = "",
                 show_align: bool = False) -> None:
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.result: TextInput | None = None
        self._color = style.color
        self._build(style, text, show_align)

        self.bind("<Control-Return>", lambda _e: self._accept())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.text.focus_set()
        self.text.tag_add("sel", "1.0", "end")

    @classmethod
    def ask(cls, parent: tk.Misc, title: str, style: TextStyle, text: str = "",
            show_align: bool = False) -> TextInput | None:
        """Muestra el diálogo y espera. Devuelve None si se cancela o el texto está vacío."""
        dialog = cls(parent, title, style, text, show_align)
        dialog.wait_visibility()
        dialog.grab_set()
        parent.wait_window(dialog)
        return dialog.result

    def _build(self, style: TextStyle, text: str, show_align: bool) -> None:
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(5, weight=1)
        frame.rowconfigure(0, weight=1)

        self.text = tk.Text(frame, width=60, height=6, wrap="word", font=("Sans", 11), undo=True)
        self.text.insert("1.0", text)
        self.text.grid(row=0, column=0, columnspan=6, sticky="nsew", pady=(0, 8))

        ttk.Label(frame, text="Fuente:").grid(row=1, column=0, sticky="w")
        self.family = ttk.Combobox(frame, values=list(FAMILIES), state="readonly", width=24)
        self.family.set(style.family)
        self.family.grid(row=1, column=1, sticky="w")

        ttk.Label(frame, text="Tamaño:").grid(row=1, column=2, sticky="e", padx=(10, 2))
        self.size = tk.StringVar(value=f"{style.size:g}")
        ttk.Spinbox(frame, from_=4, to=96, increment=0.5, textvariable=self.size, width=6).grid(
            row=1, column=3, sticky="w")

        self.bold = tk.BooleanVar(value=style.bold)
        self.italic = tk.BooleanVar(value=style.italic)
        ttk.Checkbutton(frame, text="Negrita", variable=self.bold).grid(row=2, column=0, sticky="w")
        ttk.Checkbutton(frame, text="Cursiva", variable=self.italic).grid(row=2, column=1, sticky="w")

        self.color_button = tk.Button(frame, text="Color", width=8, command=self._pick_color)
        self.color_button.grid(row=2, column=2, columnspan=2, sticky="w", padx=(10, 0))
        self._paint_color_button()

        self.align = tk.StringVar(value="Izquierda")
        if show_align:
            ttk.Label(frame, text="Alinear:").grid(row=3, column=0, sticky="w", pady=(6, 0))
            ttk.Combobox(frame, textvariable=self.align, state="readonly", width=12,
                         values=list(ALIGN_LABELS)).grid(row=3, column=1, sticky="w", pady=(6, 0))

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=6, sticky="e", pady=(10, 0))
        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Aceptar (Ctrl+Enter)", command=self._accept).pack(side="right", padx=6)

    def _paint_color_button(self) -> None:
        dark = sum(self._color) < 1.5
        self.color_button.configure(bg=rgb_to_hex(self._color), fg="white" if dark else "black")

    def _pick_color(self) -> None:
        _rgb, hex_value = colorchooser.askcolor(color=rgb_to_hex(self._color), parent=self)
        if hex_value:
            self._color = hex_to_rgb(hex_value)
            self._paint_color_button()

    def _accept(self) -> None:
        text = self.text.get("1.0", "end-1c")
        try:
            size = float(self.size.get().replace(",", "."))
        except ValueError:
            size = 0
        if not 1 <= size <= 400:
            messagebox.showerror("Tamaño", "El tamaño de letra no es válido.", parent=self)
            return
        if text.strip():
            style = TextStyle(self.family.get(), size, self.bold.get(), self.italic.get(), self._color)
            self.result = TextInput(text, style, ALIGN_LABELS[self.align.get()])
        self.destroy()
