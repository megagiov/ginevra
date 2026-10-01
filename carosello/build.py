"""Carosello TikTok GM Vegasi: genera le slide 1080x1080 nel formato di casa.

Uso:
    python3 carosello/build.py spec.json

spec.json:
{
  "out": "carosello/out/pantofole",
  "slides": [
    {"layout": "split", "foto": ["a.jpg", "b.jpg"], "testo": "Marrone o Nero?"},
    {"layout": "tre",   "foto": ["a.jpg", "b.jpg", "c.jpg"], "testo": "..."},
    {"layout": "pieno", "foto": ["a.jpg"], "testo": "..."},
    {"layout": "split", "foto": ["a.jpg", "b.jpg"], "titoli": ["sx", "dx"]}
  ]
}

Le misure sono prese dai caroselli pubblicati (vedi FORMATO.md).
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

QUI = Path(__file__).parent
LATO = 1080
BLU = (2, 114, 188)
CORNICE = 22
DIVISORIO = 10
LOGO_BOX = (70, 818)  # angolo in alto a sinistra, 186x198
TESTO = 54
TESTO_TITOLO = 34
FONT_CANDIDATI = [
    QUI / "fonts/OpenSans-Bold.ttf",
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]


def font(size):
    for f in FONT_CANDIDATI:
        if f.exists():
            return ImageFont.truetype(str(f), size)
    return ImageFont.load_default(size)


def riempi(foto, w, h):
    """Foto con fondo bianco: la scala per intero dentro il pannello (contain)
    se e' un packshot, altrimenti la ritaglia al centro (cover)."""
    im = Image.open(foto).convert("RGB")
    angoli = [im.getpixel(p) for p in [(0, 0), (im.width - 1, 0),
                                       (0, im.height - 1), (im.width - 1, im.height - 1)]]
    packshot = all(min(c) > 235 for c in angoli)
    pannello = Image.new("RGB", (w, h), (255, 255, 255))
    if packshot:
        s = min(w * 0.92 / im.width, h * 0.92 / im.height)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        pannello.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    else:
        s = max(w / im.width, h / im.height)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        pannello.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return pannello


def pannelli(layout, n):
    interno = LATO - 2 * CORNICE
    if layout == "pieno":
        return [(CORNICE, CORNICE, interno, interno)]
    if layout == "split":
        w = (interno - DIVISORIO) // 2
        return [(CORNICE, CORNICE, w, interno),
                (CORNICE + w + DIVISORIO, CORNICE, interno - w - DIVISORIO, interno)]
    if layout == "tre":  # fasce orizzontali: i prodotti larghi (scarpe) restano grandi
        h = (interno - 2 * DIVISORIO) // 3
        return [(CORNICE, CORNICE + i * (h + DIVISORIO), interno,
                 h if i < 2 else interno - 2 * (h + DIVISORIO)) for i in range(3)]
    raise ValueError(layout)


def scrivi(img, testo, centro, size, larghezza_max):
    f = font(size)
    d = ImageDraw.Draw(img)
    righe, riga = [], ""
    for parola in testo.split():
        prova = (riga + " " + parola).strip()
        if d.textbbox((0, 0), prova, font=f)[2] > larghezza_max and riga:
            righe.append(riga)
            riga = parola
        else:
            riga = prova
    righe.append(riga)
    passo = round(size * 1.25)
    y0 = centro[1] - passo * len(righe) // 2
    # ombra morbida: il bianco resta leggibile anche sui fondi chiari
    ombra = Image.new("L", img.size, 0)
    do = ImageDraw.Draw(ombra)
    for i, r in enumerate(righe):
        do.text((centro[0], y0 + i * passo), r, font=f, fill=200, anchor="ma")
    ombra = ombra.filter(ImageFilter.GaussianBlur(size // 6))
    img.paste((0, 0, 0), (0, 0), ombra.point(lambda v: min(255, v * 0.8)))
    for i, r in enumerate(righe):
        d.text((centro[0], y0 + i * passo), r, font=f, fill="white", anchor="ma")


def slide(s):
    img = Image.new("RGB", (LATO, LATO), BLU)
    box = pannelli(s["layout"], len(s["foto"]))
    for (x, y, w, h), foto in zip(box, s["foto"]):
        img.paste(riempi(foto, w, h), (x, y))
    for (x, y, w, h), t in zip(box, s.get("titoli", [])):
        scrivi(img, t, (x + w // 2, y + 30 + TESTO_TITOLO), TESTO_TITOLO, w - 60)
    if s.get("testo"):
        scrivi(img, s["testo"], (LATO // 2, LATO // 2), TESTO, LATO - 2 * 120)
    img.paste(Image.open(QUI / "assets/logo_gmvegasi_tiktokshop.png").convert("RGB"), LOGO_BOX)
    return img


def main():
    spec = json.loads(Path(sys.argv[1]).read_text())
    out = Path(spec["out"])
    out.mkdir(parents=True, exist_ok=True)
    for i, s in enumerate(spec["slides"], 1):
        p = out / f"slide_{i}.jpg"
        slide(s).save(p, quality=95)
        print(p)


if __name__ == "__main__":
    main()
