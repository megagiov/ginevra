#!/usr/bin/env python3
"""Osserva una cartella (di default i Download) e brandizza da sola ogni
nuova LDV che ci arriva.

Uso:
    python3 osserva_cartella.py
    # oppure, per un'altra cartella:
    python3 osserva_cartella.py "C:\\Users\\NomeUtente\\Desktop\\LDV da stampare"

Lascia questa finestra aperta. Scarichi la LDV dal corriere come sempre
(finisce nei Download): dopo pochi secondi si apre da solo il PDF con i
loghi già dentro, pronto per Ctrl+P. Il PDF originale non viene toccato.

Viene elaborato solo ciò che è davvero una LDV da brandizzare, in due modi:

- **automatico**: i PDF che il gestionale nomina come
  `49313-1-1-20260916143218.pdf` (numero spedizione, due contatori, data e
  ora a 14 cifre);
- **a mano**: qualsiasi altro PDF che rinomini mettendoci dentro la parola
  `ldv`, se una volta ti serve brandizzarne uno fuori dal solito giro.

In più la pagina dev'essere piccola come un'etichetta corriere (entrambi i
lati sotto i 200mm): così se il gestionale nomina allo stesso modo anche
fatture o DDT in A4, quelli restano fuori.
"""

import os
import re
import sys
import time
from pathlib import Path

import fitz  # PyMuPDF

from applica_maschera import applica_maschera, ZONA_LDV_DEFAULT_MM, PT_PER_MM

POLL_SECONDS = 2
LATO_MASSIMO_ETICHETTA_MM = 200

# Il gestionale scarica le LDV come "49313-1-1-20260916143218.pdf". La coda
# " (1)" la aggiunge il browser quando riscarichi un file già presente.
NOME_GESTIONALE = re.compile(r"^\d+-\d+-\d+-\d{14}(\s*\(\d+\))?$")
PAROLA_MANUALE = "ldv"


def sembra_etichetta(path: Path) -> bool:
    try:
        doc = fitz.open(path)
        rect = doc[0].rect
        doc.close()
    except Exception:
        return False
    larghezza_mm = rect.width / PT_PER_MM
    altezza_mm = rect.height / PT_PER_MM
    return larghezza_mm < LATO_MASSIMO_ETICHETTA_MM and altezza_mm < LATO_MASSIMO_ETICHETTA_MM


def da_brandizzare(path: Path) -> bool:
    riconosciuto = bool(NOME_GESTIONALE.match(path.stem)) or PAROLA_MANUALE in path.stem.lower()
    return riconosciuto and sembra_etichetta(path)


def is_stable(path: Path) -> bool:
    """True se il file ha smesso di crescere (download/scrittura conclusi)."""
    try:
        size1 = path.stat().st_size
    except OSError:
        return False
    time.sleep(0.5)
    try:
        size2 = path.stat().st_size
    except OSError:
        return False
    return size1 == size2 and size1 > 0


def apri(path: Path) -> None:
    try:
        os.startfile(path)  # type: ignore[attr-defined]
    except AttributeError:
        print(f"Apri manualmente: {path}")


def osserva(cartella: Path) -> None:
    print(f"Osservo la cartella: {cartella}")
    print("Lascia aperta questa finestra. Salva qui le LDV da brandizzare.")
    visti = {p.name for p in cartella.glob("*.pdf")}
    tmp_dir = Path(os.environ.get("TEMP") or os.environ.get("TMPDIR") or "/tmp")

    while True:
        time.sleep(POLL_SECONDS)
        for pdf in cartella.glob("*.pdf"):
            if pdf.name in visti:
                continue
            if pdf.stem.endswith("_brandizzato"):
                visti.add(pdf.name)
                continue
            output = pdf.with_name(pdf.stem + "_brandizzato.pdf")
            if output.exists():
                visti.add(pdf.name)
                continue
            if not is_stable(pdf):
                continue  # non ancora scritto del tutto, ricontrolla al giro dopo

            visti.add(pdf.name)
            if not da_brandizzare(pdf):
                continue  # non è una LDV del gestionale, lo lascio stare

            print(f"Nuova LDV: {pdf.name} -> elaboro...")
            try:
                applica_maschera(pdf, output, ZONA_LDV_DEFAULT_MM, tmp_dir)
                print(f"Fatto: {output.name}")
                apri(output)
            except Exception as e:
                print(f"Errore su {pdf.name}: {e}")


def main() -> None:
    cartella = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads"
    cartella.mkdir(parents=True, exist_ok=True)
    osserva(cartella)


if __name__ == "__main__":
    main()
