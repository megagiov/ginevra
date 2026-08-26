#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
START UP® — generatore del catalogo.

Legge l'archivio in `dati/` e impagina due PDF pronti per la stampa:

    catalogo-licenze.pdf    per le aziende che possono prendere una categoria
    catalogo-prodotti.pdf   il lookbook delle linee gia' prodotte in licenza

Tutto in locale: nessun servizio a pagamento, nessuna API, nessun credito.
Il marchio finisce nel PDF come tracciato vettoriale, non come immagine.

    python3 genera.py              entrambi i cataloghi
    python3 genera.py licenze      solo il catalogo licenze
    python3 genera.py prodotti     solo il lookbook
    python3 genera.py --anno 2027  cambia l'anno in copertina
"""

import json
import math
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

import yaml
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rlcanvas
from reportlab.pdfgen.canvas import FILL_EVEN_ODD

QUI = Path(__file__).resolve().parent
DATI = QUI / "dati"
FOTO = QUI / "foto"
FONT = QUI / "font"
OUT = QUI / "out"

# ---------------------------------------------------------------- geometria --

MM = 72 / 25.4
LARG, ALT = 210 * MM, 297 * MM          # A4 verticale
MSX = MDX = 18 * MM
MSU = 16 * MM
MGIU = 15 * MM
GUT = 4 * MM
NCOL = 12
UTILE = LARG - MSX - MDX
COLW = (UTILE - (NCOL - 1) * GUT) / NCOL


def cx(i):
    """Ascissa della colonna i (0-based)."""
    return MSX + i * (COLW + GUT)


def cw(n):
    """Larghezza di n colonne contigue, gutter inclusi."""
    return n * COLW + (n - 1) * GUT


# ------------------------------------------------------------------- font --
# Tutti SIL OFL, scaricati da jsdelivr: i raw di github.com possono essere
# bloccati da un proxy, il CDN serve gli stessi file (vedi video-prodotto).

SORGENTI = {
    "ZillaSlab":       "ofl/zillaslab/ZillaSlab-Regular.ttf",
    "ZillaSlab-Bold":  "ofl/zillaslab/ZillaSlab-Bold.ttf",
    "Barlow":          "ofl/barlow/Barlow-Regular.ttf",
    "Barlow-Medium":   "ofl/barlow/Barlow-Medium.ttf",
    "Barlow-SemiBold": "ofl/barlow/Barlow-SemiBold.ttf",
    "Barlow-Bold":     "ofl/barlow/Barlow-Bold.ttf",
    "PlexMono":        "ofl/ibmplexmono/IBMPlexMono-Medium.ttf",
}
CDN = "https://cdn.jsdelivr.net/gh/google/fonts@main/"


def carica_font():
    FONT.mkdir(exist_ok=True)
    for nome, percorso in SORGENTI.items():
        f = FONT / (nome + ".ttf")
        if not f.exists():
            print(f"  scarico {nome}...")
            urllib.request.urlretrieve(CDN + percorso, f)
        pdfmetrics.registerFont(TTFont(nome, str(f)))


# ------------------------------------------------------------------ marchio --

class Bollo:
    """Il bollo circolare START UP, ridisegnato come tracciato vettoriale."""

    def __init__(self, percorso):
        d = json.loads(Path(percorso).read_text())
        self.paths = d["paths"]
        self.prop = d["proporzione"]

    def disegna(self, c, x, y, lato, colore):
        """x, y = angolo in basso a sinistra. `lato` e' la larghezza."""
        h = lato / self.prop
        c.saveState()
        c.setFillColor(colore)
        for pt in self.paths:
            p = c.beginPath()
            ultimo = None
            for cmd in pt["cmds"]:
                if cmd[0] != "l":
                    continue
                x1, y1, x2, y2 = cmd[1:5]
                a = (x + x1 * lato, y + y1 * h)
                b = (x + x2 * lato, y + y2 * h)
                # segmento staccato dal precedente: comincia un sottotracciato
                if ultimo is None or abs(ultimo[0] - a[0]) > 1e-4 or abs(ultimo[1] - a[1]) > 1e-4:
                    if ultimo is not None:
                        p.close()
                    p.moveTo(*a)
                p.lineTo(*b)
                ultimo = b
            p.close()
            c.drawPath(p, stroke=0, fill=1, fillMode=FILL_EVEN_ODD)
        c.restoreState()


# --------------------------------------------------------- testo e primitive --

def larg(s, font, size, tracking=0.0):
    return pdfmetrics.stringWidth(s, font, size) + tracking * max(0, len(s) - 1)


def scrivi(c, x, y, s, font, size, colore, tracking=0.0, allinea="sx"):
    if not s:
        return
    w = larg(s, font, size, tracking)
    if allinea == "dx":
        x -= w
    elif allinea == "centro":
        x -= w / 2
    t = c.beginText(x, y)
    t.setFont(font, size)
    t.setFillColor(colore)
    # La spaziatura va sempre dichiarata, anche a zero: reportlab la tiene nello
    # stato del canvas e senza il reset l'ultimo valore usato si trascina sui
    # testi successivi, allargandoli oltre il margine.
    t.setCharSpace(tracking)
    t.textOut(s)
    c.drawText(t)


def spezza(s, font, size, larghezza, tracking=0.0):
    righe, riga = [], ""
    for parola in (s or "").split():
        prova = (riga + " " + parola).strip()
        if larg(prova, font, size, tracking) <= larghezza or not riga:
            riga = prova
        else:
            righe.append(riga)
            riga = parola
    if riga:
        righe.append(riga)
    return righe


def blocco(c, x, y, s, font, size, interlinea, larghezza, colore,
           tracking=0.0, allinea="sx", max_righe=None):
    """Scrive un paragrafo andando a capo. Restituisce la y sotto l'ultima riga."""
    righe = spezza(s, font, size, larghezza, tracking)
    if max_righe:
        righe = righe[:max_righe]
    for r in righe:
        scrivi(c, x, y, r, font, size, colore, tracking, allinea)
        y -= interlinea
    return y


def passo(y_alto, y_basso, n, minimo=0):
    """Distribuisce n voci sull'altezza disponibile invece di usare un passo
    fisso: senza questo le pagine con pochi elementi restano vuote in basso."""
    return max(minimo, (y_alto - y_basso) / n)


PIEDE_Y = None  # calcolata a runtime: quota sopra il filetto del piede


def filetto(c, x, y, w, colore, spessore=0.5):
    c.saveState()
    c.setStrokeColor(colore)
    c.setLineWidth(spessore)
    c.line(x, y, x + w, y)
    c.restoreState()


def occhiello(c, x, y, s, colore, allinea="sx"):
    """Etichetta piccola in mono spaziato: classi, sezioni, campi."""
    scrivi(c, x, y, s.upper(), "PlexMono", 7, colore, 1.1, allinea)


FINESTRE = []       # inventario riempito a ogni impaginazione


def finestra_foto(c, x, y, w, h, etichetta="", percorso=""):
    """Piazza la foto se c'e'. Se manca, lascia la finestra con la misura
    esatta dello scatto che serve: il catalogo si stampa lo stesso."""
    FINESTRE.append({"etichetta": etichetta, "mm_w": w / MM, "mm_h": h / MM,
                     "file": percorso})
    f = FOTO / percorso if percorso else None
    if f and f.exists():
        try:
            # Riempie la finestra e taglia il resto: una foto "adattata" lascia
            # bande vuote e in un catalogo si vedono tutte.
            img = ImageReader(str(f))
            iw, ih = img.getSize()
            scala = max(w / iw, h / ih)
            dw, dh = iw * scala, ih * scala
            c.saveState()
            taglio = c.beginPath()
            taglio.rect(x, y, w, h)
            c.clipPath(taglio, stroke=0, fill=0)
            c.drawImage(img, x - (dw - w) / 2, y - (dh - h) / 2, dw, dh, mask="auto")
            c.restoreState()
            return True
        except Exception as e:                       # PIL assente o file rotto
            print(f"  ! foto non inserita ({percorso}): {e}")
    c.saveState()
    c.setFillColor(CARTA_CALDA)
    c.rect(x, y, w, h, stroke=0, fill=1)
    c.setStrokeColor(FILETTO)
    c.setLineWidth(0.6)
    c.setDash(3, 3)
    c.rect(x, y, w, h, stroke=1, fill=0)
    c.setDash()
    # La didascalia va mandata a capo dentro la finestra: su una finestra
    # stretta una riga sola deborda sulla colonna accanto.
    px = round(w / MM / 25.4 * 300)
    py = round(h / MM / 25.4 * 300)
    cxm = x + w / 2
    utile = w - 6 * MM
    m1 = f"{w/MM:.0f} × {h/MM:.0f} mm"
    m2 = f"{px} × {py} px a 300 dpi"
    unica = m1 + " · " + m2
    misure = [unica] if larg(unica, "PlexMono", 6.5, 0.4) <= utile else [m1, m2]
    et = spezza((etichetta or "foto").upper(), "PlexMono", 7, utile, 1.1)
    alto = len(et) * 4.2 * MM + 2 * MM + len(misure) * 3.6 * MM
    yy = y + h / 2 + alto / 2 - 3 * MM
    for r in et:
        scrivi(c, cxm, yy, r, "PlexMono", 7, GRIGIO, 1.1, "centro")
        yy -= 4.2 * MM
    yy -= 2 * MM
    for r in misure:
        scrivi(c, cxm, yy, r, "PlexMono", 6.5, GRIGIO, 0.4, "centro")
        yy -= 3.6 * MM
    c.restoreState()
    return False


def pastiglia(c, x, y, testo, sfondo, testo_col, altezza=5.2 * MM):
    """Etichetta piena: stato di una categoria, canale di vendita."""
    w = larg(testo.upper(), "PlexMono", 6.8, 1.0) + 5 * MM
    c.saveState()
    c.setFillColor(sfondo)
    c.roundRect(x, y, w, altezza, altezza / 2, stroke=0, fill=1)
    c.restoreState()
    scrivi(c, x + 2.5 * MM, y + altezza / 2 - 2.3, testo.upper(),
           "PlexMono", 6.8, testo_col, 1.0)
    return w


# ------------------------------------------------------------------ pagina --

def testata(c, sezione):
    """Filo alto: marchio a sinistra, sezione a destra. Restituisce la y del filetto."""
    y = ALT - MSU
    BOLLO.disegna(c, MSX, y - 4.6 * MM, 4.6 * MM, INCHIOSTRO)
    scrivi(c, MSX + 6.6 * MM, y - 3.5 * MM, "START UP" + M["simbolo_registrato"],
           "Barlow-SemiBold", 7.6, INCHIOSTRO, 0.5)
    occhiello(c, LARG - MDX, y - 3.5 * MM, sezione, GRIGIO, "dx")
    filetto(c, MSX, y - 7 * MM, UTILE, FILETTO)
    return y - 7 * MM


def piede(c, numero, nota=""):
    filetto(c, MSX, MGIU + 5 * MM, UTILE, FILETTO)
    scrivi(c, MSX, MGIU, nota, "Barlow", 7, GRIGIO)
    scrivi(c, LARG - MDX, MGIU, f"{numero:02d}", "PlexMono", 7.5, GRIGIO, 0.6, "dx")


def fondo(c, colore):
    c.saveState()
    c.setFillColor(colore)
    c.rect(0, 0, LARG, ALT, stroke=0, fill=1)
    c.restoreState()


# ------------------------------------------------------- pagine del catalogo --

def copertina(c, n, titolo, sottotitolo, anno):
    fondo(c, INCHIOSTRO)
    lato = 78 * MM
    BOLLO.disegna(c, (LARG - lato) / 2, ALT - 118 * MM, lato, CARTA)

    y = 118 * MM
    filetto(c, MSX, y, UTILE, colors.Color(1, 1, 1, 0.25))
    y -= 11 * MM
    occhiello(c, MSX, y, M["posizionamento"], colors.Color(1, 1, 1, 0.55))
    y -= 16 * MM
    for riga in spezza(titolo, "ZillaSlab-Bold", 40, cw(9)):
        scrivi(c, MSX, y, riga, "ZillaSlab-Bold", 40, CARTA)
        y -= 15 * MM
    y -= 1 * MM
    blocco(c, MSX, y, sottotitolo, "Barlow", 12.5, 17, cw(7),
           colors.Color(1, 1, 1, 0.72))

    y = MGIU + 6 * MM
    filetto(c, MSX, y + 7 * MM, UTILE, colors.Color(1, 1, 1, 0.25))
    occhiello(c, MSX, y, M["paese"], CARTA)
    scrivi(c, LARG / 2, y, str(anno), "PlexMono", 7, colors.Color(1, 1, 1, 0.55), 1.1, "centro")
    scrivi(c, LARG - MDX, y, M["dominio"], "PlexMono", 7,
           colors.Color(1, 1, 1, 0.55), 1.1, "dx")


def pag_sommario(c, n, voci):
    y = testata(c, "Sommario") - 18 * MM
    scrivi(c, MSX, y, "Sommario", "ZillaSlab-Bold", 30, INCHIOSTRO)
    y -= 16 * MM
    for etichetta, numero in voci:
        filetto(c, MSX, y + 6.5 * MM, UTILE, FILETTO)
        scrivi(c, MSX, y, etichetta, "Barlow-Medium", 11.5, INCHIOSTRO)
        scrivi(c, LARG - MDX, y, f"{numero:02d}", "PlexMono", 9, ACCENTO, 0.6, "dx")
        y -= 12 * MM
    piede(c, n)


def pag_apertura(c, n):
    y = testata(c, "Il marchio") - 22 * MM
    for riga in spezza(M["promessa"], "ZillaSlab-Bold", 34, cw(10)):
        scrivi(c, MSX, y, riga, "ZillaSlab-Bold", 34, INCHIOSTRO)
        y -= 13 * MM
    y -= 8 * MM
    y = blocco(c, MSX, y, M["abstract"], "Barlow", 11, 16.5, cw(7), INCHIOSTRO)

    # fascia dei numeri
    y -= 14 * MM
    filetto(c, MSX, y + 8 * MM, UTILE, FILETTO)
    passo = UTILE / len(M["numeri"])
    for i, num in enumerate(M["numeri"]):
        x = MSX + i * passo
        scrivi(c, x, y - 4 * MM, num["valore"], "ZillaSlab-Bold", 19, ACCENTO)
        blocco(c, x, y - 12 * MM, num["etichetta"], "Barlow", 8.5, 11.5,
               passo - 6 * MM, GRIGIO)

    # Quello che resta tra la fascia dei numeri e il blocco scuro e' la
    # finestra dell'immagine di apertura: si dimensiona su cio' che avanza.
    h = 62 * MM
    yb = MGIU + 12 * MM
    y_alto = y - 20 * MM
    y_basso = yb + h + 12 * MM
    if y_alto - y_basso > 35 * MM:
        finestra_foto(c, MSX, y_basso, UTILE, y_alto - y_basso,
                      "Immagine di apertura · prodotti in licenza")

    # blocco scuro con la chiusura commerciale
    c.saveState()
    c.setFillColor(INCHIOSTRO)
    c.rect(MSX, yb, UTILE, h, stroke=0, fill=1)
    c.restoreState()
    lato = 30 * MM
    BOLLO.disegna(c, LARG - MDX - lato - 12 * MM, yb + (h - lato) / 2, lato,
                  colors.Color(1, 1, 1, 0.16))
    ty = yb + h - 16 * MM
    occhiello(c, MSX + 12 * MM, ty, M["chiusura"]["azione"], colors.Color(1, 1, 1, 0.55))
    ty -= 12 * MM
    scrivi(c, MSX + 12 * MM, ty, M["chiusura"]["titolo"], "ZillaSlab-Bold", 20, CARTA)
    ty -= 9 * MM
    blocco(c, MSX + 12 * MM, ty, M["chiusura"]["testo"], "Barlow", 10.5, 15,
           cw(6), colors.Color(1, 1, 1, 0.72))
    piede(c, n)


def pag_chi_siamo(c, n):
    y = testata(c, "Chi siamo") - 20 * MM
    occhiello(c, MSX, y, "Chi siamo", ACCENTO)
    y -= 14 * MM
    for riga in spezza(M["chi_siamo"]["titolo"], "ZillaSlab-Bold", 26, cw(9)):
        scrivi(c, MSX, y, riga, "ZillaSlab-Bold", 26, INCHIOSTRO)
        y -= 10 * MM
    y -= 6 * MM
    for par in M["chi_siamo"]["paragrafi"]:
        y = blocco(c, MSX, y, par, "Barlow", 10, 15.5, cw(7), INCHIOSTRO)
        y -= 5 * MM

    y -= 8 * MM
    filetto(c, MSX, y + 10 * MM, UTILE, FILETTO)
    occhiello(c, MSX, y + 3 * MM, "Come lavoriamo con i licenziatari", GRIGIO)
    y -= 16 * MM
    p = passo(y, MGIU + 20 * MM, (len(M["metodo"]) + 1) // 2, 40 * MM)
    for i, v in enumerate(M["metodo"]):
        x = cx(0) if i % 2 == 0 else cx(6)
        yy = y - (i // 2) * p
        scrivi(c, x, yy, "—", "Barlow-Bold", 11, ACCENTO)
        scrivi(c, x + 6 * MM, yy, v["titolo"], "Barlow-SemiBold", 11.5, INCHIOSTRO)
        blocco(c, x + 6 * MM, yy - 8 * MM, v["testo"], "Barlow", 9.5, 14.5,
               cw(5) - 6 * MM, GRIGIO)
    piede(c, n)


def pag_argomenti(c, n):
    y = testata(c, "Perché il marchio") - 20 * MM
    occhiello(c, MSX, y, "Un solo marchio, sei classi coperte", ACCENTO)
    y -= 14 * MM
    scrivi(c, MSX, y, "Perché entrare in licenza", "ZillaSlab-Bold", 26, INCHIOSTRO)
    y -= 22 * MM
    p = passo(y, MGIU + 16 * MM, len(M["argomenti"]), 46 * MM)
    for v in M["argomenti"]:
        filetto(c, MSX, y + 12 * MM, UTILE, FILETTO)
        scrivi(c, MSX, y - 2 * MM, v["numero"], "ZillaSlab-Bold", 40,
               colors.HexColor("#D6CFC4"))
        scrivi(c, cx(2), y, v["titolo"], "ZillaSlab-Bold", 18, INCHIOSTRO)
        blocco(c, cx(2), y - 11 * MM, v["testo"], "Barlow", 10.5, 16, cw(8), GRIGIO)
        y -= p
    piede(c, n)


def pag_marchio(c, n):
    y = testata(c, "Il marchio") - 20 * MM
    occhiello(c, MSX, y, "Uso del segno", ACCENTO)
    y -= 14 * MM
    scrivi(c, MSX, y, M["marchio_pagina"]["titolo"], "ZillaSlab-Bold", 26, INCHIOSTRO)
    y -= 12 * MM
    y = blocco(c, MSX, y, M["marchio_pagina"]["testo"], "Barlow", 10, 15.5, cw(7), INCHIOSTRO)

    y -= 12 * MM
    riq = cw(6) - 3 * MM
    h = 96 * MM
    # positivo
    c.saveState()
    c.setFillColor(CARTA_CALDA)
    c.rect(MSX, y - h, riq, h, stroke=0, fill=1)
    c.restoreState()
    lato = 42 * MM
    BOLLO.disegna(c, MSX + (riq - lato) / 2, y - h + (h - lato) / 2 + 4 * MM, lato, INCHIOSTRO)
    occhiello(c, MSX + riq / 2, y - h + 8 * MM, M["marchio_pagina"]["positivo"], GRIGIO, "centro")
    # negativo
    x2 = MSX + riq + 6 * MM
    c.saveState()
    c.setFillColor(INCHIOSTRO)
    c.rect(x2, y - h, riq, h, stroke=0, fill=1)
    c.restoreState()
    BOLLO.disegna(c, x2 + (riq - lato) / 2, y - h + (h - lato) / 2 + 4 * MM, lato, CARTA)
    occhiello(c, x2 + riq / 2, y - h + 8 * MM, M["marchio_pagina"]["negativo"],
              colors.Color(1, 1, 1, 0.6), "centro")

    y = MGIU + 26 * MM
    filetto(c, MSX, y + 10 * MM, UTILE, FILETTO)
    occhiello(c, MSX, y, "I file consegnati con il contratto", GRIGIO)
    y -= 9 * MM
    blocco(c, MSX, y, M["contratto"][3]["testo"], "Barlow", 10, 15, cw(8), INCHIOSTRO)
    piede(c, n)


def pag_categorie_indice(c, n, categorie, prima_pagina):
    y = testata(c, "Categorie") - 20 * MM
    occhiello(c, MSX, y, "Otto categorie in licenza", ACCENTO)
    y -= 14 * MM
    scrivi(c, MSX, y, M["sottotitolo_catalogo"], "ZillaSlab-Bold", 26, INCHIOSTRO)
    y -= 12 * MM
    y = blocco(c, MSX, y,
               "Ogni categoria ha il suo contratto, la sua classe di deposito e il "
               "suo file marchio. Puoi partire da una sola categoria e aggiungerne "
               "altre dopo la prima stagione.",
               "Barlow", 10, 15.5, cw(7), INCHIOSTRO)
    y -= 16 * MM
    p = passo(y, MGIU + 14 * MM, len(categorie), 13 * MM)
    for i, cat in enumerate(categorie):
        filetto(c, MSX, y + p / 2, UTILE, FILETTO)
        scrivi(c, MSX, y, f"{i+1:02d}", "PlexMono", 8, colors.HexColor("#C9C2B7"), 0.6)
        scrivi(c, cx(1), y, cat["nome"], "Barlow-SemiBold", 12, INCHIOSTRO)
        scrivi(c, cx(5), y, f"Classe {cat['classe']}", "PlexMono", 8, GRIGIO, 0.6)
        if cat.get("_articoli"):
            scrivi(c, cx(7), y, f"{cat['_articoli']} articoli", "Barlow", 9.5, GRIGIO)
        stato = cat.get("stato", "")
        col = ACCENTO if stato == "libera" else GRIGIO
        scrivi(c, cx(9), y, stato.replace("-", " ").upper(), "PlexMono", 7, col, 1.0)
        scrivi(c, LARG - MDX, y, f"{prima_pagina + i // 2:02d}", "PlexMono", 8, GRIGIO, 0.6, "dx")
        y -= p
    piede(c, n)


def scheda_categoria(c, cat, x, y, w, h):
    """Una scheda categoria dentro il rettangolo dato (y = bordo superiore)."""
    wfoto = cw(5)
    finestra_foto(c, x, y - h, wfoto, h, f"{cat['nome']} · scatto prodotto")
    xt = x + wfoto + 8 * MM
    wt = w - wfoto - 8 * MM
    yy = y - 5 * MM
    occhiello(c, xt, yy, f"Classe {cat['classe']}", ACCENTO)
    yy -= 12 * MM
    scrivi(c, xt, yy, cat["nome"], "ZillaSlab-Bold", 22, INCHIOSTRO)
    yy -= 10 * MM
    yy = blocco(c, xt, yy, cat["descrizione"], "Barlow", 10.5, 15.5, wt, INCHIOSTRO)
    yy -= 6 * MM
    occhiello(c, xt, yy, "Applicazione del marchio", GRIGIO)
    yy -= 8 * MM
    yy = blocco(c, xt, yy, cat["applicazione"], "Barlow", 9.5, 14.5, wt, GRIGIO)
    yy -= 10 * MM
    stato = cat.get("stato", "")
    if stato:
        sfondo = ACCENTO if stato == "libera" else colors.HexColor("#E3DED6")
        col = CARTA if stato == "libera" else INCHIOSTRO
        etichetta = "Categoria libera" if stato == "libera" else stato.replace("-", " ")
        w_past = pastiglia(c, xt, yy, etichetta, sfondo, col)
        coda = cat.get("licenziatario") or (
            f"{cat['_articoli']} articoli in gamma tipo" if cat.get("_articoli") else "")
        if coda:
            scrivi(c, xt + w_past + 5 * MM, yy + 1.6 * MM, coda,
                   "Barlow-Medium", 9, GRIGIO)


def pag_categorie(c, n, coppia):
    y = testata(c, "Categorie") - 12 * MM
    h = 100 * MM
    for i, cat in enumerate(coppia):
        yy = y - i * (h + 16 * MM)
        scheda_categoria(c, cat, MSX, yy, UTILE, h)
        if i == 0 and len(coppia) > 1:
            filetto(c, MSX, yy - h - 8 * MM, UTILE, FILETTO)
    piede(c, n, "Categorie in licenza")


def pag_precedente(c, n, linea):
    y = testata(c, "Precedente commerciale") - 20 * MM
    occhiello(c, MSX, y, "Licenza in esercizio", ACCENTO)
    y -= 14 * MM
    scrivi(c, MSX, y, "Oltre 15 anni di distribuzione", "ZillaSlab-Bold", 26, INCHIOSTRO)
    y -= 12 * MM
    y = blocco(c, MSX, y, linea["descrizione"], "Barlow", 10, 15.5, cw(7), INCHIOSTRO)

    y -= 12 * MM
    ris = linea.get("risultato") or {}
    if ris.get("valore"):
        c.saveState()
        c.setFillColor(CARTA_CALDA)
        c.rect(MSX, y - 44 * MM, UTILE, 44 * MM, stroke=0, fill=1)
        c.restoreState()
        scrivi(c, MSX + 10 * MM, y - 26 * MM, ris["valore"], "ZillaSlab-Bold", 46, INCHIOSTRO)
        wnum = larg(ris["valore"], "ZillaSlab-Bold", 46)
        scrivi(c, MSX + 12 * MM + wnum, y - 26 * MM, ris.get("unita", ""),
               "ZillaSlab-Bold", 18, ACCENTO)
        blocco(c, MSX + 10 * MM, y - 34 * MM, ris.get("nota", ""), "Barlow", 10, 14,
               cw(6), GRIGIO)
        y -= 56 * MM

    for etichetta, valore in [("Gamma sviluppata", linea.get("gamma", "")),
                              ("Domanda generata", linea.get("domanda", ""))]:
        if not valore:
            continue
        filetto(c, MSX, y + 8 * MM, UTILE, FILETTO)
        occhiello(c, MSX, y, etichetta, GRIGIO)
        blocco(c, cx(4), y, valore, "Barlow", 10, 15, cw(8), INCHIOSTRO)
        y -= 26 * MM
    piede(c, n)


def pag_retail(c, n):
    y = testata(c, "Retail") - 20 * MM
    occhiello(c, MSX, y, M["retail"]["titolo"], ACCENTO)
    y -= 16 * MM
    for riga in spezza(M["retail"]["testo"], "ZillaSlab-Bold", 24, cw(9)):
        scrivi(c, MSX, y, riga, "ZillaSlab-Bold", 24, INCHIOSTRO)
        y -= 10 * MM
    y -= 8 * MM
    finestra_foto(c, MSX, y - 92 * MM, UTILE, 92 * MM, "Corner o negozio a insegna")
    y -= 104 * MM
    filetto(c, MSX, y + 8 * MM, UTILE, FILETTO)
    occhiello(c, MSX, y, "Materiali compresi", GRIGIO)
    blocco(c, cx(4), y, M["contratto"][3]["testo"], "Barlow", 10, 15, cw(8), INCHIOSTRO)
    piede(c, n)


def pag_percorso(c, n):
    y = testata(c, "Come si arriva alla licenza") - 20 * MM
    occhiello(c, MSX, y, "Tre passi", ACCENTO)
    y -= 14 * MM
    scrivi(c, MSX, y, "Come si arriva alla licenza", "ZillaSlab-Bold", 26, INCHIOSTRO)
    y -= 24 * MM
    p = passo(y, MGIU + 16 * MM, len(M["percorso"]), 44 * MM)
    for v in M["percorso"]:
        filetto(c, MSX, y + 12 * MM, UTILE, FILETTO)
        occhiello(c, MSX, y, v["passo"], ACCENTO)
        scrivi(c, cx(3), y, v["titolo"], "ZillaSlab-Bold", 18, INCHIOSTRO)
        blocco(c, cx(3), y - 11 * MM, v["testo"], "Barlow", 10.5, 16, cw(8), GRIGIO)
        y -= p
    piede(c, n)


def pag_contratto(c, n):
    y = testata(c, "Il contratto") - 20 * MM
    occhiello(c, MSX, y, "Cosa comprende", ACCENTO)
    y -= 14 * MM
    scrivi(c, MSX, y, "Cosa comprende il contratto", "ZillaSlab-Bold", 26, INCHIOSTRO)
    y -= 24 * MM
    righe = (len(M["contratto"]) + 1) // 2
    p = passo(y, MGIU + 20 * MM, righe, 52 * MM)
    for i, v in enumerate(M["contratto"]):
        x = cx(0) if i % 2 == 0 else cx(6)
        yy = y - (i // 2) * p
        filetto(c, x, yy + 10 * MM, cw(6) - 3 * MM, FILETTO)
        scrivi(c, x, yy, v["titolo"], "ZillaSlab-Bold", 16, INCHIOSTRO)
        blocco(c, x, yy - 10 * MM, v["testo"], "Barlow", 10, 15, cw(6) - 3 * MM, GRIGIO)
    piede(c, n)


def pag_retro(c, n):
    fondo(c, INCHIOSTRO)
    lato = 46 * MM
    BOLLO.disegna(c, MSX, ALT - 62 * MM, lato, CARTA)
    y = ALT - 92 * MM
    for riga in spezza(M["chiusura"]["titolo"] + " " + M["chiusura"]["testo"],
                       "ZillaSlab-Bold", 26, cw(9)):
        scrivi(c, MSX, y, riga, "ZillaSlab-Bold", 26, CARTA)
        y -= 10 * MM

    y -= 14 * MM
    filetto(c, MSX, y + 10 * MM, UTILE, colors.Color(1, 1, 1, 0.25))
    campi = [("Sede", M["contatti"].get("sede", "")),
             ("Email", M["contatti"].get("email", "")),
             ("Telefono", M["contatti"].get("telefono", "")),
             ("Sito", M["dominio"])]
    for etichetta, valore in campi:
        occhiello(c, MSX, y, etichetta, colors.Color(1, 1, 1, 0.5))
        scrivi(c, cx(3), y, valore or "—", "Barlow-Medium", 11, CARTA)
        y -= 12 * MM

    y = MGIU + 20 * MM
    filetto(c, MSX, y + 10 * MM, UTILE, colors.Color(1, 1, 1, 0.25))
    blocco(c, MSX, y,
           "START UP" + M["simbolo_registrato"] + " è un marchio registrato. "
           "Il segno, i file vettoriali e il manuale d'uso sono concessi in licenza "
           "e restano di proprietà del titolare.",
           "Barlow", 8.5, 12.5, cw(8), colors.Color(1, 1, 1, 0.55))
    scrivi(c, LARG - MDX, y, M["paese"], "PlexMono", 7,
           colors.Color(1, 1, 1, 0.55), 1.1, "dx")


# ---------------------------------------------------------- pagine lookbook --

def pag_lookbook_indice(c, n, linee, voci_gamma):
    y = testata(c, "Sommario") - 20 * MM
    occhiello(c, MSX, y, "Sommario", ACCENTO)
    y -= 14 * MM
    scrivi(c, MSX, y, M["sottotitolo_lookbook"], "ZillaSlab-Bold", 26, INCHIOSTRO)
    y -= 20 * MM

    occhiello(c, MSX, y, "In produzione", INCHIOSTRO)
    y -= 10 * MM
    for i, l in enumerate(linee):
        filetto(c, MSX, y + 7 * MM, UTILE, FILETTO)
        scrivi(c, MSX, y, l["nome"], "Barlow-SemiBold", 12, INCHIOSTRO)
        scrivi(c, cx(5), y, f"Classe {l.get('classe','')}", "PlexMono", 8, GRIGIO, 0.6)
        scrivi(c, cx(8), y, l.get("licenziatario", ""), "Barlow", 9.5, GRIGIO)
        scrivi(c, LARG - MDX, y, f"{n + 1 + i:02d}", "PlexMono", 8, ACCENTO, 0.6, "dx")
        y -= 14 * MM

    y -= 10 * MM
    occhiello(c, MSX, y, "Gamma tipo · proposta di sviluppo", INCHIOSTRO)
    y -= 10 * MM
    p = passo(y, MGIU + 14 * MM, len(voci_gamma), 12 * MM)
    for nome, classe, n_art, pagina in voci_gamma:
        filetto(c, MSX, y + p / 2, UTILE, FILETTO)
        scrivi(c, MSX, y, nome, "Barlow-Medium", 11.5, INCHIOSTRO)
        scrivi(c, cx(5), y, f"Classe {classe}", "PlexMono", 8, GRIGIO, 0.6)
        scrivi(c, cx(8), y, f"{n_art} articoli", "Barlow", 9.5, GRIGIO)
        scrivi(c, LARG - MDX, y, f"{pagina:02d}", "PlexMono", 8, GRIGIO, 0.6, "dx")
        y -= p
    piede(c, n)


def pag_linea(c, n, l):
    y = testata(c, l["nome"]) - 14 * MM
    occhiello(c, MSX, y, f"Classe {l.get('classe','')} · {l.get('categoria','')}", ACCENTO)
    y -= 14 * MM
    scrivi(c, MSX, y, l["nome"], "ZillaSlab-Bold", 32, INCHIOSTRO)
    y -= 10 * MM
    hf = 80 * MM
    finestra_foto(c, MSX, y - hf, UTILE, hf,
                  f"{l['nome']} · immagine di apertura", l.get("foto", ""))
    y -= hf + 12 * MM

    # Le due colonne scendono a velocita' diverse: quello che viene dopo parte
    # dalla piu' bassa delle due, altrimenti i blocchi si sovrappongono.
    y_desc = blocco(c, MSX, y, l.get("descrizione", ""), "Barlow", 10.5, 16,
                    cw(7), INCHIOSTRO)

    ris = l.get("risultato") or {}
    campi = [("Licenziatario", l.get("licenziatario", "")),
             ("Distribuzione", l.get("distribuzione", "")),
             ("Canali", ", ".join(l.get("canali") or [])),
             ("Mercati", ", ".join(l.get("mercati") or [])),
             ("Target", ", ".join(l.get("target") or [])),
             ("Varianti colore", str(l.get("varianti_colore") or "")),
             ("Risultato", " ".join(x for x in [ris.get("valore", ""),
                                                ris.get("unita", "")] if x))]
    xd = cx(8)
    y_dati = y
    for etichetta, valore in campi:
        if not valore:
            continue
        occhiello(c, xd, y_dati, etichetta, GRIGIO)
        y_dati = blocco(c, xd, y_dati - 5.5 * MM, valore, "Barlow-Medium", 9.5, 13,
                        cw(4), INCHIOSTRO)
        y_dati -= 4.5 * MM

    # Gamma e domanda restano nella colonna di sinistra, sotto la descrizione:
    # la colonna dei dati scende parecchio e li' finirebbero addosso.
    y = y_desc - 12 * MM
    for etichetta, valore in [("Gamma sviluppata", l.get("gamma", "")),
                              ("Domanda generata", l.get("domanda", ""))]:
        if not valore:
            continue
        filetto(c, MSX, y + 8 * MM, cw(7), FILETTO)
        occhiello(c, MSX, y, etichetta, GRIGIO)
        y = blocco(c, MSX, y - 8 * MM, valore, "Barlow", 10, 15, cw(7), INCHIOSTRO)
        y -= 12 * MM
    piede(c, n, l["nome"])


def pag_referenze(c, n, l):
    y = testata(c, l["nome"]) - 16 * MM
    occhiello(c, MSX, y, "Referenze", ACCENTO)
    y -= 12 * MM
    scrivi(c, MSX, y, "Referenze", "ZillaSlab-Bold", 24, INCHIOSTRO)
    y -= 14 * MM
    wcell = cw(4)
    hcell = 78 * MM
    for i, r in enumerate(l.get("referenze") or []):
        col = i % 3
        riga = i // 3
        x = cx(col * 4)
        yy = y - riga * (hcell + 10 * MM)
        finestra_foto(c, x, yy - 52 * MM, wcell, 52 * MM, r.get("codice") or "referenza",
                      r.get("foto", ""))
        scrivi(c, x, yy - 60 * MM, r.get("nome", ""), "Barlow-SemiBold", 10, INCHIOSTRO)
        scrivi(c, x, yy - 66 * MM, r.get("codice", ""), "PlexMono", 7.5, GRIGIO, 0.5)
        dettagli = " · ".join([d for d in [", ".join(r.get("colori") or []),
                                           r.get("taglie", ""), r.get("prezzo", "")] if d])
        blocco(c, x, yy - 72 * MM, dettagli, "Barlow", 8.5, 12, wcell, GRIGIO)
    piede(c, n, l["nome"])


# ------------------------------------------------------------ gamma tipo --

def pag_gamma_apertura(c, n, intro, categorie, conteggio, prima_pagina):
    y = testata(c, "Gamma tipo") - 20 * MM
    occhiello(c, MSX, y, intro["sottotitolo"], ACCENTO)
    y -= 16 * MM
    scrivi(c, MSX, y, intro["titolo"], "ZillaSlab-Bold", 34, INCHIOSTRO)
    y -= 14 * MM
    y = blocco(c, MSX, y, intro["testo"], "Barlow", 10.5, 16, cw(8), INCHIOSTRO)

    # L'avvertenza non e' decorativa: queste pagine non sono produzione in corso
    # e chi sfoglia il catalogo deve leggerlo prima degli articoli.
    y -= 14 * MM
    h = 26 * MM
    c.saveState()
    c.setFillColor(CARTA_CALDA)
    c.rect(MSX, y - h, UTILE, h, stroke=0, fill=1)
    c.restoreState()
    c.saveState()
    c.setFillColor(ACCENTO)
    c.rect(MSX, y - h, 1.6 * MM, h, stroke=0, fill=1)
    c.restoreState()
    blocco(c, MSX + 8 * MM, y - 9 * MM,
           "Gli articoli che seguono non sono in produzione e non sono mai stati "
           "venduti. I prezzi restano volutamente in bianco: si fissano con il "
           "licenziatario.",
           "Barlow-Medium", 9.5, 13.5, cw(10), INCHIOSTRO)
    y -= h + 16 * MM

    p = passo(y, MGIU + 14 * MM, len(categorie), 12 * MM)
    for i, cat in enumerate(categorie):
        filetto(c, MSX, y + p / 2, UTILE, FILETTO)
        scrivi(c, MSX, y, cat["nome"], "Barlow-SemiBold", 11, INCHIOSTRO)
        scrivi(c, cx(5), y, f"Classe {cat['classe']}", "PlexMono", 8, GRIGIO, 0.6)
        n_art = conteggio.get(cat["id"], 0)
        scrivi(c, cx(8), y, f"{n_art} articoli", "Barlow", 9.5, GRIGIO)
        scrivi(c, LARG - MDX, y, f"{prima_pagina + i:02d}", "PlexMono", 8, GRIGIO, 0.6, "dx")
        y -= p
    piede(c, n, "Gamma tipo · proposta di sviluppo")


def scheda_articolo(c, a, y, h):
    """Una fascia articolo a tutta larghezza. y = bordo superiore."""
    finestra_foto(c, MSX, y - h, cw(3), h, a["codice"], a.get("foto", ""))

    xa = cx(3)
    ya = y - 4 * MM
    occhiello(c, xa, ya, a["codice"], ACCENTO)
    ya -= 8 * MM
    ya = blocco(c, xa, ya, a["nome"], "Barlow-SemiBold", 12, 14.5, cw(4), INCHIOSTRO)
    ya -= 2 * MM
    blocco(c, xa, ya, a.get("forma", ""), "Barlow", 8.8, 12, cw(4), GRIGIO)
    if a.get("target"):
        scrivi(c, xa, y - h + 1 * MM, a["target"].upper(), "PlexMono", 6.8, GRIGIO, 1.0)

    yb = y - 4 * MM
    occhiello(c, cx(7), yb, "Marchio", GRIGIO)
    blocco(c, cx(7), yb - 6 * MM, a.get("marchio", ""), "Barlow", 8.8, 12,
           cw(2.5), INCHIOSTRO)

    xv = cx(9.5)
    wv = LARG - MDX - xv
    # Su profumi e linee corpo la colonna non elenca colori ma formati: cambia
    # l'etichetta, non la colonna.
    varianti = a.get("formato") or ", ".join(a.get("varianti") or [])
    if varianti:
        occhiello(c, xv, y - 4 * MM, "Formato" if a.get("formato") else "Varianti", GRIGIO)
        blocco(c, xv, y - 10 * MM, varianti, "Barlow", 8.8, 12, wv, INCHIOSTRO,
               max_righe=3)

    # Taglie ancorate al fondo della fascia: appese sotto le varianti
    # scivolavano oltre il filetto quando i colori andavano a tre righe.
    misura = a.get("misure") or a.get("taglie") or ""
    if misura:
        occhiello(c, xv, y - h + 9 * MM, "Misure" if a.get("misure") else "Taglie", GRIGIO)
        blocco(c, xv, y - h + 3 * MM, misura, "PlexMono", 8, 11, wv, INCHIOSTRO,
               max_righe=1)


def pag_gamma_categoria(c, n, cat, articoli):
    y = testata(c, f"Gamma · {cat['nome']}") - 16 * MM
    occhiello(c, MSX, y, f"Classe {cat['classe']} · gamma tipo", ACCENTO)
    y -= 13 * MM
    scrivi(c, MSX, y, cat["nome"], "ZillaSlab-Bold", 28, INCHIOSTRO)
    y -= 9 * MM
    blocco(c, MSX, y, cat["applicazione"], "Barlow", 9.5, 13.5, cw(8), GRIGIO)
    y -= 12 * MM

    p = passo(y, MGIU + 12 * MM, len(articoli), 40 * MM)
    h = min(p - 8 * MM, 56 * MM)
    for a in articoli:
        filetto(c, MSX, y + 5 * MM, UTILE, FILETTO)
        scheda_articolo(c, a, y, h)
        y -= p
    piede(c, n, f"Gamma tipo · classe {cat['classe']}")


# ----------------------------------------------------------------- montaggio --

def costruisci_licenze(anno):
    categorie = yaml.safe_load((DATI / "categorie.yml").read_text(encoding="utf-8"))
    prodotti = [p for p in yaml.safe_load((DATI / "prodotti.yml").read_text(encoding="utf-8"))
                if p.get("pubblica")]
    for cat in categorie:
        cat["_articoli"] = sum(1 for a in GAMMA["articoli"]
                               if a["categoria"] == cat["id"])
    coppie = [categorie[i:i + 2] for i in range(0, len(categorie), 2)]

    # Il sommario deve conoscere i numeri di pagina: si monta la scaletta prima.
    pagine = []
    pagine.append(("copertina", None))
    pagine.append(("sommario", None))
    pagine.append(("apertura", lambda c, n: pag_apertura(c, n)))
    pagine.append(("chi siamo", lambda c, n: pag_chi_siamo(c, n)))
    pagine.append(("argomenti", lambda c, n: pag_argomenti(c, n)))
    pagine.append(("marchio", lambda c, n: pag_marchio(c, n)))
    n_indice = len(pagine) + 1
    pagine.append(("categorie indice", None))
    prima_cat = len(pagine) + 1
    for coppia in coppie:
        pagine.append(("categorie", lambda c, n, k=coppia: pag_categorie(c, n, k)))
    n_prec = len(pagine) + 1
    if prodotti:
        pagine.append(("precedente", lambda c, n, l=prodotti[0]: pag_precedente(c, n, l)))
    n_retail = len(pagine) + 1
    pagine.append(("retail", lambda c, n: pag_retail(c, n)))
    n_percorso = len(pagine) + 1
    pagine.append(("percorso", lambda c, n: pag_percorso(c, n)))
    n_contratto = len(pagine) + 1
    pagine.append(("contratto", lambda c, n: pag_contratto(c, n)))
    pagine.append(("retro", lambda c, n: pag_retro(c, n)))

    voci = [("Il marchio", 3),
            ("Chi siamo", 4),
            ("Perché entrare in licenza", 5),
            ("Il marchio in stampa", 6),
            ("Le otto categorie", n_indice)]
    if prodotti:
        voci.append(("Precedente commerciale", n_prec))
    voci += [("Retail", n_retail),
             ("Come si arriva alla licenza", n_percorso),
             ("Cosa comprende il contratto", n_contratto)]

    pagine[0] = ("copertina", lambda c, n: copertina(
        c, n, M["titolo_catalogo"], M["sottotitolo_catalogo"], anno))
    pagine[1] = ("sommario", lambda c, n: pag_sommario(c, n, voci))
    pagine[6] = ("categorie indice", lambda c, n: pag_categorie_indice(
        c, n, categorie, prima_cat))
    return pagine


def costruisci_prodotti(anno):
    linee = [p for p in yaml.safe_load((DATI / "prodotti.yml").read_text(encoding="utf-8"))
             if p.get("pubblica")]
    categorie = yaml.safe_load((DATI / "categorie.yml").read_text(encoding="utf-8"))
    articoli = GAMMA["articoli"]
    per_categoria = {c["id"]: [a for a in articoli if a["categoria"] == c["id"]]
                     for c in categorie}
    conteggio = {k: len(v) for k, v in per_categoria.items()}
    con_articoli = [c for c in categorie if per_categoria[c["id"]]]

    pagine = [("copertina", None), ("indice", None)]
    for l in linee:
        pagine.append((l["nome"], lambda c, n, l=l: pag_linea(c, n, l)))
        if l.get("referenze"):
            pagine.append((l["nome"], lambda c, n, l=l: pag_referenze(c, n, l)))

    n_apertura = len(pagine) + 1
    pagine.append(("gamma", None))
    prima_gamma = len(pagine) + 1
    voci_gamma = []
    for i, cat in enumerate(con_articoli):
        voci_gamma.append((cat["nome"], cat["classe"],
                           conteggio[cat["id"]], prima_gamma + i))
        pagine.append((cat["nome"],
                       lambda c, n, cat=cat: pag_gamma_categoria(
                           c, n, cat, per_categoria[cat["id"]])))
    pagine.append(("retro", lambda c, n: pag_retro(c, n)))

    pagine[0] = ("copertina", lambda c, n: copertina(
        c, n, M["titolo_lookbook"], M["sottotitolo_lookbook"], anno))
    pagine[1] = ("indice", lambda c, n: pag_lookbook_indice(c, n, linee, voci_gamma))
    pagine[n_apertura - 1] = ("gamma", lambda c, n: pag_gamma_apertura(
        c, n, GAMMA["intro"], con_articoli, conteggio, prima_gamma))
    return pagine


def stampa(pagine, percorso, titolo):
    OUT.mkdir(exist_ok=True)
    c = rlcanvas.Canvas(str(percorso), pagesize=(LARG, ALT))
    c.setTitle(f"START UP® — {titolo}")
    c.setAuthor("START UP®")
    c.setSubject(M["posizionamento"])
    for i, (_, disegna) in enumerate(pagine, start=1):
        disegna(c, i)
        c.showPage()
    c.save()
    print(f"  {percorso.relative_to(QUI.parent)} — {len(pagine)} pagine")


def inventario(quali, anno):
    """Elenca ogni finestra foto con la misura richiesta e il gradino di
    risoluzione piu' basso che la copre. Non genera nulla e non spende nulla."""
    import collections

    # Gradini offerti dai modelli immagine, per lato lungo in pixel.
    GRADINI = [("512px", 512), ("1K", 1024), ("2K", 2048), ("4K", 4096)]

    def gradino(px_lato_lungo):
        for nome, lato in GRADINI:
            if lato >= px_lato_lungo:
                return nome, lato
        return "oltre 4K", None

    for nome_doc, costruisci in quali:
        FINESTRE.clear()
        pagine = costruisci(anno)
        # si impagina su un canvas buttato via: serve solo a raccogliere le misure
        c = rlcanvas.Canvas(os.devnull, pagesize=(LARG, ALT))
        for i, (_, disegna) in enumerate(pagine, start=1):
            disegna(c, i)
            c.showPage()

        print(f"\n{nome_doc} — {len(FINESTRE)} finestre foto")
        print(f"  {'misura':>14}  {'a 300 dpi':>13}  {'a 200 dpi':>13}  "
              f"{'300dpi':>7}  {'200dpi':>7}  n.")
        conteggio = collections.Counter()
        for f in FINESTRE:
            k = (round(f["mm_w"]), round(f["mm_h"]))
            conteggio[k] += 1
        for (mw, mh), n_volte in sorted(conteggio.items(),
                                        key=lambda kv: -kv[0][0] * kv[0][1]):
            for dpi in (300,):
                pass
            p300 = (round(mw / 25.4 * 300), round(mh / 25.4 * 300))
            p200 = (round(mw / 25.4 * 200), round(mh / 25.4 * 200))
            g300 = gradino(max(p300))[0]
            g200 = gradino(max(p200))[0]
            print(f"  {mw:>5} × {mh:<6} mm  {p300[0]:>5} × {p300[1]:<5}  "
                  f"{p200[0]:>5} × {p200[1]:<5}  {g300:>7}  {g200:>7}  ×{n_volte}")
        tot = collections.Counter()
        for f in FINESTRE:
            px = max(round(f["mm_w"] / 25.4 * 300), round(f["mm_h"] / 25.4 * 300))
            tot[gradino(px)[0]] += 1
        print("  totale per gradino a 300 dpi:",
              ", ".join(f"{k} ×{v}" for k, v in tot.items()))


def main():
    argomenti = [a for a in sys.argv[1:] if not a.startswith("--")]
    anno = date.today().year
    if "--anno" in sys.argv:
        anno = int(sys.argv[sys.argv.index("--anno") + 1])
    quali = argomenti or ["licenze", "prodotti"]

    if "--finestre" in sys.argv:
        carica_font()
        FOTO.mkdir(exist_ok=True)
        print("START UP® — inventario delle finestre foto")
        inventario([("catalogo-licenze", costruisci_licenze),
                    ("catalogo-prodotti", costruisci_prodotti)], anno)
        return

    print("START UP® — genero il catalogo")
    carica_font()
    FOTO.mkdir(exist_ok=True)

    if "licenze" in quali:
        stampa(costruisci_licenze(anno), OUT / "catalogo-licenze.pdf",
               M["titolo_catalogo"])
    if "prodotti" in quali:
        stampa(costruisci_prodotti(anno), OUT / "catalogo-prodotti.pdf",
               M["titolo_lookbook"])


# I dati e i colori si caricano all'import: le funzioni di pagina li usano
# come costanti di modulo.
M = yaml.safe_load((DATI / "marchio.yml").read_text(encoding="utf-8"))
GAMMA = yaml.safe_load((DATI / "gamma.yml").read_text(encoding="utf-8"))
INCHIOSTRO = colors.HexColor(M["colori"]["inchiostro"])
CARTA = colors.HexColor(M["colori"]["carta"])
CARTA_CALDA = colors.HexColor(M["colori"]["carta_calda"])
ACCENTO = colors.HexColor(M["colori"]["accento"])
GRIGIO = colors.HexColor(M["colori"]["grigio"])
FILETTO = colors.HexColor(M["colori"]["filetto"])
BOLLO = Bollo(DATI / "bollo.json")

if __name__ == "__main__":
    main()
