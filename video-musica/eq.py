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
    # la sfocatura si applica sul piccolo: sul frame intero costerebbe da sola
    # piu' di tutto il resto del render
    return img.filter(ImageFilter.GaussianBlur(0.6)).resize((W, H), Image.BICUBIC)


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


def centrato(dr, txt, f, y, col):
    w = dr.textbbox((0, 0), txt, font=f)[2]
    x = (W - w) / 2
    dr.text((x + 3, y + 4), txt, font=f, fill=(0, 0, 0, 150))
    dr.text((x, y), txt, font=f, fill=col)


def a_capo(dr, parole, f, largh_max):
    """Spezza la riga cantata in piu' righe che stiano nella larghezza data."""
    righe, cur = [], []
    for p in parole:
        prova = cur + [p]
        if dr.textbbox((0, 0), " ".join(prova), font=f)[2] > largh_max and cur:
            righe.append(cur)
            cur = [p]
        else:
            cur = prova
    if cur:
        righe.append(cur)
    return righe


def verso(dr, seg, t, colori):
    """Riga cantata, con la parola in corso accesa sull'accento."""
    _, _, acc, _ = colori
    f = font(64)
    parole = seg.get("words") or [{"w": w, "s": seg["start"], "e": seg["end"]}
                                  for w in seg["text"].split()]
    righe = a_capo(dr, [p["w"] for p in parole], f, W - 200)
    # dissolvenza in entrata e in uscita, mezzo secondo per parte
    a = min(1.0, (t - seg["start"] + 0.25) / 0.45, (seg["end"] + 0.5 - t) / 0.45)
    a = max(0.0, a)

    y = H * 0.70 - (len(righe) - 1) * 40
    i = 0
    for riga in righe:
        largh = dr.textbbox((0, 0), " ".join(riga), font=f)[2]
        x = (W - largh) / 2
        for w in riga:
            p = parole[i]; i += 1
            accesa = p["s"] <= t <= p["e"] + 0.08
            col = acc if accesa else (255, 255, 255)
            dr.text((x + 3, y + 4), w, font=f, fill=(0, 0, 0, int(150 * a)))
            dr.text((x, y), w, font=f, fill=tuple(col) + (int(255 * a),))
            x += dr.textbbox((0, 0), w + " ", font=f)[2]
        y += 80


def testo(dr, titolo, artista, avanzamento, seg=None, t=0.0, colori=None):
    if seg is not None:
        # con i versi a schermo il titolo sale in alto, se no si accavallano
        if titolo:
            centrato(dr, titolo.upper(), font(52), H * 0.085, (255, 255, 255))
        if artista:
            centrato(dr, artista, font(34), H * 0.085 + 68, (232, 232, 232))
        verso(dr, seg, t, colori)
    else:
        if titolo:
            centrato(dr, titolo.upper(), font(84), H * 0.72, (255, 255, 255))
        if artista:
            centrato(dr, artista, font(46), H * 0.72 + 105, (235, 235, 235))

    # barra di avanzamento del brano
    y, m = int(H * 0.86), 120
    dr.rounded_rectangle([m, y, W - m, y + 10], radius=5, fill=(255, 255, 255, 70))
    dr.rounded_rectangle([m, y, m + (W - 2 * m) * avanzamento, y + 10],
                         radius=5, fill=(255, 255, 255))


def spezza(seg, max_dur=4.5, max_par=7):
    """Segmenti lunghi divisi sui tempi delle parole: a schermo una riga che
    resta ferma dieci secondi non segue piu' il cantato."""
    par = seg.get("words") or []
    if len(par) <= max_par and seg["end"] - seg["start"] <= max_dur:
        return [seg]
    if not par:
        return [seg]
    fuori, cur = [], []
    for p in par:
        cur.append(p)
        troppo_lungo = cur[-1]["e"] - cur[0]["s"] > max_dur
        if len(cur) >= max_par or troppo_lungo:
            fuori.append(cur)
            cur = []
    if cur:
        fuori.append(cur)
    return [{"start": g[0]["s"], "end": g[-1]["e"],
             "text": " ".join(w["w"] for w in g), "words": g} for g in fuori]


def carica_versi(path, start, durata):
    """Segmenti dal JSON della trascrizione, riportati a zero sul ritaglio."""
    import json
    with open(path, encoding="utf-8") as f:
        dati = [x for s in json.load(f) for x in spezza(s)]
    out = []
    for s in dati:
        a, b = s["start"] - start, s["end"] - start
        if b <= 0 or a >= durata or not s.get("text"):
            continue
        out.append({"start": a, "end": b, "text": s["text"],
                    "words": [{"w": w["w"], "s": w["s"] - start, "e": w["e"] - start}
                              for w in s.get("words") or []]})
    return out


def verso_a(versi, t):
    for s in versi:
        if s["start"] - 0.25 <= t <= s["end"] + 0.5:
            return s
    return None


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
    versi = carica_versi(args.testo, args.start, durata) if args.testo else None

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", args.out)
    cmd = [FFMPEG, "-y", "-v", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    if args.muto:
        # nessuna traccia audio: il brano lo mette l'app al momento della
        # pubblicazione, e due audio sovrapposti non si vogliono
        coda = ["-an"]
    else:
        cmd += ["-ss", str(args.start), "-t", f"{durata:.3f}", "-i", args.audio]
        coda = ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
            "-pix_fmt", "yuv420p"] + coda + ["-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    for f in range(n):
        img = sfondo(f / FPS, float(en[f]), colori)
        barre(img, sp[f], colori)
        dr = ImageDraw.Draw(img, "RGBA")
        t = f / FPS
        seg = verso_a(versi, t) if versi else None
        testo(dr, args.titolo, args.artista, f / max(n - 1, 1), seg, t, colori)
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
    p.add_argument("--testo", help="JSON dei versi con i tempi (vedi versi.py)")
    p.add_argument("--muto", action="store_true",
                   help="esporta senza audio: il brano lo mette TikTok")
    p.add_argument("--crf", type=int, default=20,
                   help="qualita' H.264: piu' alto = file piu' leggero")
    p.add_argument("--out", default="eq.mp4")
    render(p.parse_args())


if __name__ == "__main__":
    main()
