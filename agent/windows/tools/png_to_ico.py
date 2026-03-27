#!/usr/bin/env python3
"""Genera app.ico desde icono_sincronizador.png (requiere Pillow). Ejecucion manual."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Instala Pillow: pip install pillow", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "agent" / "windows" / "assets"
PNG = ASSETS / "icono_sincronizador.png"
ICO = ASSETS / "app.ico"


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else PNG
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ICO
    if not src.is_file():
        print("No existe:", src, file=sys.stderr)
        sys.exit(1)
    im = Image.open(src).convert("RGBA")
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    images = [im.resize(s, Image.Resampling.LANCZOS) for s in sizes]
    images[0].save(
        out,
        format="ICO",
        sizes=[img.size for img in images],
        append_images=images[1:],
    )
    print("Escrito:", out)


if __name__ == "__main__":
    main()
