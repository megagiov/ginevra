"""Spot back to school 9:16 — montaggio locale, nessun pixel di prodotto generato.

La presentatrice e' l'unica immagine generata e ha il fondo sfocato: il modello
storpia le scritte sui prodotti (KUROMI -> ROIRCHMI, Mickey Mouse -> Mickey
eHouse), quindi la merce si vede solo nelle foto vere del negozio.

    python3 back-to-school/build_bts.py
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import json, os, shutil, subprocess, wave
import imageio_ffmpeg

W, H, FPS = 1080, 1920, 30
FF = imageio_ffmpeg.get_ffmpeg_exe()
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
FOTO = os.path.join(BASE, 'foto')
OUT = os.path.join(ROOT, 'out')
ANTON = os.path.join(ROOT, 'fonts', 'Anton.ttf')

WHITE = (255, 255, 255)
CIANO = (37, 244, 238)          # coordinati all'end card GM Vegasi TikTok Shop
ROSA = (254, 44, 85)

LEAD = 0.30                     # silenzio prima della prima parola
PAUSA_MAX = 0.40                # le pause vere della voce si accorciano, non si stira mai l'audio
CODA = 0.55                     # aria dopo l'ultima parola

# --------------------------------------------------------------------------
# audio: si taglia solo dentro i silenzi misurati sull'onda. Stirare i segmenti
# per accorciare il parlato suona come tono instabile ed e' gia' stato scartato.
# --------------------------------------------------------------------------

def carica_wav(path):
    w = wave.open(path)
    sr, n = w.getframerate(), w.getnframes()
    a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    return a, sr


def trova_pause(a, sr, soglia=0.02, minimo=0.15):
    win = int(sr * 0.02)
    env = np.convolve(np.abs(a), np.ones(win) / win, 'same')
    th = env.max() * soglia
    voce = env > th
    d = np.diff(voce.astype(np.int8))
    inizi, fini = np.where(d == -1)[0], np.where(d == 1)[0]
    if len(fini) and len(inizi) and fini[0] < inizi[0]:
        fini = fini[1:]
    pause = [(s, e) for s, e in zip(inizi, fini) if (e - s) / sr > minimo]
    primo = int(np.argmax(voce))
    ultimo = len(voce) - 1 - int(np.argmax(voce[::-1]))
    return pause, primo, ultimo


def monta_voce(src, dst):
    a, sr = carica_wav(src)
    pause, primo, ultimo = trova_pause(a, sr)
    xf = int(sr * 0.010)                      # dissolvenza al giunto, evita il click

    pezzi, cuts, cur = [], [], primo
    for s, e in pause:
        pezzi.append(a[cur:s])
        tenuta = min(e - s, int(sr * PAUSA_MAX))
        pezzi.append(a[s:s + tenuta] * 0.0)
        cuts.append(sum(len(p) for p in pezzi) - tenuta // 2)
        cur = e
    pezzi.append(a[cur:ultimo])

    fuso = pezzi[0]
    for p in pezzi[1:]:
        if len(fuso) >= xf and len(p) >= xf:
            r = np.linspace(0, 1, xf)
            fuso[-xf:] = fuso[-xf:] * (1 - r) + p[:xf] * r
            p = p[xf:]
            cuts = [c - xf if c > len(fuso) else c for c in cuts]
        fuso = np.concatenate([fuso, p])

    lead = np.zeros(int(sr * LEAD), np.float32)
    coda = np.zeros(int(sr * CODA), np.float32)
    fuso = np.concatenate([lead, fuso, coda])
    tempi = [(c + len(lead)) / sr for c in cuts]

    w = wave.open(dst, 'w')
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((np.clip(fuso, -1, 1) * 32767).astype(np.int16).tobytes())
    w.close()
    return len(fuso) / sr, tempi


# --------------------------------------------------------------------------
# immagine
# --------------------------------------------------------------------------

_F = {}
def font(size):
    if size not in _F:
        _F[size] = ImageFont.truetype(ANTON, size)
    return _F[size]


def finestra(im, r0, r1, t):
    """Carrellata digitale: ritaglio che si stringe da r0 a r1, con ease-in-out."""
    e = t * t * (3 - 2 * t)
    box = [a + (b - a) * e for a, b in zip(r0, r1)]
    x, y, w, h = box
    return im.resize((W, H), Image.LANCZOS, box=(x, y, x + w, y + h))


def blocco_testo(righe, larghezza):
    """Corpo massimo che tiene la riga piu' lunga dentro la larghezza utile.

    La misura va presa su textbbox e non su font.size: le maiuscole accentate
    (E' di "E' TEMPO") salgono sopra l'altezza nominale e verrebbero tagliate.
    """
    d = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    corpo = 200
    while corpo > 30:
        f = font(corpo)
        if max(d.textbbox((0, 0), r[0], font=f)[2] for r in righe) <= larghezza:
            break
        corpo -= 2
    return corpo


def disegna_testo(base, righe, ancora, alpha):
    if alpha <= 0.003:
        return base
    margine = 80
    corpo = blocco_testo(righe, W - 2 * margine)
    f = font(corpo)
    interlinea = int(corpo * 1.12)
    d0 = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    hs = [d0.textbbox((0, 0), r[0], font=f)[3] - d0.textbbox((0, 0), r[0], font=f)[1] for r in righe]
    altezza = sum(hs) + interlinea - hs[-1] + (len(righe) - 1) * (interlinea - hs[0]) * 0
    altezza = interlinea * (len(righe) - 1) + hs[0]
    y0 = ancora if ancora >= 0 else H + ancora - altezza

    # velatura scura sotto il testo: senza, il bianco sparisce sulle mensole chiare
    vel = Image.new('L', (W, H), 0)
    dv = ImageDraw.Draw(vel)
    pad_x, pad_y = 46, 40
    x0 = margine - pad_x
    dv.rounded_rectangle([x0, y0 - pad_y, W - x0, y0 + altezza + pad_y], radius=34, fill=165)
    vel = vel.filter(ImageFilter.GaussianBlur(26))
    vel = vel.point(lambda v: int(v * alpha))
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
        y += interlinea
    return Image.composite(lay, base, msk)


def rampa(t, t0, t1, salita=0.18, discesa=0.14):
    if t < t0 or t > t1:
        return 0.0
    return min(1.0, (t - t0) / salita, (t1 - t) / discesa)


def main():
    os.makedirs(OUT, exist_ok=True)
    durata, cuts = monta_voce(os.path.join(OUT, 'voce.wav'), os.path.join(OUT, 'voce_bts.wav'))
    print('voce montata: %.2f s, stacchi a %s' % (durata, ['%.2f' % c for c in cuts]))

    # gli stacchi cadono nelle pause della voce: 1 dopo "scuola", 3 dopo
    # "borracce", 4 dopo "cartoni". La pausa 2 e' interna all'elenco.
    tB, tC, tD = cuts[0], cuts[2], cuts[3]
    fine = durata

    pres = Image.open(os.path.join(FOTO, 'avatar-sfocato.png')).convert('RGB')
    close = Image.open(os.path.join(FOTO, 'negozio-close.jpg')).convert('RGB')
    largo = Image.open(os.path.join(FOTO, 'negozio-largo.jpg')).convert('RGB')

    scene = [
        # (fine scena, immagine, ritaglio iniziale, ritaglio finale)
        (tB,   pres,  (0, 0, 1536, 2731),      (54, 96, 1428, 2539)),
        (tC,   close, (192, 0, 1080, 1920),    (268, 88, 972, 1728)),
        (tD,   largo, (0, 0, 1012, 1799),      (88, 104, 900, 1600)),
        (fine, pres,  (150, 300, 1236, 2197),  (198, 356, 1140, 2027)),
    ]

    testi = [
        ([('È TEMPO DI PENSARE', WHITE), ('ALLA SCUOLA', WHITE)],            0.42, tB - 0.12, 250),
        ([('ZAINI · ASTUCCI', WHITE), ('BORRACCE', WHITE)],                  tB + 0.18, tC - 0.12, -560),
        ([('ANCHE CON I PERSONAGGI', WHITE), ('DEI CARTONI', WHITE)],        tC + 0.18, tD - 0.12, -560),
        ([('DA NOI TROVI TUTTO', WHITE), ('COSA ASPETTI?', CIANO)],          tD + 0.10, fine - 0.20, 250),
    ]

    frames = os.path.join(OUT, 'frames_bts')
    shutil.rmtree(frames, ignore_errors=True)
    os.makedirs(frames)

    n = int(round(fine * FPS))
    for i in range(n):
        t = i / FPS
        t0 = 0.0
        for tfine, im, r0, r1 in scene:
            if t < tfine or tfine == fine:
                fr = finestra(im, r0, r1, min(1.0, (t - t0) / max(0.001, tfine - t0)))
                break
            t0 = tfine
        for righe, ta, tb, ancora in testi:
            a = rampa(t, ta, tb)
            if a > 0:
                fr = disegna_testo(fr, righe, ancora, a)
        fr.save(os.path.join(frames, '%04d.png' % i))
        if i % 40 == 0:
            print('  frame %d/%d' % (i, n))

    mp4 = os.path.join(OUT, 'spot-back-to-school.mp4')
    subprocess.run([FF, '-y', '-hide_banner', '-loglevel', 'error',
                    '-framerate', str(FPS), '-i', os.path.join(frames, '%04d.png'),
                    '-i', os.path.join(OUT, 'voce_bts.wav'),
                    '-map', '0:v', '-map', '1:a', '-shortest',
                    '-c:v', 'libx264', '-profile:v', 'high', '-crf', '19',
                    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', mp4], check=True)
    print('scritto', mp4)
    json.dump({'durata': fine, 'stacchi': [tB, tC, tD]},
              open(os.path.join(OUT, 'tempi_bts.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
