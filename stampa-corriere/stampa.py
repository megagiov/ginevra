#!/usr/bin/env python3
"""Stampa diretta di un PDF sulla stampante etichette PL50E, senza finestre.

Usa SumatraPDF in modalità silenziosa, a dimensioni reali (100%, niente
"adatta alla pagina"), così barcode e badge restano nella misura giusta.

Uso:
    py stampa.py etichetta_brandizzato.pdf

Se la stampa diretta non riesce (stampante spenta, SumatraPDF mancante...)
il PDF viene aperto come prima, così puoi stamparlo a mano con Ctrl+P.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Parte del nome della stampante come appare in Windows. Basta che sia
# contenuta nel nome vero (es. "PL50E Label", "PL50E(USB)"...).
STAMPANTE = "PL50E"

# Impostazioni SumatraPDF: dimensioni reali, una copia.
IMPOSTAZIONI = "noscale,1x"

# --- Regolazioni di stampa (in mm) -----------------------------------------
# Bordo bianco tenuto libero su tutti i lati: il contenuto viene
# rimpicciolito in proporzione per starci dentro, centrato.
MARGINE_MM = 4
# Se la stampa esce ancora spostata, correggi qui.
# SPOSTA_X_MM positivo = sposta a destra, negativo = a sinistra.
# SPOSTA_Y_MM positivo = sposta in basso, negativo = in alto.
SPOSTA_X_MM = 0
SPOSTA_Y_MM = 0

PT_PER_MM = 72 / 25.4


def prepara_per_stampa(path: Path) -> Path:
    """Crea una copia temporanea con margine e centratura applicati."""
    import tempfile
    import pymupdf

    src = pymupdf.open(path)
    out = pymupdf.open()
    m = MARGINE_MM * PT_PER_MM
    dx = SPOSTA_X_MM * PT_PER_MM
    dy = SPOSTA_Y_MM * PT_PER_MM
    for i, pag in enumerate(src):
        r = pag.rect
        nuova = out.new_page(width=r.width, height=r.height)
        zona = pymupdf.Rect(m + dx, m + dy, r.width - m + dx, r.height - m + dy)
        nuova.show_pdf_page(zona, src, i, keep_proportion=True)
    dest = Path(tempfile.gettempdir()) / (path.stem + "_stampa.pdf")
    out.save(dest)
    out.close()
    src.close()
    return dest


def trova_sumatra() -> str | None:
    qui = Path(__file__).resolve().parent
    candidati = [
        qui / "SumatraPDF.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "SumatraPDF" / "SumatraPDF.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "SumatraPDF" / "SumatraPDF.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "SumatraPDF" / "SumatraPDF.exe",
    ]
    for c in candidati:
        if c.is_file():
            return str(c)
    return shutil.which("SumatraPDF") or shutil.which("SumatraPDF.exe")


def trova_stampante() -> str | None:
    """Nome esatto della stampante che contiene STAMPANTE nel nome."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Printer | Select-Object -ExpandProperty Name"],
            capture_output=True, text=True, timeout=20,
        ).stdout
    except Exception:
        return None
    for nome in out.splitlines():
        if STAMPANTE.lower() in nome.strip().lower():
            return nome.strip()
    return None


def apri(path: Path) -> None:
    try:
        os.startfile(path)  # type: ignore[attr-defined]
    except AttributeError:
        print(f"Apri manualmente: {path}")


def stampa(path: Path) -> bool:
    """Stampa sulla PL50E. Se non riesce apre il PDF e restituisce False."""
    sumatra = trova_sumatra()
    if not sumatra:
        print("SumatraPDF non trovato: rilancia installa.bat. Apro il PDF per stamparlo a mano.")
        apri(path)
        return False
    stampante = trova_stampante()
    if not stampante:
        print(f"Stampante '{STAMPANTE}' non trovata in Windows. Apro il PDF per stamparlo a mano.")
        apri(path)
        return False
    try:
        da_stampare = prepara_per_stampa(path)
    except Exception as e:
        print(f"Non riesco ad applicare il margine ({e}): stampo il file così com'è.")
        da_stampare = path
    r = subprocess.run(
        [sumatra, "-print-to", stampante, "-print-settings", IMPOSTAZIONI, "-silent", str(da_stampare)],
        timeout=120,
    )
    if r.returncode != 0:
        print("Stampa non riuscita. Apro il PDF per stamparlo a mano.")
        apri(path)
        return False
    print(f"Inviato a {stampante}: {path.name}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: py stampa.py file.pdf")
        sys.exit(1)
    sys.exit(0 if stampa(Path(sys.argv[1])) else 2)
