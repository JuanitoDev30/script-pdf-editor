#!/usr/bin/env python3
"""
Editor PDF sencillo que conserva la plantilla / diseño original.

Modos de trabajo:
  * Escribir texto : clic = texto en ese punto; arrastrar = cuadro de texto con ajuste de línea.
  * Reemplazar     : clic sobre un texto existente para cambiarlo (misma fuente, tamaño y color).
  * Borrar zona    : arrastrar un rectángulo para eliminar el texto que hay dentro
                     (las imágenes, líneas y fondos de la plantilla se conservan).

Uso:  editor-pdf [archivo.pdf]
"""
import base64
import os
import sys
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

import pymupdf as fitz

FONT_DIR = "/usr/share/fonts/truetype"
# Fuentes libres con las mismas medidas que Arial, Times, Courier, Calibri y Cambria.
FAMILIAS = {
    "Sans (Arial)": ("liberation/LiberationSans", "helv"),
    "Serif (Times New Roman)": ("liberation/LiberationSerif", "tiro"),
    "Mono (Courier)": ("liberation/LiberationMono", "cour"),
    "Calibri (Carlito)": ("crosextra/Carlito", "helv"),
    "Cambria (Caladea)": ("crosextra/Caladea", "tiro"),
}
ESTILOS = {(False, False): "Regular", (True, False): "Bold",
           (False, True): "Italic", (True, True): "BoldItalic"}

MODOS = {"texto": "Escribir texto", "reemplazar": "Reemplazar texto", "borrar": "Borrar zona"}


def archivo_fuente(familia, negrita, cursiva):
    """Devuelve (fontname, fontfile) para insertar texto en el PDF."""
    base, respaldo = FAMILIAS.get(familia, FAMILIAS["Sans (Arial)"])
    estilo = ESTILOS[(negrita, cursiva)]
    ruta = os.path.join(FONT_DIR, f"{base}-{estilo}.ttf")
    if os.path.exists(ruta):
        nombre = "F" + os.path.basename(ruta).replace("-", "").replace(".ttf", "")
        return nombre, ruta
    return respaldo, None


def familia_de_span(span):
    """Adivina qué familia usar a partir de la fuente original del PDF."""
    nombre = span["font"].lower()
    flags = span["flags"]
    if "calibri" in nombre:
        fam = "Calibri (Carlito)"
    elif "cambria" in nombre:
        fam = "Cambria (Caladea)"
    elif "courier" in nombre or "mono" in nombre or flags & 8:
        fam = "Mono (Courier)"
    elif "times" in nombre or "serif" in nombre and "sans" not in nombre or flags & 4:
        fam = "Serif (Times New Roman)"
    else:
        fam = "Sans (Arial)"
    negrita = bool(flags & 16) or "bold" in nombre or "black" in nombre
    cursiva = bool(flags & 2) or "italic" in nombre or "oblique" in nombre
    return fam, negrita, cursiva


def int_a_rgb(c):
    return ((c >> 16) & 255) / 255, ((c >> 8) & 255) / 255, (c & 255) / 255


def rgb_a_hex(rgb):
    return "#%02x%02x%02x" % tuple(int(v * 255) for v in rgb)


def hex_a_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


class DialogoTexto(tk.Toplevel):
    """Ventana para escribir el texto y elegir fuente, tamaño, color y alineación."""

    def __init__(self, padre, titulo, texto="", familia="Sans (Arial)", tam=11.0,
                 negrita=False, cursiva=False, color=(0, 0, 0), con_alineacion=False):
        super().__init__(padre)
        self.title(titulo)
        self.transient(padre)
        self.resultado = None
        self.color = color

        marco = ttk.Frame(self, padding=10)
        marco.pack(fill="both", expand=True)

        self.txt = tk.Text(marco, width=60, height=6, wrap="word", font=("Sans", 11), undo=True)
        self.txt.insert("1.0", texto)
        self.txt.grid(row=0, column=0, columnspan=6, sticky="nsew", pady=(0, 8))

        ttk.Label(marco, text="Fuente:").grid(row=1, column=0, sticky="w")
        self.familia = ttk.Combobox(marco, values=list(FAMILIAS), state="readonly", width=24)
        self.familia.set(familia)
        self.familia.grid(row=1, column=1, sticky="w")

        ttk.Label(marco, text="Tamaño:").grid(row=1, column=2, sticky="e", padx=(10, 2))
        self.tam = tk.DoubleVar(value=round(tam, 1))
        ttk.Spinbox(marco, from_=4, to=96, increment=0.5, textvariable=self.tam, width=6).grid(
            row=1, column=3, sticky="w")

        self.negrita = tk.BooleanVar(value=negrita)
        self.cursiva = tk.BooleanVar(value=cursiva)
        ttk.Checkbutton(marco, text="Negrita", variable=self.negrita).grid(row=2, column=0, sticky="w")
        ttk.Checkbutton(marco, text="Cursiva", variable=self.cursiva).grid(row=2, column=1, sticky="w")

        self.btn_color = tk.Button(marco, text="Color", width=8, command=self.elegir_color,
                                   bg=rgb_a_hex(color), fg="white" if sum(color) < 1.5 else "black")
        self.btn_color.grid(row=2, column=2, columnspan=2, sticky="w", padx=(10, 0))

        self.alineacion = tk.StringVar(value="Izquierda")
        if con_alineacion:
            ttk.Label(marco, text="Alinear:").grid(row=3, column=0, sticky="w", pady=(6, 0))
            ttk.Combobox(marco, textvariable=self.alineacion, state="readonly", width=12,
                         values=["Izquierda", "Centro", "Derecha", "Justificado"]).grid(
                row=3, column=1, sticky="w", pady=(6, 0))

        botones = ttk.Frame(marco)
        botones.grid(row=4, column=0, columnspan=6, sticky="e", pady=(10, 0))
        ttk.Button(botones, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(botones, text="Aceptar (Ctrl+Enter)", command=self.aceptar).pack(side="right", padx=6)

        marco.columnconfigure(5, weight=1)
        marco.rowconfigure(0, weight=1)
        self.bind("<Control-Return>", lambda e: self.aceptar())
        self.bind("<Escape>", lambda e: self.destroy())
        self.txt.focus_set()
        self.txt.tag_add("sel", "1.0", "end")
        self.wait_visibility()
        self.grab_set()
        padre.wait_window(self)

    def elegir_color(self):
        c = colorchooser.askcolor(color=rgb_a_hex(self.color), parent=self)
        if c[1]:
            self.color = hex_a_rgb(c[1])
            self.btn_color.configure(bg=c[1], fg="white" if sum(self.color) < 1.5 else "black")

    def aceptar(self):
        try:
            tam = float(self.tam.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Tamaño", "El tamaño de letra no es válido.", parent=self)
            return
        self.resultado = {
            "texto": self.txt.get("1.0", "end-1c"),
            "familia": self.familia.get(),
            "tam": tam,
            "negrita": self.negrita.get(),
            "cursiva": self.cursiva.get(),
            "color": self.color,
            "alineacion": ["Izquierda", "Centro", "Derecha", "Justificado"].index(self.alineacion.get()),
        }
        self.destroy()


class EditorPDF(tk.Tk):
    def __init__(self, ruta=None):
        super().__init__()
        self.title("Editor PDF")
        self.geometry("1100x850")
        self.doc = None
        self.ruta = None
        self.pagina = 0
        self.zoom = 1.5
        self.historial = []      # copias del PDF para Deshacer
        self.rehacer = []
        self.modificado = False
        self.modo = tk.StringVar(value="texto")
        self.ultimo_estilo = {"familia": "Sans (Arial)", "tam": 11.0, "negrita": False,
                              "cursiva": False, "color": (0, 0, 0)}
        self.inicio_arrastre = None
        self.rect_id = None
        self.hover_id = None

        self.crear_interfaz()
        self.protocol("WM_DELETE_WINDOW", self.salir)
        if ruta:
            self.abrir(ruta)

    # ------------------------------------------------------------------ interfaz
    def crear_interfaz(self):
        barra = ttk.Frame(self, padding=4)
        barra.pack(fill="x")
        ttk.Button(barra, text="Abrir", command=self.abrir).pack(side="left")
        ttk.Button(barra, text="Guardar", command=self.guardar).pack(side="left", padx=2)
        ttk.Button(barra, text="Guardar como", command=self.guardar_como).pack(side="left")
        ttk.Separator(barra, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(barra, text="↶ Deshacer", command=self.deshacer).pack(side="left")
        ttk.Button(barra, text="↷ Rehacer", command=self.rehacer_cambio).pack(side="left", padx=2)
        ttk.Separator(barra, orient="vertical").pack(side="left", fill="y", padx=8)
        for clave, nombre in MODOS.items():
            ttk.Radiobutton(barra, text=nombre, value=clave, variable=self.modo,
                            command=self.cambio_modo).pack(side="left", padx=2)
        ttk.Separator(barra, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(barra, text="◀", width=3, command=lambda: self.ir_a(self.pagina - 1)).pack(side="left")
        self.lbl_pag = ttk.Label(barra, text="- / -", width=9, anchor="center")
        self.lbl_pag.pack(side="left")
        ttk.Button(barra, text="▶", width=3, command=lambda: self.ir_a(self.pagina + 1)).pack(side="left")
        ttk.Button(barra, text="−", width=3, command=lambda: self.cambiar_zoom(0.8)).pack(side="left", padx=(8, 0))
        ttk.Button(barra, text="+", width=3, command=lambda: self.cambiar_zoom(1.25)).pack(side="left")

        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(cuerpo, bg="#6b6b6b", highlightthickness=0)
        sy = ttk.Scrollbar(cuerpo, orient="vertical", command=self.canvas.yview)
        sx = ttk.Scrollbar(cuerpo, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        self.canvas.pack(fill="both", expand=True)

        self.estado = ttk.Label(self, relief="sunken", anchor="w", padding=(6, 2))
        self.estado.pack(fill="x")
        self.cambio_modo()

        self.canvas.bind("<ButtonPress-1>", self.al_presionar)
        self.canvas.bind("<B1-Motion>", self.al_arrastrar)
        self.canvas.bind("<ButtonRelease-1>", self.al_soltar)
        self.canvas.bind("<Motion>", self.al_mover)
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-e.delta // 40, "units"))
        self.bind("<Control-o>", lambda e: self.abrir())
        self.bind("<Control-s>", lambda e: self.guardar())
        self.bind("<Control-Shift-S>", lambda e: self.guardar_como())
        self.bind("<Control-z>", lambda e: self.deshacer())
        self.bind("<Control-y>", lambda e: self.rehacer_cambio())
        self.bind("<Prior>", lambda e: self.ir_a(self.pagina - 1))
        self.bind("<Next>", lambda e: self.ir_a(self.pagina + 1))
        self.bind("<Control-plus>", lambda e: self.cambiar_zoom(1.25))
        self.bind("<Control-minus>", lambda e: self.cambiar_zoom(0.8))

    def cambio_modo(self):
        ayudas = {
            "texto": "Clic: escribir en ese punto  ·  Arrastrar: cuadro de texto con ajuste de línea",
            "reemplazar": "Pasa el ratón sobre un texto (se marca en azul) y haz clic para cambiarlo",
            "borrar": "Arrastra un rectángulo: se borra el texto dentro (el diseño se conserva)",
        }
        self.canvas.configure(cursor={"texto": "xterm", "reemplazar": "hand2", "borrar": "crosshair"}[self.modo.get()])
        self.estado.configure(text=ayudas[self.modo.get()])
        self.borrar_hover()

    # ------------------------------------------------------------------ archivo
    def abrir(self, ruta=None):
        if not self.confirmar_descartar():
            return
        ruta = ruta or filedialog.askopenfilename(filetypes=[("PDF", "*.pdf *.PDF"), ("Todos", "*")])
        if not ruta:
            return
        try:
            doc = fitz.open(ruta)
            if doc.needs_pass:
                messagebox.showerror("Protegido", "El PDF está protegido con contraseña.")
                return
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el archivo:\n{e}")
            return
        # Las páginas giradas complican las coordenadas: se "enderezan" sin cambiar su aspecto.
        for p in doc:
            if p.rotation:
                p.remove_rotation()
        self.doc, self.ruta, self.pagina = doc, ruta, 0
        self.historial.clear()
        self.rehacer.clear()
        self.modificado = False
        self.actualizar_titulo()
        self.dibujar()

    def guardar(self):
        if not self.doc:
            return
        if self.ruta and self.ruta.lower().endswith(".pdf"):
            destino = self.ruta
            if not messagebox.askyesno("Guardar", f"¿Sobrescribir el archivo original?\n{destino}\n\n"
                                       "(Elige 'No' para guardar una copia)"):
                return self.guardar_como()
        else:
            return self.guardar_como()
        self.escribir(destino)

    def guardar_como(self):
        if not self.doc:
            return
        base = os.path.splitext(os.path.basename(self.ruta or "documento"))[0]
        destino = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"{base}_editado.pdf",
                                               initialdir=os.path.dirname(self.ruta or ""),
                                               filetypes=[("PDF", "*.pdf")])
        if destino:
            self.escribir(destino)

    def escribir(self, destino):
        try:
            datos = self.doc.tobytes(garbage=3, deflate=True)
            with open(destino, "wb") as f:
                f.write(datos)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar:\n{e}")
            return
        self.doc = fitz.open("pdf", datos)
        self.ruta = destino
        self.modificado = False
        self.actualizar_titulo()
        self.estado.configure(text=f"Guardado en {destino}")

    def confirmar_descartar(self):
        if self.doc and self.modificado:
            r = messagebox.askyesnocancel("Cambios sin guardar", "¿Guardar los cambios antes de continuar?")
            if r is None:
                return False
            if r:
                self.guardar_como()
                return not self.modificado
        return True

    def salir(self):
        if self.confirmar_descartar():
            self.destroy()

    def actualizar_titulo(self):
        nombre = os.path.basename(self.ruta) if self.ruta else ""
        self.title(f"{'* ' if self.modificado else ''}{nombre} — Editor PDF")

    # ------------------------------------------------------------------ historial
    def guardar_estado(self):
        self.historial.append((self.doc.tobytes(), self.pagina))
        self.historial = self.historial[-30:]
        self.rehacer.clear()

    def deshacer(self):
        if not self.historial:
            return
        self.rehacer.append((self.doc.tobytes(), self.pagina))
        datos, self.pagina = self.historial.pop()
        self.doc = fitz.open("pdf", datos)
        self.marcar_modificado()

    def rehacer_cambio(self):
        if not self.rehacer:
            return
        self.historial.append((self.doc.tobytes(), self.pagina))
        datos, self.pagina = self.rehacer.pop()
        self.doc = fitz.open("pdf", datos)
        self.marcar_modificado()

    def marcar_modificado(self):
        self.modificado = True
        self.actualizar_titulo()
        self.dibujar()

    # ------------------------------------------------------------------ dibujo
    def dibujar(self):
        self.canvas.delete("all")
        self.hover_id = None
        if not self.doc:
            return
        pag = self.doc[self.pagina]
        pix = pag.get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom), alpha=False)
        self.imagen = tk.PhotoImage(data=base64.b64encode(pix.tobytes("png")))
        self.canvas.create_image(0, 0, image=self.imagen, anchor="nw")
        self.canvas.configure(scrollregion=(0, 0, pix.width, pix.height))
        self.lbl_pag.configure(text=f"{self.pagina + 1} / {len(self.doc)}")

    def ir_a(self, n):
        if self.doc and 0 <= n < len(self.doc):
            self.pagina = n
            self.dibujar()
            self.canvas.yview_moveto(0)

    def cambiar_zoom(self, factor):
        self.zoom = max(0.5, min(5.0, self.zoom * factor))
        self.dibujar()

    def a_pdf(self, event):
        """Convierte coordenadas del ratón a coordenadas del PDF (puntos)."""
        x = self.canvas.canvasx(event.x) / self.zoom
        y = self.canvas.canvasy(event.y) / self.zoom
        return fitz.Point(x, y)

    def a_canvas(self, rect):
        return [v * self.zoom for v in (rect.x0, rect.y0, rect.x1, rect.y1)]

    # ------------------------------------------------------------------ ratón
    def al_presionar(self, event):
        if not self.doc:
            return
        self.inicio_arrastre = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))

    def al_arrastrar(self, event):
        if not self.inicio_arrastre or self.modo.get() == "reemplazar":
            return
        x0, y0 = self.inicio_arrastre
        x1, y1 = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        color = "#d33" if self.modo.get() == "borrar" else "#27f"
        if self.rect_id:
            self.canvas.coords(self.rect_id, x0, y0, x1, y1)
        else:
            self.rect_id = self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=2, dash=(4, 2))

    def al_soltar(self, event):
        if not self.inicio_arrastre:
            return
        x0, y0 = self.inicio_arrastre
        x1, y1 = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.inicio_arrastre = None
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None
        rect = fitz.Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)) / self.zoom
        es_arrastre = rect.width > 8 and rect.height > 8
        modo = self.modo.get()
        if modo == "texto":
            if es_arrastre:
                self.agregar_cuadro(rect)
            else:
                self.agregar_texto(fitz.Point(x1, y1) / self.zoom)
        elif modo == "reemplazar":
            self.reemplazar(self.a_pdf(event))
        elif modo == "borrar" and es_arrastre:
            if messagebox.askyesno("Borrar", "¿Borrar el texto dentro del rectángulo?"):
                self.guardar_estado()
                self.redactar(self.doc[self.pagina], [rect])
                self.marcar_modificado()

    def al_mover(self, event):
        if not self.doc or self.modo.get() != "reemplazar":
            return
        span = self.span_en(self.a_pdf(event))
        self.borrar_hover()
        if span:
            self.hover_id = self.canvas.create_rectangle(*self.a_canvas(fitz.Rect(span["bbox"])),
                                                         outline="#27f", width=2)

    def borrar_hover(self):
        if self.hover_id:
            self.canvas.delete(self.hover_id)
            self.hover_id = None

    # ------------------------------------------------------------------ edición
    def span_en(self, punto):
        """Busca el fragmento de texto (span) bajo el punto dado."""
        pag = self.doc[self.pagina]
        for bloque in pag.get_text("dict")["blocks"]:
            if bloque["type"] != 0:
                continue
            for linea in bloque["lines"]:
                for span in linea["spans"]:
                    if span["text"].strip() and fitz.Rect(span["bbox"]).contains(punto):
                        span["dir"] = linea["dir"]
                        return span
        return None

    def pedir_texto(self, titulo, con_alineacion=False, **estilo):
        e = {**self.ultimo_estilo, **estilo}
        d = DialogoTexto(self, titulo, con_alineacion=con_alineacion, **e)
        if d.resultado and d.resultado["texto"].strip():
            r = d.resultado
            self.ultimo_estilo = {k: r[k] for k in ("familia", "tam", "negrita", "cursiva", "color")}
            return r
        return None

    def insertar_lineas(self, pag, origen, r):
        nombre, archivo = archivo_fuente(r["familia"], r["negrita"], r["cursiva"])
        pag.insert_text(origen, r["texto"], fontsize=r["tam"], fontname=nombre,
                        fontfile=archivo, color=r["color"], lineheight=1.15)

    def agregar_texto(self, punto):
        r = self.pedir_texto("Escribir texto")
        if not r:
            return
        self.guardar_estado()
        pag = self.doc[self.pagina]
        # El clic marca la esquina superior izquierda; el texto se apoya en su línea base.
        self.insertar_lineas(pag, fitz.Point(punto.x, punto.y + r["tam"] * 0.8), r)
        self.marcar_modificado()

    def agregar_cuadro(self, rect):
        r = self.pedir_texto("Cuadro de texto", con_alineacion=True)
        if not r:
            return
        self.guardar_estado()
        pag = self.doc[self.pagina]
        nombre, archivo = archivo_fuente(r["familia"], r["negrita"], r["cursiva"])
        tam = r["tam"]
        # Si el texto no cabe, se reduce la letra poco a poco.
        while tam >= 4:
            sobra = pag.insert_textbox(rect, r["texto"], fontsize=tam, fontname=nombre, fontfile=archivo,
                                       color=r["color"], align=r["alineacion"], lineheight=1.15)
            if sobra >= 0:
                break
            tam -= 0.5
        if tam < 4:
            messagebox.showwarning("No cabe", "El texto no cabe en el cuadro. Dibuja un cuadro más grande.")
            self.doc = fitz.open("pdf", self.historial.pop()[0])
            return self.dibujar()
        if tam != r["tam"]:
            self.estado.configure(text=f"El texto se redujo a {tam} pt para que cupiera en el cuadro.")
        self.marcar_modificado()

    def reemplazar(self, punto):
        span = self.span_en(punto)
        if not span:
            return
        familia, negrita, cursiva = familia_de_span(span)
        r = self.pedir_texto(f"Reemplazar  «{span['text'].strip()[:50]}»", texto=span["text"].strip(),
                             familia=familia, tam=span["size"], negrita=negrita, cursiva=cursiva,
                             color=int_a_rgb(span["color"]))
        if not r:
            return
        self.guardar_estado()
        pag = self.doc[self.pagina]
        self.redactar(pag, [fitz.Rect(span["bbox"])])
        # Conserva la sangría original: el texto nuevo empieza donde empezaba el texto visible.
        inicio = len(span["text"]) - len(span["text"].lstrip())
        origen = fitz.Point(span["origin"])
        if inicio:
            ancho = fitz.get_text_length(span["text"][:inicio], fontsize=span["size"])
            origen.x += ancho
        self.insertar_lineas(pag, origen, r)
        self.marcar_modificado()

    @staticmethod
    def redactar(pag, rects):
        """Elimina el texto dentro de los rectángulos sin tocar imágenes, líneas ni fondos."""
        for rect in rects:
            # Se estrecha verticalmente para no llevarse letras de las líneas vecinas.
            margen = rect.height * 0.25
            r = fitz.Rect(rect.x0 + 0.5, rect.y0 + margen, rect.x1 - 0.5, rect.y1 - margen)
            pag.add_redact_annot(r, fill=False)
        pag.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                             graphics=fitz.PDF_REDACT_LINE_ART_NONE)


if __name__ == "__main__":
    EditorPDF(sys.argv[1] if len(sys.argv) > 1 else None).mainloop()
