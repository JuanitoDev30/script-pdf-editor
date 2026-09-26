#!/usr/bin/env bash
# Instala Editor PDF para el usuario actual (no requiere sudo).
#   - crea un entorno virtual en ./venv con las dependencias
#   - añade el comando `editor-pdf` en ~/.local/bin
#   - añade "Editor PDF" al menú de aplicaciones y a "Abrir con" para PDF
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$PROJECT_DIR/venv"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"

if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "Falta Tkinter. Instálalo con:  sudo apt install python3-tk" >&2
    exit 1
fi

echo "→ Creando entorno virtual en $VENV"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -e "$PROJECT_DIR${DEV:+[dev]}"

echo "→ Enlazando el comando editor-pdf en $BIN_DIR"
mkdir -p "$BIN_DIR" "$APPS_DIR"
ln -sf "$VENV/bin/editor-pdf" "$BIN_DIR/editor-pdf"

echo "→ Registrando la aplicación en el menú"
cat > "$APPS_DIR/editor-pdf.desktop" <<EOF
[Desktop Entry]
Name=Editor PDF
Comment=Editar PDF conservando la plantilla
Exec=$VENV/bin/editor-pdf %f
Icon=accessories-text-editor
Terminal=false
Type=Application
MimeType=application/pdf;
Categories=Office;
EOF
update-desktop-database "$APPS_DIR" 2>/dev/null || true

for font in liberation/LiberationSans-Regular.ttf crosextra/Carlito-Regular.ttf; do
    if [[ ! -f "/usr/share/fonts/truetype/$font" ]]; then
        echo "Aviso: no se encontró $font. Para que el texto se parezca más al de Word instala:"
        echo "       sudo apt install fonts-liberation fonts-crosextra-carlito fonts-crosextra-caladea"
        break
    fi
done

echo "✓ Listo. Ejecuta «editor-pdf» o búscalo en el menú como «Editor PDF»."
