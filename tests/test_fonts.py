import pytest

from editor_pdf.core import fonts
from editor_pdf.core.fonts import TextStyle, guess_family, hex_to_rgb, resolve_font, rgb_to_hex, style_from_span


@pytest.mark.parametrize("font_name, flags, expected", [
    ("ArialMT", 0, "Sans (Arial)"),
    ("BCDEEE+Arial-BoldMT", 16, "Sans (Arial)"),
    ("TimesNewRomanPSMT", 0, "Serif (Times New Roman)"),
    ("Calibri-Light", 0, "Calibri (Carlito)"),
    ("Cambria", 0, "Cambria (Caladea)"),
    ("CourierNewPSMT", 0, "Mono (Courier)"),
    ("DejaVuSans", 0, "Sans (Arial)"),
    ("Unknown", 4, "Serif (Times New Roman)"),
])
def test_guess_family(font_name, flags, expected):
    assert guess_family(font_name, flags) == expected


def test_style_from_span():
    style = style_from_span("Arial-BoldItalicMT", 0, 10.04, 0xFF0000)
    assert style == TextStyle("Sans (Arial)", 10.0, True, True, (1.0, 0.0, 0.0))


def test_resolve_font_falls_back_to_base14(monkeypatch, tmp_path):
    monkeypatch.setattr(fonts, "FONT_DIRS", (tmp_path,))
    assert resolve_font(TextStyle()) == ("helv", None)
    assert resolve_font(TextStyle(family="Serif (Times New Roman)", bold=True, italic=True)) == ("tibi", None)


def test_resolve_font_prefers_installed_file(monkeypatch, tmp_path):
    (tmp_path / "liberation").mkdir()
    ttf = tmp_path / "liberation" / "LiberationSans-Bold.ttf"
    ttf.write_bytes(b"")
    monkeypatch.setattr(fonts, "FONT_DIRS", (tmp_path,))
    assert resolve_font(TextStyle(bold=True)) == ("FLiberationSansBold", str(ttf))


def test_hex_roundtrip():
    assert rgb_to_hex(hex_to_rgb("#1a4d99")) == "#1a4d99"
