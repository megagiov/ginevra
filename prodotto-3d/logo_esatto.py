"""Rimette il logo START UP ufficiale sui render generati.

Il modello generativo non riproduce il logo fedelmente: sbaglia la fase delle
lettere sull'anello, ne aggiunge una di troppo e ridisegna i tratti. Il brief
pero' chiede il logo *esatto*. Questo script cancella il marchio inventato dal
render e ci sovrappone il file ufficiale, con l'ombreggiatura e il rilievo del
ricamo ricostruiti dal render sottostante.

Uso:  python3 logo_esatto.py
"""

import numpy as np
from PIL import Image
from scipy import ndimage

BASE = __file__.rsplit("/", 1)[0]
LOGO = f"{BASE}/logo/startup-logo-classico.png"


# --------------------------------------------------------------------------
# geometria misurata sui render (pixel, immagini 1792x2400)
# --------------------------------------------------------------------------
# box     : area da ripulire dal marchio generato
# donor   : zona di tessuto pulito da cui prendere la grana
# cx, cy  : centro dove va il logo ufficiale
# w, h    : larghezza e altezza del logo (ellittiche: la coscia e' cilindrica
#           e comprime il cerchio in orizzontale)
# part    : "full" tutto il logo, "symbol" solo il doppio triangolo centrale
PIAZZAMENTI = {
    "01-fronte": [
        dict(name="logo coscia", box=(1092, 616, 1288, 884), donor=(1092, 950, 1288, 1218),
             cx=1198, cy=750, w=158, h=204, part="full", ink=(233, 227, 211),
             relief=2.6, grain=1.6, dilate=9, sigma=9, mask_scale=0.66),
        # Il modello ha messo il doppio triangolo sulla gamba destra. Il brief
        # lo vuole sulla gamba sinistra, la stessa del logo: qui viene tolto...
        dict(name="doppio triangolo fuori posto", box=(534, 1596, 622, 1676),
             donor=(626, 1596, 714, 1676),
             cx=576, cy=1636, w=62, h=52, part=None, ink=None,
             relief=0.0, grain=0.0, dilate=15, sigma=6, mask_scale=0.95,
             soglia=30),
        # ...e rimesso sul lato esterno della gamba sinistra, alla stessa
        # altezza e alla stessa distanza dal bordo del capo.
        dict(name="doppio triangolo gamba sinistra", box=(1170, 1594, 1262, 1678),
             donor=None, cx=1215, cy=1636, w=60, h=52, part="symbol",
             ink=(226, 220, 205), relief=1.6, grain=1.4, pulisci=False),
    ],
    "02-retro": [
        dict(name="marchio su etichetta", box=(1163, 369, 1229, 458),
             donor=None, cx=1201, cy=413, w=46, h=62, part="full",
             ink=(246, 245, 241), relief=0.9, grain=0.0, rot=-6.0, dilate=5,
             sigma=14, mask_scale=0.95),
        # due schegge del marchio generato restano sul bordo destro
        # dell'etichetta, fuori dal box qui sopra: si cancellano e basta.
        dict(name="schegge bordo etichetta", box=(1222, 398, 1235, 440),
             donor=None, cx=1228, cy=419, w=14, h=44, part=None, ink=None,
             relief=0.0, grain=0.0, dilate=3, sigma=7, mask_scale=1.0),
    ],
}


def carica_logo(part):
    """Alpha del logo ufficiale, ritagliata sull'inchiostro reale."""
    la = np.asarray(Image.open(LOGO).convert("LA")).astype(np.float32)
    gray, a = la[..., 0], la[..., 1]
    ink = np.clip((1.0 - gray / 255.0) * (a / 255.0), 0.0, 1.0)

    if part == "symbol":
        # il doppio triangolo e' l'unico segno nel disco centrale
        h, w = ink.shape
        yy, xx = np.mgrid[0:h, 0:w]
        r = np.hypot(yy - (h - 1) / 2.0, xx - (w - 1) / 2.0)
        ink = np.where(r < w * 0.20, ink, 0.0)

    ys, xs = np.nonzero(ink > 0.05)
    return ink[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def piano_pulito(img, box, donor, mask, sigma=22):
    """Ricostruisce il tessuto sotto il marchio generato.

    Il gradiente largo viene interpolato dai pixel non mascherati; la grana
    fine arriva da una zona di tessuto pulito, cosi' la toppa non risulta
    liscia in mezzo a un fleece spazzolato.
    """
    x0, y0, x1, y1 = box
    reg = img[y0:y1, x0:x1].astype(np.float32)
    keep = (~mask).astype(np.float32)[..., None]

    num = ndimage.gaussian_filter(reg * keep, sigma=(sigma, sigma, 0))
    den = ndimage.gaussian_filter(np.repeat(keep, 3, axis=2), sigma=(sigma, sigma, 0))
    base = num / np.maximum(den, 1e-6)

    if donor is not None:
        dx0, dy0, dx1, dy1 = donor
        d = img[dy0:dy1, dx0:dx1].astype(np.float32)[: reg.shape[0], : reg.shape[1]]
        if d.shape[:2] == reg.shape[:2]:
            # Il tessuto pulito porta la texture; il livello di grigio resta
            # quello interpolato dai bordi del buco, cosi' la toppa segue
            # l'ombreggiatura invece di stamparsi come una macchia piatta.
            base = base + (d - ndimage.gaussian_filter(d, sigma=(sigma, sigma, 0)))

    out = reg.copy()
    m3 = mask[..., None]
    out = np.where(m3, base, out)
    return out


def maschera_marchio(reg, spec):
    """Isola i pixel del marchio generato, e solo quelli.

    Due filtri, entrambi necessari. La soglia alta separa il filo panna dal
    tessuto: il bordo del capo prende luce e supera una soglia bassa, e se
    finisce nella maschera la ricostruzione lo appiattisce lasciando una
    banda visibile. L'ellisse tiene la pulizia dentro l'ingombro del logo,
    cosi' nessuna piega illuminata altrove viene toccata.
    """
    lum = reg.mean(axis=2)
    m = lum > (np.median(lum) + spec.get("soglia", 60))
    m = ndimage.binary_closing(m, np.ones((3, 3)))

    h, w = m.shape
    cx = spec["cx"] - spec["box"][0]
    cy = spec["cy"] - spec["box"][1]
    yy, xx = np.mgrid[0:h, 0:w]
    k = spec.get("mask_scale", 0.62)
    dentro = ((xx - cx) / (spec["w"] * k)) ** 2 + ((yy - cy) / (spec["h"] * k)) ** 2 <= 1.0
    m &= dentro

    return ndimage.binary_dilation(m, np.ones((spec.get("dilate", 9),) * 2)) & dentro


def ricama(reg, spec, ink_alpha):
    """Sovrappone il logo come ricamo: rilievo, ombra e ombreggiatura del drappo."""
    h, w = reg.shape[:2]
    cx = spec["cx"] - spec["box"][0]
    cy = spec["cy"] - spec["box"][1]

    a = Image.fromarray((ink_alpha * 255).astype(np.uint8), "L")
    a = a.resize((spec["w"], spec["h"]), Image.LANCZOS)
    if spec.get("rot"):
        a = a.rotate(spec["rot"], resample=Image.BICUBIC, expand=True)

    alpha = np.zeros((h, w), np.float32)
    aw, ah = a.size
    px, py = int(round(cx - aw / 2)), int(round(cy - ah / 2))
    sx0, sy0 = max(0, -px), max(0, -py)
    dx0, dy0 = max(0, px), max(0, py)
    dx1, dy1 = min(w, px + aw), min(h, py + ah)
    alpha[dy0:dy1, dx0:dx1] = (
        np.asarray(a).astype(np.float32)[sy0:sy0 + dy1 - dy0, sx0:sx0 + dx1 - dx0] / 255.0
    )
    alpha = ndimage.gaussian_filter(alpha, 0.7)

    out = reg.copy()

    # ombra portata: il ricamo sta sopra il tessuto e proietta
    r = spec["relief"]
    if r > 0:
        sh = ndimage.gaussian_filter(np.roll(np.roll(alpha, int(r), 0), int(r), 1), r)
        sh = np.clip(sh - alpha, 0, 1) * 0.55
        out *= (1.0 - sh * 0.45)[..., None]

    # filo, ombreggiato dal drappo sottostante
    lum = ndimage.gaussian_filter(reg.mean(axis=2), 9)
    shade = np.clip(lum / max(np.median(lum), 1e-6), 0.74, 1.12)
    thread = np.array(spec["ink"], np.float32)[None, None, :] * shade[..., None]

    # grana del filo: punti satin, non superficie piatta
    if spec["grain"] > 0:
        rng = np.random.default_rng(7)
        n = ndimage.gaussian_filter(rng.normal(0, 1, (h, w)).astype(np.float32), 0.8)
        thread = thread + (n * 9.0 * spec["grain"])[..., None]

    # bordo in luce in alto a sinistra: vende il rilievo
    if r > 0:
        rim = np.clip(alpha - np.roll(np.roll(alpha, 1, 0), 1, 1), 0, 1)
        thread = thread + (rim * 22.0)[..., None]

    a3 = alpha[..., None]
    return np.clip(out * (1 - a3) + thread * a3, 0, 255)


def elabora(nome):
    src = f"{BASE}/render/{nome}-grezzo.png"
    img = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)

    for spec in PIAZZAMENTI[nome]:
        x0, y0, x1, y1 = spec["box"]
        reg = img[y0:y1, x0:x1].astype(np.float32)
        mask = np.zeros(reg.shape[:2], bool)
        if spec.get("pulisci", True):
            mask = maschera_marchio(reg, spec)
            reg = piano_pulito(img, spec["box"], spec.get("donor"), mask,
                               spec.get("sigma", 22))
        if spec["part"] is not None:
            reg = ricama(reg, spec, carica_logo(spec["part"]))
        img[y0:y1, x0:x1] = reg
        print(f"  {nome}: {spec['name']} - {int(mask.sum())} px di marchio generato rimossi")

    out = f"{BASE}/render/{nome}.png"
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(out)
    print(f"  scritto {out}")


if __name__ == "__main__":
    for nome in PIAZZAMENTI:
        elabora(nome)
