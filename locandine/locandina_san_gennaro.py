#!/usr/bin/env python3
"""
Locandina social — On The Road Napoli, chiusura per San Gennaro.

Gira interamente in locale: nessun modello generativo, nessun credito speso.
Il testo e' composto con font veri, quindi e' esatto al pixel: non ci sono
marchi inventati sulla moto ne' parole italiane storpiate da un modello.

    python3 locandina_san_gennaro.py                       # tutti i formati
    python3 locandina_san_gennaro.py story                 # solo il 9:16
    python3 locandina_san_gennaro.py --riapertura=""       # senza la riga finale
    python3 locandina_san_gennaro.py --riapertura="Torniamo domenica 20"
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "assets", "on-the-road-napoli-interceptor.jpg")
FONTS = os.path.join(HERE, "fonts")
OUT = os.path.join(HERE, "out")

# --- testi -----------------------------------------------------------------
# Ogni riga qui sotto viene dall'utente o e' verificabile: il 19 settembre 2026
# cade di sabato, San Gennaro e' il patrono di Napoli. Niente orari, indirizzi
# o recapiti: non li abbiamo, e inventarli sarebbe un'affermazione falsa.
KICKER = "SABATO 19 SETTEMBRE"
RIGA1 = "CHIUSI PER"
RIGA2 = "SAN GENNARO"
RIGA3 = "FESTA PATRONALE DI NAPOLI"
AUGURIO = "Buona festa a tutti"
RIAPERTURA = "Vi aspettiamo lunedì 21"      # da confermare col negozio
FOOTER = "CONCESSIONARIA · OFFICINA · ACCESSORI · RICAMBI"

# --- palette ---------------------------------------------------------------
ROSSO = (218, 4, 17)          # campionato dalle fiamme del logo, non scelto a occhio
ORO = (232, 178, 58)
ORO_CHIARO = (250, 229, 160)
ORO_SCURO = (188, 130, 26)
BIANCO = (255, 255, 255)

SRC_HEADER = 320              # la fascia bianca col logo, misurata sull'originale
FARO = (808, 1048)            # centro del faro: perno della composizione


# --- helper ----------------------------------------------------------------
def font(nome, size, peso=None):
    f = ImageFont.truetype(os.path.join(FONTS, nome + ".ttf"), max(int(size), 8))
    if peso:
        try:
            f.set_variation_by_name(peso)
        except Exception:
            pass
    return f


def misura(testo, fnt, tracking):
    larg = sum(fnt.getlength(c) for c in testo) + tracking * max(len(testo) - 1, 0)
    return larg, fnt.getbbox(testo)[3]


def scrivi(draw, cx, y, testo, fnt, colore, tracking=0, ombra=None):
    """Testo spaziato, centrato su cx, bordo superiore a y."""
    larg, _ = misura(testo, fnt, tracking)
    x0 = cx - larg / 2
    for dx, dy, col in (ombra or []):
        x = x0
        for c in testo:
            draw.text((x + dx, y + dy), c, font=fnt, fill=col)
            x += fnt.getlength(c) + tracking
    x = x0
    for c in testo:
        draw.text((x, y), c, font=fnt, fill=colore)
        x += fnt.getlength(c) + tracking


def adatta(nome, testo, larg_max, tracking=0, peso=None, lo=16, hi=400):
    """La dimensione piu' grande che sta dentro larg_max."""
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        if misura(testo, font(nome, mid, peso), tracking)[0] <= larg_max:
            best, lo = mid, mid + 1
        else:
            hi = mid - 1
    return font(nome, best, peso)


def testo_oro(size, testo, fnt, tracking=0):
    """Gradiente metallico verticale ritagliato sulle lettere."""
    W, H = size
    mask = Image.new("L", (W, H), 0)
    scrivi(ImageDraw.Draw(mask), W / 2, 0, testo, fnt, 255, tracking)
    bb = mask.getbbox()
    top, bot = (bb[1], bb[3]) if bb else (0, H)
    span = max(bot - top, 1)
    grad = Image.new("RGB", (W, H))
    g = ImageDraw.Draw(grad)
    for y in range(H):
        t = min(max((y - top) / span, 0.0), 1.0)
        if t < 0.55:
            k = t / 0.55
            col = tuple(int(ORO_CHIARO[i] + (ORO[i] - ORO_CHIARO[i]) * k) for i in range(3))
        else:
            k = (t - 0.55) / 0.45
            col = tuple(int(ORO[i] + (ORO_SCURO[i] - ORO[i]) * k) for i in range(3))
        g.line([(0, y), (W, y)], fill=col)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.paste(grad, (0, 0), mask)
    return out


def _proteggi_logo(rgba, header_h):
    """Azzera l'alpha sulla fascia del logo.

    Senza questo la raggiera sborda sul bianco e vela il marchio: nel formato
    quadrato, dove il faro e' vicino all'header, il logo usciva grigiastro.
    """
    a = np.asarray(rgba).copy()
    a[:header_h, :, 3] = 0
    return Image.fromarray(a, "RGBA")


def raggiera(size, centro, header_h, n=24, alpha=52, inner=150, outer=1500):
    """Raggi dorati che partono dal faro e si aprono nel cielo."""
    W, H = size
    S = 2
    layer = Image.new("L", (W * S, H * S), 0)
    d = ImageDraw.Draw(layer)
    cx, cy = centro[0] * S, centro[1] * S
    passo = 360.0 / n
    mezzo = passo * 0.26
    r = outer * S * 1.6
    for i in range(n):
        a0, a1 = math.radians(i * passo - mezzo), math.radians(i * passo + mezzo)
        d.polygon([(cx, cy),
                   (cx + r * math.cos(a0), cy + r * math.sin(a0)),
                   (cx + r * math.cos(a1), cy + r * math.sin(a1))], fill=255)
    # senza sfocatura i bordi netti dei raggi bandeggiano sul carroponte
    layer = layer.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(7))

    yy, xx = np.mgrid[0:H, 0:W]
    dist = np.hypot(xx - centro[0], yy - centro[1])
    sale = np.clip((dist - inner) / 220.0, 0, 1)
    scende = np.clip(1.0 - (dist - inner) / float(outer), 0, 1) ** 1.5
    a = (np.asarray(layer).astype(float) / 255.0) * sale * scende * alpha

    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = 255, 222, 150
    rgba[..., 3] = a.astype(np.uint8)
    return _proteggi_logo(Image.fromarray(rgba, "RGBA"), header_h)


def alone(size, centro, header_h, raggio=430, alpha=74):
    """Alone caldo attorno al faro: il faro della moto diventa l'aureola."""
    W, H = size
    yy, xx = np.mgrid[0:H, 0:W]
    a = np.clip(1.0 - np.hypot(xx - centro[0], yy - centro[1]) / raggio, 0, 1) ** 2.2 * alpha
    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = 255, 228, 168
    rgba[..., 3] = a.astype(np.uint8)
    return _proteggi_logo(Image.fromarray(rgba, "RGBA"), header_h)


def alone_testo(maschera, raggio, alpha):
    """Alone scuro sfocato ricavato dalle lettere.

    Serve a tenere leggibile il testo senza affogare la foto: con questo la
    velatura puo' scendere molto, e la moto resta visibile sotto il titolo.
    """
    sfoc = maschera.filter(ImageFilter.GaussianBlur(raggio))
    out = Image.new("RGBA", maschera.size, (0, 0, 0, 0))
    out.putalpha(sfoc.point(lambda v: min(int(v * alpha / 255) * 2, alpha)))
    return out


def velatura(size, inizio, pieno, picco=228):
    """Sfumatura scura dal basso: regge il testo senza cancellare la moto."""
    W, H = size
    col = np.zeros((H,), dtype=float)
    for y in range(H):
        if y <= inizio:
            col[y] = 0.0
        elif y >= pieno:
            col[y] = picco
        else:
            t = (y - inizio) / float(pieno - inizio)
            col[y] = picco * (t * t * (3 - 2 * t))          # smoothstep
    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = 8, 7, 10
    rgba[..., 3] = np.repeat(col[:, None], W, axis=1).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


# --- composizione ----------------------------------------------------------
def costruisci(nome, size, header_h, faro_y, s, compatto, zoom, picco,
               riapertura, debug=False):
    W, H = size
    foto = Image.open(SRC).convert("RGB")
    alto = H - header_h

    # Il corpo della foto si ingrandisce e si ritaglia attorno al faro: cosi'
    # la moto riempie il quadro invece di lasciare mezzo cielo vuoto.
    corpo = foto.crop((0, SRC_HEADER, 1080, foto.height))
    if zoom != 1.0:
        corpo = corpo.resize((round(corpo.width * zoom), round(corpo.height * zoom)),
                             Image.LANCZOS)
    fx, fy = FARO[0] * zoom, (FARO[1] - SRC_HEADER) * zoom
    tx = max(0, min(int(round(fx - FARO[0])), corpo.width - W))
    ty = max(0, min(int(round(fy - (faro_y - header_h))), corpo.height - alto))

    # --- si misura il blocco di testo PRIMA di disegnare, cosi' si ancora da
    #     solo alla fascia rossa invece di finire fuori quadro ---
    f_k = font("Oswald", 44 * s, "SemiBold")
    f1 = adatta("Anton", RIGA1, W * 0.50, 6 * s)
    f2 = adatta("Anton", RIGA2, W * 0.88, 2 * s)
    f3 = font("Cinzel", 36 * s, "Bold")
    f4 = font("Oswald", 46 * s, "Medium")
    h1, h2 = f1.getbbox(RIGA1)[3], f2.getbbox(RIGA2)[3]
    fb = int(76 * s)                                        # fascia rossa finale

    coda = []
    if compatto and riapertura:
        # col tetto alla dimensione nominale: senza, la riga unita si gonfiava
        # fino a sovrastare "FESTA PATRONALE DI NAPOLI"
        f5 = adatta("Oswald", AUGURIO + " · " + riapertura, W * 0.86, 2 * s,
                    "Medium", hi=int(46 * s))
        coda = [(AUGURIO + " · " + riapertura, f5, ORO + (255,))]
    else:
        coda = [(AUGURIO, f4, ORO + (255,))]
        if riapertura:
            coda.append((riapertura, font("Oswald", 40 * s, "Light"), (255, 255, 255, 210)))

    blocco_h = (int(86 * s) + int(h1 + 22 * s) + int(h2 + 40 * s)
                + int(34 * s) + int(78 * s))
    for i, (t, f, _) in enumerate(coda):
        blocco_h += int(62 * s) if i == 0 else int(f.getbbox(t)[3] * 1.15)
    base_y = H - fb - int(46 * s) - blocco_h

    # --- fondo: logo intatto in cima, foto ritagliata sul faro sotto ---
    tela = Image.new("RGB", (W, H), (12, 12, 14))
    testata = foto.crop((0, 0, 1080, SRC_HEADER))
    if (W, header_h) != testata.size:
        testata = testata.resize((W, header_h), Image.LANCZOS)
    tela.paste(testata, (0, 0))
    tela.paste(corpo.crop((tx, ty, tx + W, ty + alto)), (0, header_h))
    tela = tela.convert("RGBA")

    faro = (int(fx - tx), int(fy - ty + header_h))
    inizio_vel = max(base_y - int(260 * s), header_h + 20)
    pieno_vel = base_y + int(210 * s)

    tela.alpha_composite(raggiera((W, H), faro, header_h, outer=int(1500 * s ** .4)))
    tela.alpha_composite(velatura((W, H), inizio_vel, pieno_vel, picco))
    # l'aureola va DOPO la velatura, altrimenti la velatura la spegne proprio
    # dove serve: il faro sta sul bordo alto della sfumatura
    tela.alpha_composite(alone((W, H), faro, header_h, raggio=int(430 * s ** .3)))

    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    masc = Image.new("L", (W, H), 0)          # solo le lettere, per l'alone
    dm = ImageDraw.Draw(masc)
    cx = W / 2

    def riga(y, testo, fnt, colore, tracking, ombre=None):
        scrivi(dm, cx, y, testo, fnt, 255, tracking)
        scrivi(d, cx, y, testo, fnt, colore, tracking, ombre)

    # filetto oro sotto il logo, con innesto rosso del marchio
    fil = max(int(7 * s), 3)
    d.rectangle([0, header_h, W, header_h + fil], fill=ORO + (255,))
    d.rectangle([0, header_h, int(W * 0.34), header_h + fil], fill=ROSSO + (255,))

    ombra = [(0, int(4 * s), (0, 0, 0, 165)), (int(2 * s), int(2 * s), (0, 0, 0, 120))]
    y = base_y

    # --- occhiello: ◆——  SABATO 19 SETTEMBRE  ——◆
    tr = 9 * s
    wk, _ = misura(KICKER, f_k, tr)
    riga(y, KICKER, f_k, ORO + (255,), tr, ombra)
    ym = y + int(30 * s)
    for sgn in (-1, 1):
        x0 = cx + sgn * (wk / 2 + int(26 * s))
        x1 = cx + sgn * (wk / 2 + int(132 * s))
        d.line([(x0, ym), (x1, ym)], fill=ORO + (215,), width=max(int(3 * s), 2))
        r = max(int(7 * s), 4)
        d.polygon([(x1 + sgn * (r + int(14 * s)), ym), (x1 + sgn * (r + int(7 * s)), ym - r),
                   (x1 + sgn * r, ym), (x1 + sgn * (r + int(7 * s)), ym + r)],
                  fill=ORO + (235,))
    y += int(86 * s)

    # --- CHIUSI PER
    riga(y, RIGA1, f1, BIANCO + (255,), 6 * s, ombra)
    y += int(h1 + 22 * s)

    # --- SAN GENNARO, in oro
    blocco = testo_oro((W, int(h2 + 40 * s)), RIGA2, f2, 2 * s)
    for dx, dy, col in ombra:
        m = Image.new("L", blocco.size, 0)
        scrivi(ImageDraw.Draw(m), W / 2, 0, RIGA2, f2, 255, 2 * s)
        sh = Image.new("RGBA", blocco.size, col[:3] + (0,))
        sh.putalpha(m.point(lambda v: int(v * col[3] / 255)))
        lay.alpha_composite(sh, (int(dx), int(y + dy)))
    scrivi(dm, cx, y, RIGA2, f2, 255, 2 * s)
    lay.alpha_composite(blocco, (0, int(y)))
    y += int(h2 + 40 * s)

    # --- filetto + FESTA PATRONALE DI NAPOLI
    d.line([(cx - int(210 * s), y), (cx + int(210 * s), y)], fill=ORO + (200,),
           width=max(int(2 * s), 1))
    y += int(34 * s)
    riga(y, RIGA3, f3, (255, 255, 255, 235), 7 * s, ombra)
    y += int(78 * s)

    # --- augurio (+ riapertura)
    for i, (t, f, col) in enumerate(coda):
        riga(y, t, f, col, 2 * s, ombra)
        y += int(62 * s) if i == 0 else 0

    # --- fascia rossa di chiusura. Non porta informazioni indispensabili: e'
    #     la zona che Instagram e TikTok coprono con la loro interfaccia.
    d.rectangle([0, H - fb, W, H], fill=ROSSO + (255,))
    d.rectangle([0, H - fb, W, H - fb + max(int(3 * s), 2)], fill=ORO + (255,))
    f_f = font("Oswald", 26 * s, "Medium")
    bf = f_f.getbbox(FOOTER)
    scrivi(d, cx, H - fb + (fb - (bf[3] - bf[1])) / 2 - bf[1], FOOTER, f_f,
           (255, 255, 255, 240), 5 * s)

    tela.alpha_composite(alone_testo(masc, max(int(17 * s), 6), 170))
    tela.alpha_composite(lay)
    fuori = os.path.join(OUT, nome)
    tela.convert("RGB").save(fuori, quality=94, subsampling=0)
    if debug:
        print(f"      testata={header_h} zoom={zoom} faro=({faro[0]},{faro[1]}) "
              f"velatura={inizio_vel}..{pieno_vel} testo={base_y}..{base_y + blocco_h}")
    print(f"  {nome}  {W}x{H}  {os.path.getsize(fuori) / 1024:.0f} KB")
    return fuori


FORMATI = {
    # nome        dimensioni  testata faro_y scala compatto zoom  velatura
    "story":  ((1080, 1920), 320, 880, 1.00, False, 1.24, 178),  # storie/reel 9:16
    "feed":   ((1080, 1350), 280, 560, 0.76, False, 1.12, 200),  # bacheca 4:5
    "quadro": ((1080, 1080), 240, 470, 0.64, True,  1.18, 205),  # quadrato 1:1
}

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    riap, scelti = RIAPERTURA, []
    for a in sys.argv[1:]:
        if a.startswith("--riapertura="):
            riap = a.split("=", 1)[1]
        else:
            scelti.append(a)
    print("Locandina San Gennaro — On The Road Napoli")
    for nome in (scelti or list(FORMATI)):
        costruisci(f"san-gennaro-{nome}.jpg", *FORMATI[nome], riap, debug=True)
    if not scelti:
        costruisci("san-gennaro-story-senza-riapertura.jpg", *FORMATI["story"], "")
