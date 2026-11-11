#!/usr/bin/env python3
"""Osserva una cartella (di default i Download) e brandizza da sola ogni
nuova LDV che ci arriva.

Uso:
    python3 osserva_cartella.py
    # oppure, per un'altra cartella:
    python3 osserva_cartella.py "C:\\Users\\NomeUtente\\Desktop\\LDV da stampare"

Lascia questa finestra aperta. Scarichi la LDV dal corriere come sempre
(finisce nei Download): dopo pochi secondi il PDF con i loghi già dentro
esce da solo dalla stampante PL50E. Il PDF originale non viene toccato.

Viene elaborato solo ciò che è davvero una LDV da brandizzare, in due modi:

- **automatico**: i PDF che il gestionale nomina come `52314.pdf` (solo il
  numero spedizione) o, nel vecchio formato, `49313-1-1-20260916143218.pdf`;
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

import pymupdf

from applica_maschera import applica_maschera, SessioneBrowser, PT_PER_MM
from stampa import stampa, riscalda

POLL_SECONDS = 0.3
GIORNI_RICERCA = 3  # ignora i PDF più vecchi di così
LATO_MASSIMO_ETICHETTA_MM = 200

# Il gestionale scarica le LDV con due formati di nome:
#   - vecchio: "49313-1-1-20260916143218.pdf" (spedizione, contatori, data-ora)
#   - nuovo:   "52314.pdf" (solo il numero spedizione)
# La coda " (1)" la aggiunge il browser quando riscarichi un file già presente.
NOME_GESTIONALE = re.compile(r"^\d+(-\d+-\d+-\d{14})?(\s*\(\d+\))?$")
PAROLA_MANUALE = "ldv"


def sembra_etichetta(path: Path) -> bool:
    try:
        doc = pymupdf.open(path)
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
    time.sleep(0.2)
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


def nome_candidato(nome: str) -> bool:
    """Scarto subito, dal solo nome, tutto ciò che non può essere una LDV."""
    if not nome.lower().endswith(".pdf"):
        return False
    stem = nome[:-4]
    if stem.endswith("_brandizzato"):
        return False
    return bool(NOME_GESTIONALE.match(stem)) or PAROLA_MANUALE in stem.lower()


def elenco_pdf(cartella: Path) -> list[tuple[Path, float, int]]:
    """LDV candidate degli ultimi GIORNI_RICERCA giorni: (percorso, data, dimensione).
    Filtra per nome e per data prima di guardare i file, così una cartella
    Download piena di vecchi PDF non rallenta niente."""
    limite = time.time() - GIORNI_RICERCA * 86400
    risultato = []
    try:
        with os.scandir(cartella) as it:
            for e in it:
                if not nome_candidato(e.name):
                    continue
                try:
                    st = e.stat()
                except OSError:
                    continue
                if st.st_mtime >= limite:
                    risultato.append((Path(e.path), st.st_mtime, st.st_size))
    except OSError:
        pass
    return risultato


def osserva(cartella: Path) -> None:
    print(f"Osservo la cartella: {cartella}")
    print("Lascia aperta questa finestra. Salva qui le LDV da brandizzare.")
    visti = {p.name: m for p, m, _ in elenco_pdf(cartella)}
    dimensioni: dict[str, int] = {}
    tmp_dir = Path(os.environ.get("TEMP") or os.environ.get("TMPDIR") or "/tmp")
    print("Avvio il motore grafico (una volta sola)...")
    sessione = SessioneBrowser()
    riscalda()
    print("Pronto.")

    while True:
        time.sleep(POLL_SECONDS)
        for pdf, mtime, size in elenco_pdf(cartella):
            if visti.get(pdf.name) == mtime:
                continue
            output = pdf.with_name(pdf.stem + "_brandizzato.pdf")
            if size == 0 or dimensioni.get(pdf.name) != size:
                dimensioni[pdf.name] = size
                continue  # sta ancora venendo scritto: ricontrollo al giro dopo

            visti[pdf.name] = mtime
            if not da_brandizzare(pdf):
                continue  # non è una LDV del gestionale, lo lascio stare

            t0 = time.time()
            # secondi passati da quando il download è finito a quando l'ho visto
            print(f"Nuova LDV: {pdf.name} (vista dopo {max(0, t0 - mtime):.1f}s) -> elaboro...")
            try:
                applica_maschera(pdf, output, tmp_dir, sessione)
                t1 = time.time()
                stampa(output)
                t2 = time.time()
                print(f"Tempi: brandizzazione {t1 - t0:.1f}s, invio alla stampante {t2 - t1:.1f}s, totale {t2 - t0:.1f}s")
            except Exception as e:
                print(f"Errore su {pdf.name}: {e}")


def main() -> None:
    cartella = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads"
    cartella.mkdir(parents=True, exist_ok=True)
    osserva(cartella)


if __name__ == "__main__":
    main()
