"""Ventana principal: barra de herramientas, gestión de archivos y despacho de herramientas."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pymupdf

from .. import __version__
from ..core import DocumentError, PdfDocument, TextStyle
from .page_view import PageView
from .text_dialog import TextDialog
from .tools import Tool

ZOOM_STEP = 1.25


class MainWindow(tk.Tk):
    def __init__(self, path: Path | None = None) -> None:
        super().__init__()
        self.title("Editor PDF")
        self.geometry("1100x850")

        self.document: PdfDocument | None = None
        self.page_no = 0
        self.style = TextStyle()  # último estilo usado, se reutiliza en el siguiente texto
        self.tool = tk.StringVar(value=Tool.WRITE.name)
        self._drag_start: pymupdf.Point | None = None

        self._build_toolbar()
        self.view = PageView(self)
        self.view.pack(fill="both", expand=True)
        self.status = ttk.Label(self, relief="sunken", anchor="w", padding=(6, 2))
        self.status.pack(fill="x")
        self._bind_events()
        self._on_tool_change()

        self.protocol("WM_DELETE_WINDOW", self.quit_app)
        if path:
            self.open(path)

    # ------------------------------------------------------------------ construcción
    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self, padding=4)
        bar.pack(fill="x")

        def button(text, command, width=None, padx=0):
            ttk.Button(bar, text=text, command=command, width=width).pack(side="left", padx=padx)

        def separator():
            ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)

        button("Abrir", self.open)
        button("Guardar", self.save, padx=2)
        button("Guardar como", self.save_as)
        separator()
        button("↶ Deshacer", self.undo)
        button("↷ Rehacer", self.redo, padx=2)
        separator()
        for tool in Tool:
            ttk.Radiobutton(bar, text=tool.label, value=tool.name, variable=self.tool,
                            command=self._on_tool_change).pack(side="left", padx=2)
        separator()
        button("◀", lambda: self.go_to(self.page_no - 1), width=3)
        self.page_label = ttk.Label(bar, text="- / -", width=9, anchor="center")
        self.page_label.pack(side="left")
        button("▶", lambda: self.go_to(self.page_no + 1), width=3)
        button("−", lambda: self.zoom(1 / ZOOM_STEP), width=3, padx=(8, 0))
        button("+", lambda: self.zoom(ZOOM_STEP), width=3)

    def _bind_events(self) -> None:
        canvas = self.view.canvas
        canvas.bind("<ButtonPress-1>", self._on_press)
        canvas.bind("<B1-Motion>", self._on_drag)
        canvas.bind("<ButtonRelease-1>", self._on_release)
        canvas.bind("<Motion>", self._on_motion)
        shortcuts = {
            "<Control-o>": self.open, "<Control-s>": self.save, "<Control-S>": self.save_as,
            "<Control-z>": self.undo, "<Control-y>": self.redo,
            "<Prior>": lambda: self.go_to(self.page_no - 1), "<Next>": lambda: self.go_to(self.page_no + 1),
            "<Control-plus>": lambda: self.zoom(ZOOM_STEP), "<Control-minus>": lambda: self.zoom(1 / ZOOM_STEP),
        }
        for sequence, action in shortcuts.items():
            self.bind(sequence, lambda _e, action=action: action())

    @property
    def current_tool(self) -> Tool:
        return Tool[self.tool.get()]

    def _on_tool_change(self) -> None:
        self.view.canvas.configure(cursor=self.current_tool.cursor)
        self.view.highlight(None)
        self.set_status(self.current_tool.help)

    def set_status(self, text: str) -> None:
        self.status.configure(text=text)

    def _error(self, exc: Exception) -> None:
        messagebox.showerror("Editor PDF", str(exc), parent=self)

    # ------------------------------------------------------------------ archivo
    def open(self, path: Path | str | None = None) -> None:
        if not self._confirm_discard():
            return
        path = path or filedialog.askopenfilename(filetypes=[("PDF", "*.pdf *.PDF"), ("Todos", "*")])
        if not path:
            return
        try:
            self.document = PdfDocument.open(path)
        except DocumentError as exc:
            return self._error(exc)
        self.page_no = 0
        self.refresh()
        self.view.scroll_top()

    def save(self) -> None:
        doc = self.document
        if not doc:
            return
        if doc.path is None or not messagebox.askyesno(
                "Guardar", f"¿Sobrescribir el archivo original?\n{doc.path}\n\n"
                           "(Elige «No» para guardar una copia)", parent=self):
            return self.save_as()
        self._write(doc.path)

    def save_as(self) -> None:
        doc = self.document
        if not doc:
            return
        folder = doc.path.parent if doc.path else Path.home()
        stem = doc.path.stem if doc.path else "documento"
        target = filedialog.asksaveasfilename(defaultextension=".pdf", initialdir=folder,
                                              initialfile=f"{stem}_editado.pdf", filetypes=[("PDF", "*.pdf")])
        if target:
            self._write(Path(target))

    def _write(self, path: Path) -> None:
        try:
            self.document.save(path)
        except DocumentError as exc:
            return self._error(exc)
        self._update_title()
        self.set_status(f"Guardado en {path}")

    def _confirm_discard(self) -> bool:
        """True si se puede cerrar el documento actual (no hay cambios o el usuario decide)."""
        if not (self.document and self.document.modified):
            return True
        answer = messagebox.askyesnocancel("Cambios sin guardar", "¿Guardar los cambios antes de continuar?",
                                           parent=self)
        if answer is None:
            return False
        if answer:
            self.save_as()
            return not self.document.modified
        return True

    def quit_app(self) -> None:
        if self._confirm_discard():
            self.destroy()

    # ------------------------------------------------------------------ vista
    def refresh(self) -> None:
        self._update_title()
        if not self.document:
            self.view.clear()
            return
        self.view.show(self.document.render_png(self.page_no, self.view.zoom))
        self.page_label.configure(text=f"{self.page_no + 1} / {self.document.page_count}")

    def _update_title(self) -> None:
        doc = self.document
        name = doc.path.name if doc and doc.path else ""
        mark = "* " if doc and doc.modified else ""
        self.title(f"{mark}{name} — Editor PDF {__version__}")

    def go_to(self, page_no: int) -> None:
        if self.document and 0 <= page_no < self.document.page_count:
            self.page_no = page_no
            self.refresh()
            self.view.scroll_top()

    def zoom(self, factor: float) -> None:
        self.view.scale_zoom(factor)
        self.refresh()

    def undo(self) -> None:
        self._after_history(self.document and self.document.undo())

    def redo(self) -> None:
        self._after_history(self.document and self.document.redo())

    def _after_history(self, page_no: int | None) -> None:
        if page_no is not None:
            self.page_no = min(page_no, self.document.page_count - 1)
            self.refresh()

    # ------------------------------------------------------------------ ratón
    def _on_press(self, event: tk.Event) -> None:
        if self.document:
            self._drag_start = self.view.to_pdf(event)

    def _on_drag(self, event: tk.Event) -> None:
        if self._drag_start is None or self.current_tool is Tool.REPLACE:
            return
        color = "#d33" if self.current_tool is Tool.ERASE else "#27f"
        self.view.draw_selection(pymupdf.Rect(self._drag_start, self.view.to_pdf(event)).normalize(), color)

    def _on_release(self, event: tk.Event) -> None:
        if self._drag_start is None:
            return
        end = self.view.to_pdf(event)
        rect = pymupdf.Rect(self._drag_start, end).normalize()
        self._drag_start = None
        self.view.clear_selection()

        tool, dragged = self.current_tool, self.view.is_drag(rect)
        if tool is Tool.WRITE and dragged:
            self._write_textbox(rect)
        elif tool is Tool.WRITE:
            self._write_text(end)
        elif tool is Tool.REPLACE:
            self._replace_text(end)
        elif tool is Tool.ERASE and dragged:
            self._erase(rect)

    def _on_motion(self, event: tk.Event) -> None:
        if self.document and self.current_tool is Tool.REPLACE:
            span = self.document.span_at(self.page_no, self.view.to_pdf(event))
            self.view.highlight(span.bbox if span else None)

    # ------------------------------------------------------------------ acciones
    def _ask_text(self, title: str, style: TextStyle | None = None, text: str = "", show_align: bool = False):
        result = TextDialog.ask(self, title, style or self.style, text, show_align)
        if result:
            self.style = result.style
        return result

    def _write_text(self, point: pymupdf.Point) -> None:
        result = self._ask_text("Escribir texto")
        if result:
            self.document.insert_text(self.page_no, point, result.text, result.style)
            self.refresh()

    def _write_textbox(self, rect: pymupdf.Rect) -> None:
        result = self._ask_text("Cuadro de texto", show_align=True)
        if not result:
            return
        try:
            size = self.document.insert_textbox(self.page_no, rect, result.text, result.style, result.align)
        except DocumentError as exc:
            return self._error(exc)
        self.refresh()
        if size != result.style.size:
            self.set_status(f"El texto se redujo a {size:g} pt para que cupiera en el cuadro.")

    def _replace_text(self, point: pymupdf.Point) -> None:
        span = self.document.span_at(self.page_no, point)
        if not span:
            return
        original = span.text.strip()
        result = self._ask_text(f"Reemplazar «{original[:50]}»", style=span.style, text=original)
        if result:
            self.document.replace_span(self.page_no, span, result.text, result.style)
            self.refresh()

    def _erase(self, rect: pymupdf.Rect) -> None:
        if messagebox.askyesno("Borrar", "¿Borrar el texto dentro del rectángulo?", parent=self):
            self.document.erase(self.page_no, rect)
            self.refresh()
