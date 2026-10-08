"""Herramientas (modos de edición) disponibles en la barra superior."""
from __future__ import annotations

from enum import Enum


class Tool(Enum):
    # valor = (etiqueta, cursor, ayuda para la barra de estado)
    WRITE = ("Escribir texto", "xterm",
             "Clic: escribir en ese punto  ·  Arrastrar: cuadro de texto con ajuste de línea")
    REPLACE = ("Reemplazar texto", "hand2",
               "Pasa el ratón sobre un texto (se marca en azul) y haz clic para cambiarlo")
    ERASE = ("Borrar zona", "crosshair",
             "Arrastra un rectángulo: se borra el texto dentro (el diseño se conserva)")

    @property
    def label(self) -> str:
        return self.value[0]

    @property
    def cursor(self) -> str:
        return self.value[1]

    @property
    def help(self) -> str:
        return self.value[2]
