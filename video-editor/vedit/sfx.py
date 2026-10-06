"""Effetti sonori sintetizzati in locale: nessun file scaricato, nessuna licenza.

Con "sfx": true nel piano ogni testo che entra ha il suo fruscio, foto e bollini un
pop, gli stacchi col flash un colpo, i glitch un disturbo. Si possono aggiungere suoni
a mano con "sfx": {"extra": [{"type": "pop", "at": 2.0}], "gain": 0}.
"""
import subprocess
import numpy as np
from .common import die, tool, SR

RNG = np.random.default_rng(7)  # stesso piano -> stessi suoni


def _lowpass(x, fc):
    """Filtro a un polo con frequenza di taglio che puo' variare campione per campione."""
    a = np.exp(-2 * np.pi * np.broadcast_to(fc, x.shape) / SR)
    y, acc = np.empty_like(x), 0.0
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def whoosh(dur=0.42, peak=0.7):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    noise = RNG.standard_normal(n)
    fc = 350 + 4200 * np.sin(np.pi * np.clip(t / peak, 0, 1) / 2) ** 2 * np.where(t < peak, 1, 1 - (t - peak) / (1 - peak) * 0.8)
    band = _lowpass(noise, fc) - _lowpass(noise, fc * 0.25)
    env = np.where(t < peak, (t / peak) ** 2, np.exp(-(t - peak) * 14))
    mono = band * env
    pan = np.clip(t * 1.3 - 0.15, 0, 1)  # passa da sinistra a destra
    return np.stack([mono * (1 - 0.6 * pan), mono * (0.4 + 0.6 * pan)], 1), peak * dur


def pop(f0=1500, f1=420, dur=0.11):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.018)
    mono = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.035)
    mono[:int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    return np.stack([mono, mono], 1), 0.0


def impact(dur=0.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 42 + 70 * np.exp(-t / 0.05)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    hit = _lowpass(RNG.standard_normal(n), 2500) * np.exp(-t / 0.012) * 1.5
    mono = np.tanh(1.6 * (boom + hit))
    mono[:int(0.001 * SR)] *= np.linspace(0, 1, int(0.001 * SR))  # niente attacco a gradino
    return np.stack([mono, mono], 1), 0.0


def glitch(dur=0.16):
    n = int(dur * SR)
    t = np.arange(n) / SR
    crush = np.round(RNG.standard_normal(n) * 3) / 3
    sq = np.sign(np.sin(2 * np.pi * 180 * t))
    gate = (np.floor(t / 0.018) % 2 == 0)
    mono = (0.6 * crush + 0.4 * sq) * gate * np.exp(-t / 0.09)
    return np.stack([mono, -mono * 0.8], 1), 0.0


# livelli relativi, a parita' di energia percepita (vedi _loud)
SOUNDS = dict(whoosh=(whoosh, 1.0), pop=(pop, 0.65), impact=(impact, 0.85), glitch=(glitch, 0.45))


def events(plan, beats):
    """Suoni automatici: dove entrano i testi e dove ci sono gli effetti di stacco."""
    ev = []
    for b in beats:
        if b['type'] in ('hook', 'label', 'cta', 'text', 'card', 'list'):
            ev.append(('impact', b['s']) if b.get('full') else ('whoosh', b['s'] + 0.06))
        elif b['type'] in ('badge', 'image', 'logo'):
            ev.append(('pop', b['s'] + 0.03))
    for m in plan.get('fx', {}).get('moves', []):
        if m['type'] == 'flash' or (m['type'] == 'punch' and m['at'] == 0):
            ev.append(('impact', m['at']))
        elif m['type'] == 'glitch':
            ev.append(('glitch', m['start']))
    cfg = plan.get('sfx') if isinstance(plan.get('sfx'), dict) else {}
    ev += [(x['type'], x['at']) for x in cfg.get('extra', [])]
    out = []  # due colpi quasi insieme suonano come uno sporco: se ne tiene uno
    for k, t in sorted(ev, key=lambda e: e[1]):
        if not any(k == k2 and abs(t - t2) < 0.12 for k2, t2 in out):
            out.append((k, t))
    return out, cfg.get('gain', 0)


def _loud(snd, win=0.05):
    """Energia dei 50 ms piu' forti: pareggia i suoni per come si sentono, non per il picco."""
    e = (snd ** 2).mean(axis=1)
    k = max(1, int(win * SR))
    c = np.convolve(e, np.ones(k) / k, mode='valid')
    return np.sqrt(c.max()) + 1e-9


def build(path, plan, beats, total):
    evs, gain = events(plan, beats)
    track = np.zeros((int(total * SR) + SR, 2))
    for k, t in evs:
        if k not in SOUNDS:
            die(f'suono sconosciuto: {k}. Tipi: {", ".join(SOUNDS)}')
        fn, level = SOUNDS[k]
        snd, lead = fn()
        i = int(max(0.0, t - lead) * SR)
        j = min(len(track), i + len(snd))
        track[i:j] += level * snd[:j - i] / _loud(snd)
    track = track[:int(total * SR)]
    pk = np.abs(track).max()
    if pk > 0:
        track *= 10 ** ((-4.5 + gain) / 20) / pk  # picco a -4,5 dBFS: la codifica AAC fa salire i transienti
    p = subprocess.run([tool('ffmpeg'), '-v', 'error', '-y', '-f', 'f32le', '-ac', '2', '-ar', str(SR),
                        '-i', '-', '-c:a', 'pcm_s16le', str(path)], input=track.astype(np.float32).tobytes())
    if p.returncode:
        die('scrittura degli effetti sonori fallita')
    print(f'  suoni: {len(evs)} ({", ".join(sorted({k for k, _ in evs}))})')
