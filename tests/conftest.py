import pymupdf
import pytest

from editor_pdf.core import PdfDocument

HEADER_FILL = (0.1, 0.3, 0.6)
BOX = pymupdf.Rect(40, 200, 550, 320)


@pytest.fixture
def template_path(tmp_path):
    """PDF que imita una plantilla: encabezado de color, línea, campos y un recuadro."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.draw_rect(pymupdf.Rect(0, 0, 595, 90), color=None, fill=HEADER_FILL)
    page.insert_text((40, 55), "UNIVERSIDAD DE EJEMPLO", fontsize=20, color=(1, 1, 1), fontname="hebo")
    page.insert_text((40, 140), "Nombre: [ESCRIBA AQUÍ]", fontsize=12, fontname="tiro")
    page.draw_line((40, 150), (550, 150), color=HEADER_FILL, width=2)
    page.insert_text((40, 170), "Línea vecina que debe conservarse", fontsize=12, fontname="tiro")
    page.draw_rect(BOX, color=(0, 0, 0))
    doc.new_page()
    path = tmp_path / "plantilla.pdf"
    doc.save(path)
    return path


@pytest.fixture
def document(template_path):
    return PdfDocument.open(template_path)
