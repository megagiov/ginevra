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

# Registro delle LDV già stampate (accanto agli script). Serve per avvisarti
# se chiedi di nuovo la stessa spedizione.
REGISTRO = Path(__file__).resolve().parent / "stampate.json"

# Risoluzione della testina della PL50E (203 dpi; metti 300 se la tua è a 300).
# Il PDF viene convertito noi a questa risoluzione esatta, in bianco e nero
# puro senza sfumature: così il driver non retina e barcode e testi escono
# netti invece che sgranati.
DPI_STAMPANTE = 203
SOGLIA_NERO = 160  # 0-255: più alto = più nero (testi più spessi)


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

    # Rasterizza noi, pixel per pixel della testina, senza antialiasing.
    pymupdf.TOOLS.set_aa_level(0)
    finale = pymupdf.open()
    for pag in out:
        pix = pag.get_pixmap(dpi=DPI_STAMPANTE, colorspace=pymupdf.csGRAY, alpha=False)
        tabella = bytes(0 if v < SOGLIA_NERO else 255 for v in range(256))
        bw = pymupdf.Pixmap(pymupdf.csGRAY, pix.width, pix.height, pix.samples.translate(tabella), False)
        fp = finale.new_page(width=pag.rect.width, height=pag.rect.height)
        fp.insert_image(fp.rect, pixmap=bw)
    out.close()
    out = finale
    dest = Path(tempfile.gettempdir()) / (path.stem + "_stampa.pdf")
    out.save(dest)
    out.close()
    src.close()
    return dest


_cache: dict = {}


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


def riscalda() -> None:
    """Cerca SumatraPDF e la stampante subito, all'avvio dell'osservatore,
    così la prima LDV non aspetta (PowerShell ci mette qualche secondo)."""
    _cache["sumatra"] = trova_sumatra()
    _cache["stampante"] = trova_stampante()
    if not _cache["sumatra"]:
        print("Attenzione: SumatraPDF non trovato (rilancia installa.bat).")
    if not _cache["stampante"]:
        print(f"Attenzione: stampante '{STAMPANTE}' non trovata in Windows.")
    else:
        print(f"Stampante: {_cache['stampante']}")


def chiave_spedizione(path: Path) -> str:
    """Numero spedizione dal nome (52314.pdf, 52314 (1).pdf, 49313-1-1-...).
    Se il nome non lo contiene, usa l'impronta del contenuto."""
    import hashlib
    import re

    m = re.match(r"^(\d+)", path.stem)
    if m:
        return m.group(1)
    return "file-" + hashlib.sha1(path.read_bytes()).hexdigest()[:12]


def leggi_registro() -> dict:
    import json

    try:
        return json.loads(REGISTRO.read_text(encoding="utf-8"))
    except Exception:
        return {}


def segna_stampata(chiave: str) -> None:
    import json
    from datetime import datetime

    reg = leggi_registro()
    reg[chiave] = datetime.now().isoformat(timespec="seconds")
    # tieni solo le ultime 2000 per non far crescere il file all'infinito
    if len(reg) > 2000:
        reg = dict(sorted(reg.items(), key=lambda kv: kv[1])[-2000:])
    try:
        REGISTRO.write_text(json.dumps(reg, indent=1), encoding="utf-8")
    except Exception as e:
        print(f"Non riesco a salvare il registro delle stampe: {e}")


def conferma_ristampa(chiave: str, quando: str) -> bool:
    """Avviso Sì/No. Predefinito: No (meglio non sprecare un'etichetta)."""
    from datetime import datetime

    try:
        dt = datetime.fromisoformat(quando).strftime("%d/%m alle %H:%M")
    except Exception:
        dt = quando
    testo = f"La LDV {chiave} è già stata stampata il {dt}.\n\nVuoi stamparla di nuovo?"
    try:
        import ctypes

        # 0x4 Sì/No, 0x20 punto interrogativo, 0x100 predefinito=No,
        # 0x10000 in primo piano, 0x40000 sempre sopra le altre finestre
        risposta = ctypes.windll.user32.MessageBoxW(0, testo, "LDV già stampata", 0x4 | 0x20 | 0x100 | 0x10000 | 0x40000)
        return risposta == 6
    except Exception:
        return input(testo.replace("\n", " ") + " [s/N] ").strip().lower() in ("s", "si", "sì", "y")


def apri(path: Path) -> None:
    try:
        os.startfile(path)  # type: ignore[attr-defined]
    except AttributeError:
        print(f"Apri manualmente: {path}")


def stampa(path: Path) -> bool:
    """Stampa sulla PL50E. Se non riesce apre il PDF e restituisce False.

    Se la stessa spedizione è già stata stampata chiede conferma: se rispondi
    No non stampa niente (restituisce False senza aprire il PDF)."""
    chiave = chiave_spedizione(path)
    precedente = leggi_registro().get(chiave)
    if precedente and not conferma_ristampa(chiave, precedente):
        print(f"LDV {chiave} già stampata: ristampa annullata.")
        return False
    if "sumatra" not in _cache:
        _cache["sumatra"] = trova_sumatra()
    sumatra = _cache["sumatra"]
    if not sumatra:
        print("SumatraPDF non trovato: rilancia installa.bat. Apro il PDF per stamparlo a mano.")
        apri(path)
        return False
    if "stampante" not in _cache:
        _cache["stampante"] = trova_stampante()  # una volta sola: PowerShell e' lento
    stampante = _cache["stampante"]
    if not stampante:
        print(f"Stampante '{STAMPANTE}' non trovata in Windows. Apro il PDF per stamparlo a mano.")
        apri(path)
        return False
    try:
        da_stampare = prepara_per_stampa(path)
    except Exception as e:
        print(f"Non riesco ad applicare il margine ({e}): stampo il file così com'è.")
        da_stampare = path
    import time

    t_prep = time.time()
    r = subprocess.run(
        [sumatra, "-print-to", stampante, "-print-settings", IMPOSTAZIONI, "-silent", str(da_stampare)],
        timeout=120,
    )
    print(f"  SumatraPDF ha impiegato {time.time() - t_prep:.1f}s")
    if r.returncode != 0:
        _cache.clear()  # ricontrolla la stampante al prossimo giro
        print("Stampa non riuscita. Apro il PDF per stamparlo a mano.")
        apri(path)
        return False
    segna_stampata(chiave)
    print(f"Inviato a {stampante}: {path.name}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: py stampa.py file.pdf")
        sys.exit(1)
    sys.exit(0 if stampa(Path(sys.argv[1])) else 2)
