"""Punto de entrada de la aplicación."""
from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="editor-pdf",
                                     description="Edita PDF conservando la plantilla y el diseño original.")
    parser.add_argument("archivo", nargs="?", type=Path, help="PDF a abrir al iniciar")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    from .ui import MainWindow  # import tardío: --help y --version funcionan sin pantalla

    MainWindow(args.archivo).mainloop()


if __name__ == "__main__":
    main()
