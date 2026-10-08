"""Núcleo de edición de PDF, independiente de la interfaz gráfica."""
from .document import Align, DocumentError, PdfDocument, TextDoesNotFit, TextSpan
from .fonts import FAMILIES, TextStyle

__all__ = ["Align", "DocumentError", "FAMILIES", "PdfDocument", "TextDoesNotFit", "TextSpan", "TextStyle"]
