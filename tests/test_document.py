import pymupdf
import pytest

from editor_pdf.core import Align, DocumentError, PdfDocument, TextDoesNotFit, TextStyle

from .conftest import BOX, HEADER_FILL


def find_span(document, needle):
    page = document._doc[0]
    rect = page.search_for(needle)[0]
    return document.span_at(0, rect.tl + (1, rect.height / 2))


def pixel(document, x, y):
    pix = document._doc[0].get_pixmap()
    return pix.pixel(x, y)


def is_header_color(rgb):
    return all(abs(c - round(f * 255)) <= 1 for c, f in zip(rgb, HEADER_FILL))


def test_open_rejects_non_pdf(tmp_path):
    fake = tmp_path / "nota.txt"
    fake.write_text("hola")
    with pytest.raises(DocumentError):
        PdfDocument.open(fake)


def test_span_at_detects_existing_style(document):
    span = find_span(document, "Nombre")
    assert span.text.startswith("Nombre: [ESCRIBA")
    assert span.style.family == "Serif (Times New Roman)"
    assert span.style.size == 12
    assert document.span_at(0, pymupdf.Point(300, 400)) is None


def test_replace_keeps_template_and_neighbours(document):
    span = find_span(document, "Nombre")
    document.replace_span(0, span, "Nombre: Walter Pérez Muñoz", span.style)

    text = document.text(0)
    assert "Walter Pérez Muñoz" in text
    assert "[ESCRIBA" not in text
    assert "Línea vecina que debe conservarse" in text
    assert "UNIVERSIDAD DE EJEMPLO" in text
    # El fondo del encabezado y la línea de la plantilla siguen dibujados.
    assert is_header_color(pixel(document, 5, 5))
    assert pixel(document, 300, 150) != (255, 255, 255)
    assert document.modified


def test_insert_text_at_point(document):
    document.insert_text(0, pymupdf.Point(100, 400), "Hola\nmundo", TextStyle(size=14, bold=True))
    assert "Hola\nmundo" in document.text(0)


def test_textbox_shrinks_font_to_fit(document):
    long_text = "Párrafo largo con acentos y eñes que debe ajustarse. " * 20
    size = document.insert_textbox(0, BOX, long_text, TextStyle(size=14), Align.JUSTIFY)
    assert size < 14
    # El texto aparece una sola vez: los intentos fallidos no dejan restos.
    assert document.text(0).count("Párrafo largo") == 20


def test_textbox_that_never_fits_leaves_document_untouched(document):
    before = document.text(0)
    with pytest.raises(TextDoesNotFit):
        document.insert_textbox(0, pymupdf.Rect(50, 400, 60, 405), "x" * 500, TextStyle())
    assert document.text(0) == before
    assert not document.modified
    assert not document.history.can_undo


def test_erase_removes_text_but_not_graphics(document):
    document.erase(0, pymupdf.Rect(0, 0, 595, 90))
    assert "UNIVERSIDAD" not in document.text(0)
    assert is_header_color(pixel(document, 5, 5))


def test_undo_redo(document):
    original = document.text(0)
    document.insert_text(1, pymupdf.Point(50, 50), "segunda página", TextStyle())
    # Deshacer y rehacer devuelven la página donde ocurrió el cambio.
    assert document.undo() == 1
    assert document.text(0) == original
    assert "segunda página" not in document.text(1)
    assert document.redo() == 1
    assert "segunda página" in document.text(1)
    assert document.redo() is None


def test_save_roundtrip(document, tmp_path):
    document.insert_text(0, pymupdf.Point(50, 400), "guardado", TextStyle())
    target = tmp_path / "salida.pdf"
    document.save(target)
    assert not document.modified
    assert document.path == target
    assert "guardado" in PdfDocument.open(target).text(0)


def test_rotated_pages_are_normalised(tmp_path):
    doc = pymupdf.open()
    doc.new_page().set_rotation(90)
    path = tmp_path / "girado.pdf"
    doc.save(path)
    document = PdfDocument.open(path)
    assert document._doc[0].rotation == 0
