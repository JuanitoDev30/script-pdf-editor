"""Estilos de texto y selección de fuentes.

Se usan fuentes libres con las mismas medidas que las de Microsoft Office, de modo
que el texto nuevo ocupe el mismo espacio que el original. Si una fuente no está
instalada se recurre a las fuentes base de PDF (Helvetica, Times, Courier).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

FONT_DIRS = (Path("/usr/share/fonts/truetype"), Path.home() / ".local/share/fonts")

# Nombre visible -> (ruta relativa sin estilo, fuente base de PDF de respaldo)
FAMILIES: dict[str, tuple[str, str]] = {
    "Sans (Arial)": ("liberation/LiberationSans", "helv"),
    "Serif (Times New Roman)": ("liberation/LiberationSerif", "tiro"),
    "Mono (Courier)": ("liberation/LiberationMono", "cour"),
    "Calibri (Carlito)": ("crosextra/Carlito", "helv"),
    "Cambria (Caladea)": ("crosextra/Caladea", "tiro"),
}
DEFAULT_FAMILY = "Sans (Arial)"

_STYLE_SUFFIX = {
    (False, False): "Regular",
    (True, False): "Bold",
    (False, True): "Italic",
    (True, True): "BoldItalic",
}
# Variantes de las fuentes base de PDF, en el mismo orden que _STYLE_SUFFIX
_BASE14_VARIANTS = {
    "helv": dict(zip(_STYLE_SUFFIX, ("helv", "hebo", "heit", "hebi"))),
    "tiro": dict(zip(_STYLE_SUFFIX, ("tiro", "tibo", "tiit", "tibi"))),
    "cour": dict(zip(_STYLE_SUFFIX, ("cour", "cobo", "coit", "cobi"))),
}

# Banderas de PyMuPDF para cada fragmento de texto (span["flags"])
_FLAG_ITALIC, _FLAG_SERIF, _FLAG_MONO, _FLAG_BOLD = 2, 4, 8, 16

RGB = tuple[float, float, float]


@dataclass(frozen=True)
class TextStyle:
    family: str = DEFAULT_FAMILY
    size: float = 11.0
    bold: bool = False
    italic: bool = False
    color: RGB = (0.0, 0.0, 0.0)

    def with_(self, **cambios) -> "TextStyle":
        return replace(self, **cambios)


def resolve_font(style: TextStyle) -> tuple[str, str | None]:
    """Devuelve (fontname, fontfile) listos para las funciones de inserción de PyMuPDF."""
    base, fallback = FAMILIES.get(style.family, FAMILIES[DEFAULT_FAMILY])
    suffix = _STYLE_SUFFIX[(style.bold, style.italic)]
    for directory in FONT_DIRS:
        path = directory / f"{base}-{suffix}.ttf"
        if path.exists():
            return "F" + path.stem.replace("-", ""), str(path)
    return _BASE14_VARIANTS[fallback][(style.bold, style.italic)], None


def guess_family(font_name: str, flags: int = 0) -> str:
    """Elige la familia más parecida a la fuente original del PDF."""
    name = font_name.lower()
    if "calibri" in name:
        return "Calibri (Carlito)"
    if "cambria" in name:
        return "Cambria (Caladea)"
    if "courier" in name or "mono" in name or flags & _FLAG_MONO:
        return "Mono (Courier)"
    if "times" in name or ("serif" in name and "sans" not in name) or flags & _FLAG_SERIF:
        return "Serif (Times New Roman)"
    return DEFAULT_FAMILY


def style_from_span(font_name: str, flags: int, size: float, color: int) -> TextStyle:
    """Construye un TextStyle equivalente al de un fragmento de texto existente."""
    name = font_name.lower()
    return TextStyle(
        family=guess_family(font_name, flags),
        size=round(size, 1),
        bold=bool(flags & _FLAG_BOLD) or "bold" in name or "black" in name,
        italic=bool(flags & _FLAG_ITALIC) or "italic" in name or "oblique" in name,
        color=int_to_rgb(color),
    )


def int_to_rgb(value: int) -> RGB:
    return ((value >> 16) & 255) / 255, ((value >> 8) & 255) / 255, (value & 255) / 255


def rgb_to_hex(rgb: RGB) -> str:
    return "#%02x%02x%02x" % tuple(round(v * 255) for v in rgb)


def hex_to_rgb(value: str) -> RGB:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]
