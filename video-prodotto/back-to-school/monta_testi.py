"""Sovraimprime i testi del copione sullo spot generato e taglia la coda muta.

Il video generato esce a 480p e dura 11,10 s, ma la presentatrice smette di
parlare a 8,6 s: l'ultimo secondo e mezzo e' lei ferma che sorride. Si taglia.

I tempi dei cartelli seguono la voce montata da `allinea_voce.py`. Il richiamo
all'azione entra mezzo secondo prima della voce: l'occhio legge, poi l'orecchio
conferma. Serve anche a coprire i 0,50 s in cui la voce corre su bocca ferma.

    python3 back-to-school/monta_testi.py
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import os, shutil, subprocess
import imageio_ffmpeg

W, H, FPS = 1080, 1920, 24
FINE = 9.60                       # oltre, la bocca e' ferma e la voce e' finita
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
OUT = os.path.join(ROOT, 'out')
ANTON = os.path.join(ROOT, 'fonts', 'Anton.ttf')
FF = imageio_ffmpeg.get_ffmpeg_exe()

BIANCO = (255, 255, 255)
CIANO = (37, 244, 238)            # coordinato all'end card GM Vegasi TikTok Shop

# (righe, entra, esce). I claim sono quelli dell'utente, parola per parola.
CARTELLI = [
    ([('È TEMPO DI PENSARE', BIANCO), ('ALLA SCUOLA', BIANCO)],        0.30, 1.88),
    ([('ZAINI · ASTUCCI', BIANCO), ('BORRACCE', BIANCO)],              1.98, 4.55),
    ([('ANCHE CON I PERSONAGGI', BIANCO), ('DEI CARTONI', BIANCO)],    4.65, 6.80),
    ([('DA NOI TROVI TUTTO', BIANCO)],                                 6.90, 7.75),
    ([('DA NOI TROVI TUTTO', BIANCO), ('COSA ASPETTI?', CIANO)],       7.80, FINE - 0.10),
]

# il testo non scende sotto questa quota: sotto ci vanno didascalia e pulsanti
# di TikTok e Instagram
FONDO_TESTO = 1400

_F = {}
def font(s):
    if s not in _F:
        _F[s] = ImageFont.truetype(ANTON, int(s))
    return _F[s]


def corpo(righe, larghezza):
    """Il corpo si misura su textbbox, non su font.size: le maiuscole accentate
    (È di 'È TEMPO') salgono sopra l'altezza nominale e verrebbero tagliate."""
    d = ImageDraw.Draw(Image.new('RGB', (8, 8)))
    c = 200
    while c > 30:
        f = font(c)
        if max(d.textbbox((0, 0), r[0], font=f)[2] for r in righe) <= larghezza:
            return c
        c -= 2
    return c


def scrivi(base, righe, alpha):
    if alpha <= 0.004:
        return base
    margine = 80
    c = corpo(righe, W - 2 * margine)
    f = font(c)
    inter = int(c * 1.14)
    d0 = ImageDraw.Draw(Image.new('RGB', (8, 8)))
    h0 = d0.textbbox((0, 0), righe[0][0], font=f)
    altezza = inter * (len(righe) - 1) + (h0[3] - h0[1])
    y0 = FONDO_TESTO - altezza

    # velatura scura: senza, il bianco sparisce sul pavimento chiaro
    vel = Image.new('L', (W, H), 0)
    dv = ImageDraw.Draw(vel)
    dv.rounded_rectangle([margine - 46, y0 - 42, W - margine + 46, y0 + altezza + 42],
                         radius=34, fill=205)
    vel = vel.filter(ImageFilter.GaussianBlur(26)).point(lambda v: int(v * alpha))
    base = Image.composite(Image.new('RGB', (W, H), (0, 0, 0)), base, vel)

    lay = Image.new('RGB', (W, H), (0, 0, 0))
    msk = Image.new('L', (W, H), 0)
    dl, dm = ImageDraw.Draw(lay), ImageDraw.Draw(msk)
    y = y0
    for testo, colore in righe:
        bb = dl.textbbox((0, 0), testo, font=f)
        x = (W - (bb[2] - bb[0])) // 2 - bb[0]
        dl.text((x, y - bb[1]), testo, font=f, fill=colore)
        dm.text((x, y - bb[1]), testo, font=f, fill=int(255 * alpha))
        y += inter
    return Image.composite(lay, base, msk)


def rampa(t, t0, t1, su=0.16, giu=0.14):
    if t < t0 or t > t1:
        return 0.0
    return min(1.0, (t - t0) / su, (t1 - t) / giu)


def main():
    src = os.path.join(OUT, 'f11')
    fs = sorted(os.listdir(src))
    frames = os.path.join(OUT, 'frames_testi')
    shutil.rmtree(frames, ignore_errors=True)
    os.makedirs(frames)

    n = int(round(FINE * FPS))
    for i in range(n):
        t = i / FPS
        fr = Image.open(os.path.join(src, fs[min(i, len(fs) - 1)])).convert('RGB')
        fr = fr.resize((W, H), Image.LANCZOS)
        for righe, ta, tb in CARTELLI:
            a = rampa(t, ta, tb)
            if a > 0:
                fr = scrivi(fr, righe, a)
        fr.save(os.path.join(frames, '%04d.png' % i))
        if i % 40 == 0:
            print('  frame %d/%d' % (i, n))

    mp4 = os.path.join(OUT, 'spot-back-to-school-finale.mp4')
    subprocess.run([FF, '-y', '-hide_banner', '-loglevel', 'error',
                    '-framerate', str(FPS), '-i', os.path.join(frames, '%04d.png'),
                    '-i', os.path.join(OUT, 'mix_finale.wav'),
                    '-map', '0:v', '-map', '1:a', '-t', '%.2f' % FINE,
                    '-c:v', 'libx264', '-profile:v', 'high', '-crf', '19',
                    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', mp4], check=True)
    print('scritto', mp4)


if __name__ == '__main__':
    main()
