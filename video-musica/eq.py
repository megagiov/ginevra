#!/usr/bin/env python3
"""Equalizzatore virtuale 9:16 per TikTok, da un brano audio.

    python3 eq.py brano.mp3 --start 45 --dur 30 --titolo "Nome brano" \
            --artista "Artista" --preset sunset

Nessun servizio esterno: decodifica, FFT, render e codifica girano in locale.
"""
import argparse, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1080, 1920, 30
SR = 44100
BANDS = 48            # barre per lato dell'equalizzatore
FMIN, FMAX = 30.0, 16000.0

# gradienti: (colore alto, colore basso, accento barre, accento glow)
PRESET = {
    "sunset":  ((255, 61, 129), (36, 12, 84), (255, 214, 102), (255, 88, 160)),
    "ocean":   ((0, 229, 255), (10, 20, 90), (120, 255, 214), (0, 180, 255)),
    "neon":    ((178, 71, 255), (12, 6, 40), (57, 255, 176), (150, 60, 255)),
    "ember":   ((255, 138, 0), (40, 8, 8), (255, 236, 179), (255, 96, 32)),
    "mono":    ((235, 235, 235), (14, 14, 14), (255, 255, 255), (160, 160, 160)),
}


def decodifica(path, start, dur):
    """Audio -> float32 mono a 44.1 kHz, piu' il ritaglio usato per il muxing."""
    cmd = [FFMPEG, "-v", "error", "-ss", str(start), "-t", str(dur),
           "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def bordi_bande():
    """Estremi delle bande, log-spaziati: l'occhio legge le ottave, non gli Hz."""
    return np.geomspace(FMIN, FMAX, BANDS + 1)


def spettro(pcm, n_frame):
    """Matrice (n_frame, BANDS) normalizzata 0..1, con smoothing temporale."""
    win_n = 2048
    win = np.hanning(win_n).astype(np.float32)
    freqs = np.fft.rfftfreq(win_n, 1.0 / SR)
    bordi = bordi_bande()
    idx = [np.where((freqs >= bordi[b]) & (freqs < bordi[b + 1]))[0]
           for b in range(BANDS)]
    # bande alte molto piu' povere di energia: compenso con una pendenza
    tilt = np.linspace(1.0, 3.2, BANDS).astype(np.float32)

    out = np.zeros((n_frame, BANDS), dtype=np.float32)
    for f in range(n_frame):
        c = int(f * SR / FPS)
        a, b = c - win_n // 2, c + win_n // 2
        seg = np.zeros(win_n, dtype=np.float32)
        lo, hi = max(a, 0), min(b, len(pcm))
        if hi > lo:
            seg[lo - a:hi - a] = pcm[lo:hi]
        mag = np.abs(np.fft.rfft(seg * win))
        for b_i, sel in enumerate(idx):
            out[f, b_i] = mag[sel].mean() if sel.size else 0.0
        out[f] *= tilt

    out = np.log1p(out * 12.0)
    # Espansione per banda: il fondo di ogni banda va a zero e il picco a uno.
    # Senza, su un brano compresso come il disco tutte le barre restano a fondo
    # scala e l'equalizzatore diventa una massa piena che non balla.
    fondo = np.percentile(out, 25.0, axis=0)
    picco = np.percentile(out, 98.0, axis=0)
    out = (out - fondo) / np.maximum(picco - fondo, 1e-6)
    out = np.clip(out, 0.0, 1.0) ** 1.35
    # un filo di fondo comune, se no le bande scariche spariscono del tutto
    out = 0.08 + 0.92 * out

    # attacco rapido, rilascio lento: le barre non sfarfallano
    sm = np.zeros_like(out)
    prev = out[0]
    for f in range(n_frame):
        cur = out[f]
        prev = np.where(cur > prev, cur, prev * 0.72 + cur * 0.28)
        sm[f] = prev
    return sm


def livelli(pcm, n_frame):
    """RMS per frame, 0..1: pilota il respiro dello sfondo."""
    hop = SR / FPS
    v = np.zeros(n_frame, dtype=np.float32)
    for f in range(n_frame):
        a = int(f * hop)
        seg = pcm[a:a + int(hop)]
        if seg.size:
            v[f] = float(np.sqrt(np.mean(seg.astype(np.float64) ** 2)))
    m = v.max()
    return v / m if m > 0 else v


def sfondo(t, energia, colori):
    """Gradiente animato a bassa risoluzione, poi ingrandito: costa poco."""
    alto, basso, _, glow = colori
    sw, sh = 96, 170
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
    yy /= sh
    xx /= sw

    onda = (0.5 + 0.5 * np.sin(2 * math.pi * (yy * 1.4 + t * 0.05)
                               + np.sin(xx * 3.1 + t * 0.31) * 0.9))
    k = np.clip(yy * 0.75 + onda * 0.25, 0.0, 1.0)[..., None]
    base = np.array(basso, np.float32) * k + np.array(alto, np.float32) * (1 - k)

    # alone centrale che pulsa sul volume
    d = np.sqrt((xx - 0.5) ** 2 + ((yy - 0.46) * 0.62) ** 2)
    alone = np.clip(1.0 - d / (0.30 + 0.22 * energia), 0.0, 1.0) ** 2
    base += np.array(glow, np.float32) * (alone * (0.22 + 0.5 * energia))[..., None]

    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    return img.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(6))


def font(px, grassetto=True):
    qui = os.path.dirname(os.path.abspath(__file__))
    cand = [os.path.join(qui, "fonts", "Anton.ttf" if grassetto else "Inter.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in cand:
        if os.path.exists(p):
            return ImageFont.truetype(p, px)
    return ImageFont.load_default()


def geometria_barre(val, colori):
    """Rettangoli dell'equalizzatore a specchio, con il loro colore."""
    _, _, acc, _ = colori
    cy = H * 0.52
    marg = 70
    passo = (W - 2 * marg) / BANDS
    largh = passo * 0.62
    rett = []
    for i, v in enumerate(val):
        x = marg + i * passo + (passo - largh) / 2
        h = 26 + v * (H * 0.30)
        # tinta che scivola verso il bianco con l'ampiezza
        c = tuple(min(255, int(acc[j] * (0.45 + 0.55 * v) + 60 * v)) for j in range(3))
        rett.append(([x, cy - h, x + largh, cy - 10], c, largh / 2))
        rett.append(([x, cy + 10, x + largh, cy + 10 + h * 0.55], c, largh / 2))
    return rett


def barre(img, val, colori):
    """Alone diffuso in bassa risoluzione, poi le barre nitide sopra."""
    rett = geometria_barre(val, colori)

    k = 5  # l'alone si disegna a 1/5 e si allarga: costa un quinto del blur
    alone = Image.new("RGB", (W // k, H // k), (0, 0, 0))
    da = ImageDraw.Draw(alone)
    for (x0, y0, x1, y1), c, r in rett:
        da.rounded_rectangle([x0 / k, y0 / k, x1 / k, y1 / k], radius=r / k, fill=c)
    alone = alone.filter(ImageFilter.GaussianBlur(4)).resize((W, H), Image.BICUBIC)

    base = np.asarray(img, np.float32)
    g = np.asarray(alone, np.float32) * 0.85
    img.paste(Image.fromarray(np.clip(255 - (255 - base) * (255 - g) / 255,
                                      0, 255).astype(np.uint8)))

    dr = ImageDraw.Draw(img, "RGBA")
    for rect, c, r in rett:
        dr.rounded_rectangle(rect, radius=r, fill=c)


def testo(dr, titolo, artista, avanzamento):
    f_t, f_a = font(84), font(46)
    def centrato(txt, f, y, col, ombra=True):
        w = dr.textbbox((0, 0), txt, font=f)[2]
        x = (W - w) / 2
        if ombra:
            dr.text((x + 3, y + 4), txt, font=f, fill=(0, 0, 0, 160))
        dr.text((x, y), txt, font=f, fill=col)

    if titolo:
        centrato(titolo.upper(), f_t, H * 0.72, (255, 255, 255))
    if artista:
        centrato(artista, f_a, H * 0.72 + 105, (235, 235, 235))

    # barra di avanzamento del brano
    y, m = int(H * 0.86), 120
    dr.rounded_rectangle([m, y, W - m, y + 10], radius=5, fill=(255, 255, 255, 70))
    dr.rounded_rectangle([m, y, m + (W - 2 * m) * avanzamento, y + 10],
                         radius=5, fill=(255, 255, 255))


def render(args):
    pcm = decodifica(args.audio, args.start, args.dur)
    if pcm.size == 0:
        sys.exit("audio vuoto: controlla --start, il brano e' piu' corto?")
    durata = pcm.size / SR
    n = int(durata * FPS)
    print(f"{durata:.2f} s, {n} frame")

    sp = spettro(pcm, n)
    en = livelli(pcm, n)
    colori = PRESET[args.preset]

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", args.out)
    proc = subprocess.Popen(
        [FFMPEG, "-y", "-v", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-ss", str(args.start), "-t", f"{durata:.3f}", "-i", args.audio,
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)

    for f in range(n):
        img = sfondo(f / FPS, float(en[f]), colori)
        barre(img, sp[f], colori)
        dr = ImageDraw.Draw(img, "RGBA")
        testo(dr, args.titolo, args.artista, f / max(n - 1, 1))
        proc.stdin.write(img.tobytes())
        if f % (FPS * 5) == 0:
            print(f"  frame {f}/{n}", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg ha fallito la codifica")
    print("scritto", out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("audio")
    p.add_argument("--start", type=float, default=0.0, help="secondo di inizio")
    p.add_argument("--dur", type=float, default=30.0, help="durata in secondi")
    p.add_argument("--titolo", default="")
    p.add_argument("--artista", default="")
    p.add_argument("--preset", default="sunset", choices=sorted(PRESET))
    p.add_argument("--out", default="eq.mp4")
    render(p.parse_args())


if __name__ == "__main__":
    main()
