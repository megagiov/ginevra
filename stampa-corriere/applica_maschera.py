#!/usr/bin/env python3
"""Fonde la maschera pubblicitaria GM Vegasi dentro una LDV corriere.

Uso:
    python3 applica_maschera.py etichetta.pdf
    python3 applica_maschera.py etichetta.pdf -o etichetta_brandizzata.pdf

L'output è un unico PDF: la LDV originale con i badge GM Vegasi / TikTok Shop
già dentro, nello spazio bianco che la pagina lascia libero. Si stampa una
volta sola, come si stampava prima il PDF del corriere.

Lo spazio libero viene cercato leggendo la pagina, non con misure fisse: ogni
corriere impagina la sua LDV a modo suo (GLS verticale con il fondo libero,
Poste orizzontale con il testo molto più in basso) e una misura buona per uno
finirebbe sopra il contenuto di un altro. Se non c'è spazio sufficiente la
pagina viene lasciata intatta: meglio un'etichetta senza badge che
un'etichetta illeggibile.
"""

import argparse
import os
import tempfile
from pathlib import Path

import pymupdf
from playwright.sync_api import sync_playwright

TEMPLATE = Path(__file__).parent / "maschera-10x15.html"
# Di norma None: usa il Chromium installato da "playwright install chromium".
# Impostabile con la variabile d'ambiente PLAYWRIGHT_CHROMIUM_PATH per chi ne
# usa uno preinstallato altrove.
CHROMIUM_PATH = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH") or None
PT_PER_MM = 72 / 25.4

BADGE_H_MM = 14.4          # altezza preferita dei badge
BANDA_MINIMA_MM = 9.0      # sotto questa altezza di spazio libero si rinuncia
MARGINE_MM = 2.0           # aria che resta comunque fra badge e contenuto
DPI_ANALISI = 100
SOGLIA_BIANCO = 245        # 0 nero, 255 bianco
# Somma dei rapporti larghezza/altezza dei due badge, per capire se ci stanno
# in larghezza: borsa 851x681 + scritta 568x257.
RAPPORTO_BADGE = 851 / 681 + 568 / 257
GAP_BADGE_MM = 3.0


def banda_libera(page: pymupdf.Page) -> tuple[float, float] | None:
    """Trova la fascia orizzontale bianca più in basso della pagina.

    Ritorna (inizio_mm_dall_alto, altezza_mm), oppure None se non c'è una
    fascia abbastanza alta da ospitare i badge.
    """
    pix = page.get_pixmap(dpi=DPI_ANALISI, colorspace=pymupdf.csGRAY)
    larghezza, altezza, campioni = pix.width, pix.height, pix.samples
    mm_per_pixel = 25.4 / DPI_ANALISI

    bande: list[tuple[int, int]] = []
    inizio = None
    for y in range(altezza):
        riga_vuota = min(campioni[y * larghezza:(y + 1) * larghezza]) >= SOGLIA_BIANCO
        if riga_vuota and inizio is None:
            inizio = y
        elif not riga_vuota and inizio is not None:
            bande.append((inizio, y))
            inizio = None
    if inizio is not None:
        bande.append((inizio, altezza))

    utilizzabili = [
        (y0, y1) for y0, y1 in bande
        if (y1 - y0) * mm_per_pixel >= BANDA_MINIMA_MM + 2 * MARGINE_MM
    ]
    if not utilizzabili:
        return None

    y0, y1 = utilizzabili[-1]  # la più in basso: i badge stanno lontani dai barcode
    return y0 * mm_per_pixel + MARGINE_MM, (y1 - y0) * mm_per_pixel - 2 * MARGINE_MM


def misure_badge(banda_h_mm: float, pagina_w_mm: float) -> tuple[float, float, float]:
    """Altezza dei badge e riquadro in cui centrarli, dentro la banda libera."""
    badge_h = min(BADGE_H_MM, banda_h_mm)
    larghezza_utile = pagina_w_mm - 2 * MARGINE_MM - GAP_BADGE_MM
    badge_h = min(badge_h, larghezza_utile / RAPPORTO_BADGE)
    box_h = min(banda_h_mm, badge_h + 8.0)
    return badge_h, box_h, banda_h_mm - box_h


def genera_overlay_pdf(
    page,
    width_mm: float,
    height_mm: float,
    box_top_mm: float,
    box_h_mm: float,
    badge_h_mm: float,
    out_path: Path,
) -> None:
    override_css = (
        f":root {{ --page-w: {width_mm}mm; --page-h: {height_mm}mm; "
        f"--box-top: {box_top_mm}mm; --box-h: {box_h_mm}mm; "
        f"--badge-h: {badge_h_mm}mm; --gap-badge: {GAP_BADGE_MM}mm; }}"
    )
    page.add_style_tag(content=override_css)
    page.pdf(
        path=str(out_path),
        width=f"{width_mm}mm",
        height=f"{height_mm}mm",
        print_background=True,
        margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
    )


def applica_maschera(input_pdf: Path, output_pdf: Path, tmp_dir: Path) -> int:
    """Brandizza ogni pagina che ha spazio libero. Ritorna quante ne ha fatte."""
    doc = pymupdf.open(input_pdf)
    overlay_cache: dict[tuple, pymupdf.Document] = {}
    overlay_paths: list[Path] = []
    brandizzate = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM_PATH)
        browser_page = browser.new_page()
        browser_page.goto(TEMPLATE.resolve().as_uri())

        for pdf_page in doc:
            w_mm = pdf_page.rect.width / PT_PER_MM
            h_mm = pdf_page.rect.height / PT_PER_MM

            banda = banda_libera(pdf_page)
            if banda is None:
                print(f"  pagina {pdf_page.number + 1}: nessuno spazio libero, la lascio com'è")
                continue

            banda_top, banda_h = banda
            badge_h, box_h, scarto = misure_badge(banda_h, w_mm)
            box_top = banda_top + scarto  # appoggiati in fondo alla banda

            key = tuple(round(v, 2) for v in (w_mm, h_mm, box_top, box_h, badge_h))
            if key not in overlay_cache:
                overlay_path = tmp_dir / ("_overlay_" + "_".join(str(v) for v in key) + ".pdf")
                genera_overlay_pdf(browser_page, w_mm, h_mm, box_top, box_h, badge_h, overlay_path)
                overlay_cache[key] = pymupdf.open(overlay_path)
                overlay_paths.append(overlay_path)

            pdf_page.show_pdf_page(pdf_page.rect, overlay_cache[key], 0)
            brandizzate += 1

        browser.close()

    doc.save(output_pdf)
    doc.close()
    for overlay_doc in overlay_cache.values():
        overlay_doc.close()
    for overlay_path in overlay_paths:
        overlay_path.unlink(missing_ok=True)
    return brandizzate


def main() -> None:
    ap = argparse.ArgumentParser(description="Fonde la maschera pubblicitaria GM Vegasi in una LDV corriere.")
    ap.add_argument("input_pdf", type=Path, help="PDF della LDV scaricato dal corriere.")
    ap.add_argument("-o", "--output", type=Path, default=None, help="PDF di output (default: <nome>_brandizzato.pdf).")
    args = ap.parse_args()

    output = args.output or args.input_pdf.with_name(args.input_pdf.stem + "_brandizzato.pdf")
    tmp_dir = Path(tempfile.gettempdir())
    applica_maschera(args.input_pdf, output, tmp_dir)
    print(f"Creato: {output}")


if __name__ == "__main__":
    main()
