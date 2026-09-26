"""Modelo de documento: todas las operaciones de edición sobre el PDF.

No depende de ninguna interfaz gráfica; las coordenadas están en puntos PDF
(1/72 de pulgada) con origen en la esquina superior izquierda de la página.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Iterator

import pymupdf

from .fonts import TextStyle, resolve_font, style_from_span
from .history import History, Snapshot

LINE_HEIGHT = 1.15
MIN_FONT_SIZE = 4.0
SHRINK_STEP = 0.5
# Fracción del alto de una línea que se ignora arriba y abajo al borrar, para no
# llevarse letras de las líneas vecinas.
ERASE_VERTICAL_MARGIN = 0.25


class DocumentError(Exception):
    """Error que se puede mostrar tal cual al usuario."""


class TextDoesNotFit(DocumentError):
    pass


class Align(IntEnum):
    LEFT = pymupdf.TEXT_ALIGN_LEFT
    CENTER = pymupdf.TEXT_ALIGN_CENTER
    RIGHT = pymupdf.TEXT_ALIGN_RIGHT
    JUSTIFY = pymupdf.TEXT_ALIGN_JUSTIFY


@dataclass(frozen=True)
class TextSpan:
    """Fragmento de texto existente con un único estilo."""
    text: str
    bbox: pymupdf.Rect
    origin: pymupdf.Point
    style: TextStyle


class PdfDocument:
    def __init__(self, doc: pymupdf.Document, path: Path | None = None) -> None:
        self._doc = doc
        self.path = path
        self.modified = False
        self.history = History()
        # Las páginas giradas complican las coordenadas: se enderezan sin cambiar su aspecto.
        for page in self._doc:
            if page.rotation:
                page.remove_rotation()

    # ------------------------------------------------------------------ archivo
    @classmethod
    def open(cls, path: str | Path) -> "PdfDocument":
        path = Path(path)
        try:
            doc = pymupdf.open(path)
        except Exception as exc:
            raise DocumentError(f"No se pudo abrir «{path.name}»:\n{exc}") from exc
        if not doc.is_pdf:
            raise DocumentError(f"«{path.name}» no es un PDF.")
        if doc.needs_pass:
            raise DocumentError(f"«{path.name}» está protegido con contraseña.")
        return cls(doc, path)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        data = self._doc.tobytes(garbage=3, deflate=True)
        try:
            path.write_bytes(data)
        except OSError as exc:
            raise DocumentError(f"No se pudo guardar en «{path}»:\n{exc}") from exc
        self.path = path
        self.modified = False

    @property
    def page_count(self) -> int:
        return len(self._doc)

    def page_rect(self, page_no: int) -> pymupdf.Rect:
        return self._doc[page_no].rect

    def render_png(self, page_no: int, zoom: float) -> bytes:
        pix = self._doc[page_no].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        return pix.tobytes("png")

    def text(self, page_no: int) -> str:
        return self._doc[page_no].get_text()

    # ------------------------------------------------------------------ consulta
    def span_at(self, page_no: int, point: pymupdf.Point) -> TextSpan | None:
        """Devuelve el fragmento de texto visible bajo el punto, si lo hay."""
        for block in self._doc[page_no].get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    bbox = pymupdf.Rect(span["bbox"])
                    if span["text"].strip() and bbox.contains(point):
                        style = style_from_span(span["font"], span["flags"], span["size"], span["color"])
                        return TextSpan(span["text"], bbox, pymupdf.Point(span["origin"]), style)
        return None

    # ------------------------------------------------------------------ edición
    def insert_text(self, page_no: int, top_left: pymupdf.Point, text: str, style: TextStyle) -> None:
        """Escribe texto (una o varias líneas) con su esquina superior izquierda en top_left."""
        baseline = pymupdf.Point(top_left.x, top_left.y + style.size * 0.8)
        with self._edit(page_no):
            self._insert_at_baseline(self._doc[page_no], baseline, text, style)

    def insert_textbox(self, page_no: int, rect: pymupdf.Rect, text: str, style: TextStyle,
                       align: Align = Align.LEFT) -> float:
        """Escribe texto con ajuste de línea dentro de rect.

        Si no cabe, reduce la letra hasta MIN_FONT_SIZE. Devuelve el tamaño usado.
        """
        fontname, fontfile = resolve_font(style)
        size = style.size
        with self._edit(page_no):
            page = self._doc[page_no]
            while size >= MIN_FONT_SIZE:
                # insert_textbox no escribe nada si el texto no cabe (devuelve < 0).
                leftover = page.insert_textbox(rect, text, fontsize=size, fontname=fontname,
                                               fontfile=fontfile, color=style.color, align=int(align),
                                               lineheight=LINE_HEIGHT)
                if leftover >= 0:
                    return size
                size -= SHRINK_STEP
            raise TextDoesNotFit("El texto no cabe en el cuadro. Dibuja un cuadro más grande.")

    def replace_span(self, page_no: int, span: TextSpan, text: str, style: TextStyle) -> None:
        """Sustituye un fragmento existente, empezando donde empezaba su texto visible."""
        origin = pymupdf.Point(span.origin)
        leading = span.text[:len(span.text) - len(span.text.lstrip())]
        if leading:
            origin.x += pymupdf.get_text_length(leading, fontsize=span.style.size)
        with self._edit(page_no):
            page = self._doc[page_no]
            self._redact(page, [span.bbox])
            self._insert_at_baseline(page, origin, text, style)

    def erase(self, page_no: int, rect: pymupdf.Rect) -> None:
        """Elimina el texto dentro de rect sin tocar imágenes, líneas ni fondos."""
        with self._edit(page_no):
            self._redact(self._doc[page_no], [rect])

    # ------------------------------------------------------------------ historial
    def undo(self) -> int | None:
        """Deshace el último cambio y devuelve la página donde ocurrió."""
        return self._restore(self.history.undo(self._doc.tobytes()))

    def redo(self) -> int | None:
        return self._restore(self.history.redo(self._doc.tobytes()))

    # ------------------------------------------------------------------ interno
    def _restore(self, snapshot: Snapshot | None) -> int | None:
        if snapshot is None:
            return None
        self._doc = pymupdf.open("pdf", snapshot.data)
        self.modified = True
        return snapshot.page

    @contextmanager
    def _edit(self, page_no: int) -> Iterator[None]:
        """Agrupa una edición: guarda el estado previo y lo restaura si algo falla."""
        was_modified = self.modified
        self.history.push(Snapshot(self._doc.tobytes(), page_no))
        try:
            yield
        except Exception:
            self._restore(self.history.discard_last())
            self.modified = was_modified
            raise
        self.modified = True

    @staticmethod
    def _insert_at_baseline(page: pymupdf.Page, baseline: pymupdf.Point, text: str,
                            style: TextStyle) -> None:
        fontname, fontfile = resolve_font(style)
        page.insert_text(baseline, text, fontsize=style.size, fontname=fontname,
                         fontfile=fontfile, color=style.color, lineheight=LINE_HEIGHT)

    @staticmethod
    def _redact(page: pymupdf.Page, rects: list[pymupdf.Rect]) -> None:
        for rect in rects:
            margin = rect.height * ERASE_VERTICAL_MARGIN
            page.add_redact_annot(pymupdf.Rect(rect.x0 + 0.5, rect.y0 + margin,
                                               rect.x1 - 0.5, rect.y1 - margin), fill=False)
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE,
                              graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
