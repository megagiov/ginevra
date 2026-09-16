#!/usr/bin/env python3
"""Fonde la maschera pubblicitaria GM Vegasi dentro una LDV corriere.

Uso:
    python3 applica_maschera.py etichetta.pdf
    python3 applica_maschera.py etichetta.pdf -o etichetta_brandizzata.pdf
    python3 applica_maschera.py etichetta.pdf --zona-ldv 94

L'output è un unico PDF: la LDV originale con il logo GM Vegasi e il
badge TikTok Shop già dentro, nello spazio bianco sotto l'etichetta.
Si stampa una volta sola, come si stampava prima il PDF del corriere.
"""

import argparse
import os
import tempfile
from pathlib import Path

import fitz  # PyMuPDF
from playwright.sync_api import sync_playwright

TEMPLATE = Path(__file__).parent / "maschera-10x15.html"
# Di norma None: usa il Chromium installato da "playwright install chromium".
# Impostabile con la variabile d'ambiente PLAYWRIGHT_CHROMIUM_PATH per chi ne
# usa uno preinstallato altrove.
CHROMIUM_PATH = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH") or None
PT_PER_MM = 72 / 25.4
ZONA_LDV_DEFAULT_MM = 90.0


def genera_overlay_pdf(page, width_mm: float, height_mm: float, zona_ldv_mm: float, out_path: Path) -> None:
    override_css = (
        f":root {{ --page-w: {width_mm}mm; --page-h: {height_mm}mm; "
        f"--zona-ldv-h: {zona_ldv_mm}mm; }}"
    )
    page.add_style_tag(content=override_css)
    page.pdf(
        path=str(out_path),
        width=f"{width_mm}mm",
        height=f"{height_mm}mm",
        print_background=True,
        margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
    )


def applica_maschera(input_pdf: Path, output_pdf: Path, zona_ldv_mm: float, tmp_dir: Path) -> None:
    doc = fitz.open(input_pdf)
    overlay_cache: dict[tuple[float, float], fitz.Document] = {}
    overlay_paths: list[Path] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM_PATH)
        browser_page = browser.new_page()
        browser_page.goto(TEMPLATE.resolve().as_uri())

        for pdf_page in doc:
            w_mm = pdf_page.rect.width / PT_PER_MM
            h_mm = pdf_page.rect.height / PT_PER_MM
            key = (round(w_mm, 2), round(h_mm, 2))

            if key not in overlay_cache:
                overlay_path = tmp_dir / f"_overlay_{key[0]}x{key[1]}.pdf"
                genera_overlay_pdf(browser_page, w_mm, h_mm, zona_ldv_mm, overlay_path)
                overlay_cache[key] = fitz.open(overlay_path)
                overlay_paths.append(overlay_path)

            pdf_page.show_pdf_page(pdf_page.rect, overlay_cache[key], 0)

        browser.close()

    doc.save(output_pdf)
    doc.close()
    for overlay_doc in overlay_cache.values():
        overlay_doc.close()
    for overlay_path in overlay_paths:
        overlay_path.unlink(missing_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Fonde la maschera pubblicitaria GM Vegasi in una LDV corriere.")
    ap.add_argument("input_pdf", type=Path, help="PDF della LDV scaricato dal corriere.")
    ap.add_argument("-o", "--output", type=Path, default=None, help="PDF di output (default: <nome>_brandizzato.pdf).")
    ap.add_argument(
        "--zona-ldv",
        type=float,
        default=ZONA_LDV_DEFAULT_MM,
        help=f"Altezza in mm della fascia lasciata alla LDV (default {ZONA_LDV_DEFAULT_MM}mm, misurata su GLS).",
    )
    args = ap.parse_args()

    output = args.output or args.input_pdf.with_name(args.input_pdf.stem + "_brandizzato.pdf")
    tmp_dir = Path(tempfile.gettempdir())
    applica_maschera(args.input_pdf, output, args.zona_ldv, tmp_dir)
    print(f"Creato: {output}")


if __name__ == "__main__":
    main()
