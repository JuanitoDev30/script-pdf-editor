# Editor PDF

Editor de escritorio para **rellenar y corregir PDF sin perder su diseño**.

Muchas plantillas (formatos de la universidad, portadas, informes) se desordenan al
convertirlas a Word. Editor PDF trabaja directamente sobre el PDF: escribe encima de la
página original, así que logos, tablas, fondos, márgenes y tipografías se quedan como están.

## Características

- **Escribir texto** en cualquier punto de la página, o en un **cuadro con ajuste de línea**
  (izquierda, centro, derecha o justificado). Si el texto no cabe, la letra se reduce sola.
- **Reemplazar texto existente** con un clic. El nuevo texto hereda la fuente, el tamaño y el
  color del original.
- **Borrar zonas de texto** sin tocar imágenes, líneas ni fondos de la plantilla.
- Fuentes compatibles con Office: Arial, Times New Roman, Courier, Calibri y Cambria
  (mediante Liberation, Carlito y Caladea, que tienen las mismas medidas).
- Deshacer / rehacer ilimitado dentro de la sesión (30 pasos).
- Admite tildes, ñ y cualquier carácter latino.

## Requisitos

- Linux con Python 3.10 o superior y Tkinter (`sudo apt install python3-tk`)
- Recomendado, para que el texto se parezca al de Word:

  ```bash
  sudo apt install fonts-liberation fonts-crosextra-carlito fonts-crosextra-caladea
  ```

Si faltan estas fuentes, el editor usa Helvetica, Times y Courier en su lugar.

## Instalación

```bash
git clone https://github.com/JuanitoDev30/script-pdf-editor.git editor-pdf
cd editor-pdf
./scripts/install.sh
```

El instalador no necesita `sudo`. Crea un entorno virtual en `venv/`, añade el comando
`editor-pdf` en `~/.local/bin` y registra **Editor PDF** en el menú de aplicaciones y en
*Abrir con…* para archivos PDF.

## Uso

```bash
editor-pdf                    # abre la ventana vacía
editor-pdf documento.pdf      # abre directamente un archivo
python -m editor_pdf          # alternativa sin instalar el comando
```

1. **Abrir** el PDF.
2. Elegir una herramienta en la barra superior:

   | Herramienta | Acción | Resultado |
   |---|---|---|
   | Escribir texto | Clic | Texto con la esquina superior izquierda en ese punto |
   | Escribir texto | Arrastrar | Cuadro de texto con ajuste de línea |
   | Reemplazar texto | Clic sobre un texto resaltado en azul | Sustituye ese fragmento |
   | Borrar zona | Arrastrar un rectángulo | Elimina el texto que hay dentro |

3. **Guardar como**, que propone `nombre_editado.pdf` para no tocar el original.

### Atajos de teclado

| Atajo | Acción |
|---|---|
| `Ctrl+O` | Abrir |
| `Ctrl+S` / `Ctrl+Shift+S` | Guardar / Guardar como |
| `Ctrl+Z` / `Ctrl+Y` | Deshacer / Rehacer |
| `Ctrl +` / `Ctrl -` | Acercar / Alejar |
| `RePág` / `AvPág` | Página anterior / siguiente |
| `Ctrl+Enter` | Aceptar el diálogo de texto |

## Cómo funciona

- **Escribir** añade texto nuevo a la página con [PyMuPDF](https://pymupdf.readthedocs.io/)
  e incrusta la fuente elegida, así que el PDF se ve igual en cualquier equipo.
- **Reemplazar y borrar** usan *redacciones* de PDF limitadas al texto: se eliminan los
  caracteres de la zona, pero las imágenes y los gráficos vectoriales (líneas, tablas,
  fondos) se conservan. La zona se estrecha verticalmente para no alcanzar las líneas vecinas.
- Las páginas giradas se enderezan al abrir, sin cambiar su aspecto, para que las
  coordenadas del ratón coincidan con las del PDF.



```python
from editor_pdf.core import PdfDocument, TextStyle
import pymupdf

doc = PdfDocument.open("plantilla.pdf")
doc.insert_text(0, pymupdf.Point(72, 100), "Juan Pérez", TextStyle(family="Sans (Arial)", size=12))
doc.save("plantilla_rellena.pdf")
```

## Desarrollo

```bash
DEV=1 ./scripts/install.sh    # instala también pytest
./venv/bin/pytest
```

Las pruebas generan una plantilla de ejemplo y comprueban que cada operación deja
intactos el encabezado, las líneas y el texto vecino.

## Limitaciones

- **PDF escaneados:** la página es una imagen, así que no hay texto que reemplazar. Se puede
  escribir encima, pero no borrar el texto de la imagen.
- **Reemplazar** trabaja por fragmento (un tramo con el mismo estilo). Si el texto nuevo es
  mucho más largo, puede salirse de su espacio. En ese caso conviene borrar la zona y usar
  un cuadro de texto.
- Si la fuente original no es ninguna de las compatibles, se usa la más parecida.
- No edita formularios PDF interactivos (campos rellenables), imágenes ni firmas digitales.

## Uso responsable

Esta herramienta sirve para rellenar plantillas y corregir documentos propios. No la uses
para alterar documentos oficiales emitidos por terceros (certificados, comprobantes de
pago, notas, etc.). Si uno de ellos tiene un error, pide a quien lo emitió que lo corrija.
