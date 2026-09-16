#!/usr/bin/env python3
"""Fonde la maschera pubblicitaria GM Vegasi dentro una LDV corriere.

Uso:
    python3 applica_maschera.py etichetta.pdf
    python3 applica_maschera.py etichetta.pdf -o etichetta_brandizzata.pdf

L'output è un unico PDF: la LDV originale con i badge GM Vegasi / TikTok Shop
già dentro. Si stampa una volta sola, come si stampava prima il PDF del
corriere.

Dove finiscono i badge non è una misura fissa, perché ogni corriere impagina
la sua LDV a modo suo:

1. se la pagina è più corta dell'etichetta fisica 10x15 viene allargata fino
   a quella misura (una LDV Poste è 114x104mm: i 34mm che restano sul lato
   lungo sono spazio pulito, e i badge vanno lì);
2. altrimenti si cerca il riquadro bianco più in basso leggendo la pagina
   (una LDV GLS 105x148mm lascia libero il fondo);
3. se non c'è spazio la pagina resta intatta: meglio un'etichetta senza badge
   che un'etichetta illeggibile.
"""

import argparse
import os
import tempfile
from math import ceil
from pathlib import Path

import pymupdf
from playwright.sync_api import sync_playwright

TEMPLATE = Path(__file__).parent / "maschera-10x15.html"
# Di norma None: usa il Chromium installato da "playwright install chromium".
# Impostabile con la variabile d'ambiente PLAYWRIGHT_CHROMIUM_PATH per chi ne
# usa uno preinstallato altrove.
CHROMIUM_PATH = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH") or None
PT_PER_MM = 72 / 25.4

# Etichetta adesiva fisica su cui si stampa.
ETICHETTA_LATO_CORTO_MM = 105.0
ETICHETTA_LATO_LUNGO_MM = 148.0
ALLARGAMENTO_MINIMO_MM = 3.0

BADGE_H_MM = 14.4          # altezza preferita, affiancati
BADGE_W_MAX_MM = 32.0      # larghezza massima, impilati
MISURA_MINIMA_MM = 8.0     # sotto questa i badge diventano illeggibili
MARGINE_MM = 2.0           # aria che resta comunque fra badge e contenuto
GAP_BADGE_MM = 3.0
DPI_ANALISI = 100
SOGLIA_BIANCO = 245        # 0 nero, 255 bianco
PASSO_RICERCA_PX = 2

# Rapporti larghezza/altezza dei due badge: borsa 851x681, scritta 568x257.
RAPPORTO_BORSA = 851 / 681
RAPPORTO_SCRITTA = 568 / 257


def allarga_a_etichetta(page: pymupdf.Page) -> bool:
    """Porta il lato lungo della pagina alla misura dell'etichetta fisica.

    Serve per le LDV più corte del 10x15 su cui vengono stampate: lo spazio
    guadagnato è pulito per definizione, quindi ci stanno i badge senza
    coprire niente.
    """
    larghezza_mm = page.rect.width / PT_PER_MM
    altezza_mm = page.rect.height / PT_PER_MM
    orizzontale = larghezza_mm >= altezza_mm
    target_mm = ETICHETTA_LATO_LUNGO_MM if orizzontale else ETICHETTA_LATO_CORTO_MM

    if target_mm - larghezza_mm < ALLARGAMENTO_MINIMO_MM:
        return False

    box = page.mediabox
    page.set_mediabox(pymupdf.Rect(box.x0, box.y0, box.x0 + target_mm * PT_PER_MM, box.y1))
    return True


def mappa_occupato(page: pymupdf.Page) -> tuple[list[list[int]], int, int, float]:
    """Somme cumulate per colonna dei pixel scuri: permette di chiedere in
    fretta se una porzione verticale di una colonna è tutta bianca."""
    pix = page.get_pixmap(dpi=DPI_ANALISI, colorspace=pymupdf.csGRAY)
    larghezza, altezza, campioni = pix.width, pix.height, pix.samples

    cumulate = [[0] * larghezza for _ in range(altezza + 1)]
    for y in range(altezza):
        riga = campioni[y * larghezza:(y + 1) * larghezza]
        sopra, corrente = cumulate[y], cumulate[y + 1]
        for x in range(larghezza):
            corrente[x] = sopra[x] + (riga[x] < SOGLIA_BIANCO)
    return cumulate, larghezza, altezza, 25.4 / DPI_ANALISI


def cerca_riquadro(
    cumulate: list[list[int]],
    larghezza_px: int,
    altezza_px: int,
    mm_px: float,
    serve_w_mm: float,
    serve_h_mm: float,
) -> tuple[float, float, float, float] | None:
    """Riquadro bianco più in basso che contiene le misure richieste."""
    box_h_px = ceil((serve_h_mm + 2 * MARGINE_MM) / mm_px)
    box_w_px = ceil((serve_w_mm + 2 * MARGINE_MM) / mm_px)
    if box_h_px > altezza_px or box_w_px > larghezza_px:
        return None

    for y in range(altezza_px - box_h_px, -1, -PASSO_RICERCA_PX):
        sopra, sotto = cumulate[y], cumulate[y + box_h_px]
        inizio, migliore = 0, (0, 0)
        for x in range(larghezza_px + 1):
            if x < larghezza_px and sotto[x] == sopra[x]:
                continue
            if x - inizio > migliore[1] - migliore[0]:
                migliore = (inizio, x)
            inizio = x + 1

        if migliore[1] - migliore[0] >= box_w_px:
            centro = (migliore[0] + migliore[1]) / 2
            return (
                (centro - box_w_px / 2) * mm_px,
                y * mm_px,
                box_w_px * mm_px,
                box_h_px * mm_px,
            )
    return None


def posiziona_badge(page: pymupdf.Page) -> dict | None:
    """Decide dove e come mettere i badge, leggendo la pagina.

    Prima prova ad affiancarli alla misura preferita, che è quella già
    approvata sulle LDV GLS. Se non ci stanno prova a impilarli (è il caso
    delle pagine allargate, dove lo spazio guadagnato è una striscia stretta
    e alta), e infine ad affiancarli più piccoli. Ritorna le misure per il
    CSS della maschera, oppure None se non c'è spazio decente.
    """
    cumulate, larghezza_px, altezza_px, mm_px = mappa_occupato(page)

    def affiancati(badge_h: float):
        larghezza = badge_h * (RAPPORTO_BORSA + RAPPORTO_SCRITTA) + GAP_BADGE_MM
        riquadro = cerca_riquadro(cumulate, larghezza_px, altezza_px, mm_px, larghezza, badge_h)
        if riquadro is None:
            return None
        return {"riquadro": riquadro, "direzione": "row", "badge_h": badge_h, "badge_w": None}

    def impilati(badge_w: float):
        altezza = badge_w / RAPPORTO_BORSA + badge_w / RAPPORTO_SCRITTA + GAP_BADGE_MM
        riquadro = cerca_riquadro(cumulate, larghezza_px, altezza_px, mm_px, badge_w, altezza)
        if riquadro is None:
            return None
        return {"riquadro": riquadro, "direzione": "column", "badge_h": None, "badge_w": badge_w}

    scelta = affiancati(BADGE_H_MM)
    if scelta is not None:
        return scelta

    larghezza = BADGE_W_MAX_MM
    while larghezza >= MISURA_MINIMA_MM * 2:
        scelta = impilati(larghezza)
        if scelta is not None:
            return scelta
        larghezza -= 2.0

    altezza = BADGE_H_MM - 1.0
    while altezza >= MISURA_MINIMA_MM:
        scelta = affiancati(altezza)
        if scelta is not None:
            return scelta
        altezza -= 1.0

    return None


def genera_overlay_pdf(page, width_mm: float, height_mm: float, piano: dict, out_path: Path) -> None:
    sinistra, alto, larghezza, altezza = piano["riquadro"]
    badge_h = f"{piano['badge_h']}mm" if piano["badge_h"] else "auto"
    badge_w = f"{piano['badge_w']}mm" if piano["badge_w"] else "auto"
    override_css = (
        f":root {{ --page-w: {width_mm}mm; --page-h: {height_mm}mm; "
        f"--box-left: {sinistra}mm; --box-top: {alto}mm; "
        f"--box-w: {larghezza}mm; --box-h: {altezza}mm; "
        f"--direzione: {piano['direzione']}; "
        f"--badge-h: {badge_h}; --badge-w: {badge_w}; "
        f"--gap-badge: {GAP_BADGE_MM}mm; }}"
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
    """Brandizza ogni pagina che ha spazio. Ritorna quante ne ha fatte."""
    doc = pymupdf.open(input_pdf)
    overlay_paths: list[Path] = []
    brandizzate = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM_PATH)
        browser_page = browser.new_page()
        browser_page.goto(TEMPLATE.resolve().as_uri())

        for pdf_page in doc:
            if allarga_a_etichetta(pdf_page):
                print(f"  pagina {pdf_page.number + 1}: allargata a {pdf_page.rect.width / PT_PER_MM:.0f}mm")

            piano = posiziona_badge(pdf_page)
            if piano is None:
                print(f"  pagina {pdf_page.number + 1}: nessuno spazio libero, la lascio com'è")
                continue

            w_mm = pdf_page.rect.width / PT_PER_MM
            h_mm = pdf_page.rect.height / PT_PER_MM
            overlay_path = tmp_dir / f"_overlay_{pdf_page.number}.pdf"
            genera_overlay_pdf(browser_page, w_mm, h_mm, piano, overlay_path)
            overlay_paths.append(overlay_path)

            overlay_doc = pymupdf.open(overlay_path)
            pdf_page.show_pdf_page(pdf_page.rect, overlay_doc, 0)
            overlay_doc.close()
            brandizzate += 1

        browser.close()

    doc.save(output_pdf)
    doc.close()
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
