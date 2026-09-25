"""Lienzo que muestra una página del PDF y traduce coordenadas pantalla <-> PDF."""
from __future__ import annotations

import base64
import tkinter as tk
from tkinter import ttk

import pymupdf

ZOOM_MIN, ZOOM_MAX = 0.5, 5.0
DRAG_THRESHOLD = 8  # puntos PDF: por debajo se considera un clic, no un arrastre


class PageView(ttk.Frame):
    def __init__(self, parent: tk.Misc, zoom: float = 1.5) -> None:
        super().__init__(parent)
        self.zoom = zoom
        self._image: tk.PhotoImage | None = None
        self._selection: int | None = None
        self._highlight: int | None = None

        self.canvas = tk.Canvas(self, bg="#6b6b6b", highlightthickness=0)
        vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        hbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        vbar.pack(side="right", fill="y")
        hbar.pack(side="bottom", fill="x")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Button-4>", lambda _e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind("<Button-5>", lambda _e: self.canvas.yview_scroll(3, "units"))
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-e.delta // 40, "units"))

    # ------------------------------------------------------------------ imagen
    def show(self, png: bytes) -> None:
        self.canvas.delete("all")
        self._selection = self._highlight = None
        self._image = tk.PhotoImage(data=base64.b64encode(png))
        self.canvas.create_image(0, 0, image=self._image, anchor="nw")
        self.canvas.configure(scrollregion=(0, 0, self._image.width(), self._image.height()))

    def clear(self) -> None:
        self.canvas.delete("all")
        self._image = None

    def scroll_top(self) -> None:
        self.canvas.yview_moveto(0)

    def scale_zoom(self, factor: float) -> None:
        self.zoom = max(ZOOM_MIN, min(ZOOM_MAX, self.zoom * factor))

    # ------------------------------------------------------------------ coordenadas
    def to_pdf(self, event: tk.Event) -> pymupdf.Point:
        return pymupdf.Point(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)) / self.zoom

    def _to_canvas(self, rect: pymupdf.Rect) -> tuple[float, float, float, float]:
        r = rect * self.zoom
        return r.x0, r.y0, r.x1, r.y1

    @staticmethod
    def is_drag(rect: pymupdf.Rect) -> bool:
        return rect.width > DRAG_THRESHOLD and rect.height > DRAG_THRESHOLD

    # ------------------------------------------------------------------ superposiciones
    def draw_selection(self, rect: pymupdf.Rect, color: str) -> None:
        """Rectángulo punteado mientras el usuario arrastra."""
        if self._selection is None:
            self._selection = self.canvas.create_rectangle(*self._to_canvas(rect), outline=color,
                                                           width=2, dash=(4, 2))
        else:
            self.canvas.coords(self._selection, *self._to_canvas(rect))

    def clear_selection(self) -> None:
        if self._selection is not None:
            self.canvas.delete(self._selection)
            self._selection = None

    def highlight(self, rect: pymupdf.Rect | None) -> None:
        """Resalta el texto bajo el ratón (herramienta Reemplazar)."""
        if self._highlight is not None:
            self.canvas.delete(self._highlight)
            self._highlight = None
        if rect is not None:
            self._highlight = self.canvas.create_rectangle(*self._to_canvas(rect), outline="#27f", width=2)
