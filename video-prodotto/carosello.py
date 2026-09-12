# Carosello TikTok 9:16 — cinque slide PNG, nessun credito speso.
#
# Il prodotto NON viene mai rigenerato: si scontorna la foto reale del catalogo
# e la si compone sopra uno sfondo costruito qui. Vedi ARTLIST.md §2 — passare
# la foto come riferimento a un modello generativo restituisce una sosia, e il
# marchio stampato sul fianco viene reinventato. Su un marchio di terzi non e'
# un difetto estetico.
from PIL import Image, ImageDraw, ImageFilter
import numpy as np, os, sys

# helper condivisi con lo spot: cutout, band, line, eo, cl, font, W, H, GR, colori
exec(open('build.py').read().split('A1,B1,C1,D1,E0')[0])

IN, OUT, SFONDI = 'carosello/in', 'carosello/out', 'carosello/sfondi'

def scontorna(path, gain=1.0, thr=247):
    """Come cutout() in build.py, ma con soglia regolabile.

    La soglia fissa a 238 dello spot mangia i prodotti chiari: su una N.92
    bianca su fondo bianco sparisce meta' scarpa. Qui si tiene alta (solo il
    bianco quasi puro e' fondo) e si lascia al floodfill dagli angoli il
    compito di distinguere il fondo dai bianchi interni al prodotto."""
    src = Image.open(path).convert('RGB'); w, h = src.size
    g = np.asarray(src.convert('L'))
    m = Image.fromarray(((g > thr).astype(np.uint8) * 255), 'L').copy()
    for xy in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if m.getpixel(xy) == 255: ImageDraw.floodfill(m, xy, 128, thresh=0)
    alpha = np.where(np.asarray(m) == 128, 0, 255).astype(np.uint8)
    a = Image.fromarray(alpha, 'L').filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.7))
    a2 = np.clip((np.asarray(a).astype(np.float32) / 255 - 0.12) / 0.80, 0, 1)
    rgb = np.asarray(src).astype(np.float32)
    if gain != 1.0: rgb = np.clip(255 * np.power(rgb / 255, 1 / gain), 0, 255)
    rgb[(a2 > 0.05) & (a2 < 0.95)] *= 0.93 / gain
    out = Image.fromarray(rgb.astype(np.uint8), 'RGB')
    out.putalpha(Image.fromarray((a2 * 255).astype(np.uint8), 'L'))
    return out.crop(out.getbbox())
ROSA, CIANO = (254, 44, 85), (37, 244, 238)      # coordinati all'end card, ARTLIST.md §6

# Area sicura: TikTok copre il fondo con didascalia, nome utente e pulsanti, e
# la colonna destra con le icone. Nessun testo esce da qui.
SX, SY, EX, EY = 96, 150, 980, 1500

SLIDES = [
 dict(slug='petrolio', src='1.jpg', bg='1.jpg', kicker='LUNED\u00cc  7:40',
      l1='PRIMA IL CAFF\u00c8.',   l2='POI TUTTO IL RESTO.', appoggio=1300, gain=1.00, dx=115),
 dict(slug='grigioblu', src='5.jpg', bg='2.jpg', kicker='MERCOLED\u00cc  19:00',
      l1='ANCHE OGGI',          l2='CI SEI ANDATO.',      appoggio=1460, gain=1.10),
 dict(slug='nero',      src='3.jpg', bg='3.jpg', kicker='SABATO  21:30',
      l1='IL NERO NON',         l2='CHIEDE PERMESSO.',    appoggio=1430, gain=1.55),
 dict(slug='marrone',   src='2.jpg', bg='4.jpg', kicker='DOMENICA',
      l1='JEANS E N.92.',       l2='NIENT\u2019ALTRO.',      appoggio=1480, gain=1.12),
 dict(slug='militare',  src='4.jpg', bg='5.jpg', kicker='CINQUE COLORI, UNA N.92',
      l1='SCEGLI',              l2='IL TUO.',             appoggio=None, gain=1.08),
]

def sfondo_foto(nome):
    """Sfondo generato, ritagliato a coprire 1080x1920 senza deformare."""
    im = Image.open(os.path.join(SFONDI, nome)).convert('RGB')
    k = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    return im.crop(((im.width - W) // 2, (im.height - H) // 2,
                    (im.width - W) // 2 + W, (im.height - H) // 2 + H))

def sfondo(lift):
    """Gradiente verticale + vignettatura + macchia morbida, come lo spot."""
    y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]
    r = np.broadcast_to(24 + 15 * (1 - y) + 7 * x, (H, W))
    g = np.broadcast_to(24 + 14 * (1 - y) + 6 * x, (H, W))
    b = np.broadcast_to(28 + 13 * (1 - y) + 5 * x, (H, W))
    base = np.dstack([r, g, b]).astype(np.float32) + lift
    rng = np.random.default_rng(11); blot = rng.normal(0, 1, (H // 8, W // 8))
    blot = np.array(Image.fromarray(((blot - blot.min()) / np.ptp(blot) * 255).astype(np.uint8))
                    .resize((W, H), Image.BICUBIC)).astype(np.float32)
    base += ((blot - 128) * (0.05 + lift * 0.0015))[:, :, None]
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    base *= np.clip(1.14 - 0.48 * d ** 1.7, 0, 1.3)[:, :, None]
    base += (GR[0] * 0.55)[:, :, None]
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB')

def ombra(dst, sh, x, y, w, h):
    """Ombra portata morbida sotto il prodotto: senza, il cutout galleggia."""
    a = sh.split()[3].resize((w, h), Image.LANCZOS)
    o = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    o.paste(Image.new('RGBA', (w, h), (0, 0, 0, 150)), (x + 12, y + 26), a)
    dst.alpha_composite(o.filter(ImageFilter.GaussianBlur(34)))

def fit(im, box_w, box_h):
    k = min(box_w / im.width, box_h / im.height)
    return im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)

def velatura(base, fino=830):
    """Velatura scura dietro al testo (ARTLIST.md §6), tarata sul fondo.

    Su uno sfondo fotografico chiaro — il piano cucina, il muro della boutique —
    una velatura fissa non basta e il testo bianco sparisce. La forza si calcola
    quindi dalla luminanza media della fascia che il testo occupa davvero.
    """
    lum = np.asarray(base.convert('L')).astype(np.float32)[:fino]
    forza = float(np.clip(72 + (lum.mean() - 60) * 1.5, 72, 238))
    piena = int(fino * 0.62)
    a = np.zeros((H, W), np.float32)
    a[:piena] = forza
    a[piena:fino] = np.linspace(forza, 0, fino - piena)[:, None]
    v = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    v.putalpha(Image.fromarray(a.astype(np.uint8), 'L'))
    base.alpha_composite(v)

# Ripiani della boutique nello sfondo 5, misurati sull'immagine: quota a cui
# appoggia la suola e margini orizzontali utili del ripiano.
RIPIANI = [(890, 70, 1010), (1205, 70, 1010)]

def slide(i, s, tutte=None):
    bg = s.get('bg')
    base = (sfondo_foto(bg) if bg and os.path.exists(os.path.join(SFONDI, bg))
            else sfondo(s.get('lift', 0))).convert('RGBA')
    velatura(base)

    if tutte is None:
        prod = scontorna(os.path.join(IN, s['src']), s.get('gain', 1.0), s.get('thr', 247))
        p = fit(prod, 800, 560)
        px = (W - p.width) // 2 + s.get('dx', 0)
        py = s['appoggio'] - p.height   # appoggia, non galleggia
        ombra(base, p, px, py, p.width, p.height)
        base.alpha_composite(p, (px, py))
    else:
        # ultima slide: le cinque sui due ripiani, tre sopra e due sotto.
        for j, (im, g, t) in enumerate(tutte):
            q = fit(scontorna(os.path.join(IN, im), g, t), 300, 215)
            riga, col, n = (0, j, 3) if j < 3 else (1, j - 3, 2)
            quota, x0, x1 = RIPIANI[riga]
            passo = (x1 - x0) / n
            qx = int(x0 + passo * (col + 0.5) - q.width / 2)
            qy = quota - q.height
            ombra(base, q, qx, qy, q.width, q.height)
            base.alpha_composite(q, (qx, qy))

    d = ImageDraw.Draw(base)
    fw = font(ARCH, 26); fk = font(ARCH, 40); f1 = font(ANTON, 118)
    # il marchio sta in cima, non a fondo pagina: li' cadeva sopra il prodotto
    line(d, W // 2, SY, 'GM VEGASI', fw, fill=(255, 255, 255, 170), track=11, off=2)
    line(d, W // 2, SY + 80, s['kicker'], fk, fill=CIANO, track=7, off=3)
    line(d, W // 2, SY + 220, s['l1'], f1, fill=WHITE, off=6)
    line(d, W // 2, SY + 340, s['l2'], f1, fill=WHITE, off=6)

    if i == len(SLIDES) - 1:                    # call to action solo sull'ultima
        fb = font(ARCH, 46)
        band(d, W // 2, SY + 482, 'ACQUISTA ORA', fb, bg=ROSA, fg=WHITE, padx=44, pady=20)

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{i+1}-{s['slug']}.png")
    base.convert('RGB').save(path, quality=95)
    print(f'  {path}')

if __name__ == '__main__':
    mancanti = [s['src'] for s in SLIDES if not os.path.exists(os.path.join(IN, s['src']))]
    if mancanti:
        sys.exit(f"Mancano in {IN}/: {', '.join(mancanti)}")
    print('Carosello TikTok 1080x1920:')
    for i, s in enumerate(SLIDES):
        slide(i, s, tutte=[(x['src'], x.get('gain', 1.0), x.get('thr', 247)) for x in SLIDES] if i == 4 else None)
