"""Effetti sul video: zoom che segue il dettaglio, colpo di zoom, tremolio, flash, glitch, colore.

Lavora fotogramma per fotogramma con Pillow tra due pipe ffmpeg: lo zoom e' al
sottopixel, senza lo scatto a gradini di zoompan. Si scrive in plan.json alla voce
"fx" (schema in docs/PIANO.md) e gira da solo dentro `gfx`, solo se il piano degli
effetti o il montato sono cambiati.
"""
import hashlib, json, math, subprocess
from PIL import Image, ImageChops
from .common import ff, die, tool, W, H, FPS, VENC

# contrasto e saturazione un filo piu' alti, nitidezza per i video compressi
# (WhatsApp), vignetta leggera che porta l'occhio al centro
GRADE = 'eq=contrast=1.07:saturation=1.18:brightness=0.01,unsharp=5:5:0.7:5:5:0.0,vignette=PI/5'
WHITE = Image.new('RGB', (W, H), (255, 255, 255))


def smooth(p):
    p = min(1.0, max(0.0, p))
    return p * p * (3 - 2 * p)


def track(at, t):
    """[x, y] fisso, oppure [[t, x, y], ...] per inseguire un dettaglio mentre la camera si muove."""
    if not at:
        return 0.5, 0.5
    if isinstance(at[0], (int, float)):
        return at[0], at[1]
    if t <= at[0][0]:
        return at[0][1], at[0][2]
    for a, b in zip(at, at[1:]):
        if t <= b[0]:
            p = (t - a[0]) / max(1e-6, b[0] - a[0])
            return a[1] + (b[1] - a[1]) * p, a[2] + (b[2] - a[2]) * p
    return at[-1][1], at[-1][2]


def state(moves, t):
    s, cx, cy, dx, dy, flash, rgb = 1.0, 0.5, 0.5, 0.0, 0.0, 0.0, 0
    for m in moves:
        k = m['type']
        if k in ('zoom', 'push'):
            a, b = m['start'], m['end']
            if not a <= t <= b:
                continue
            fr, to = m.get('from', 1.0), m.get('to', 1.3)
            if k == 'push':  # lento e continuo per tutta la durata
                p = smooth((t - a) / max(1e-6, b - a))
            else:            # entra in `ramp`, resta, ed esce solo se out=true
                r = m.get('ramp', 0.35)
                p = smooth((t - a) / r) if r > 0 else 1.0
                if m.get('out'):
                    p = min(p, smooth((b - t) / r))
            s *= fr + (to - fr) * p
            cx, cy = track(m.get('at'), t)
        elif k == 'punch':  # colpo di zoom sullo stacco: parte stretto e si apre
            a, d = m['at'], m.get('dur', 0.3)
            if a <= t <= a + d:
                s *= 1 + m.get('amount', 0.12) * (1 - (1 - (1 - (t - a) / d) ** 3))
        elif k == 'shake':
            a, b, amp = m['start'], m['end'], m.get('amp', 10)
            if a <= t <= b:
                env = min(1.0, (b - t) / 0.12)
                dx += amp * env * (math.sin(t * 53) + 0.6 * math.sin(t * 97 + 1.3)) / 1.6
                dy += amp * env * (math.sin(t * 61 + 0.7) + 0.6 * math.sin(t * 89)) / 1.6
                s = max(s, 1 + 2.4 * amp / W)  # margine, cosi' il tremolio non mostra bordi neri
        elif k == 'flash':
            a, d, pk = m['at'], m.get('dur', 0.25), m.get('peak', 0.85)
            if a - 0.07 <= t < a:
                flash = max(flash, pk * (t - (a - 0.07)) / 0.07)
            elif a <= t <= a + d:
                flash = max(flash, pk * (1 - (t - a) / d) ** 2)
        elif k == 'glitch':
            a, b = m['start'], m['end']
            if a <= t <= b:
                amp = m.get('amp', 12)
                rgb = int(amp if (int(t * FPS) // 2) % 2 == 0 else -0.6 * amp)
        else:
            die(f'effetto sconosciuto: {k}. Tipi: zoom, push, punch, shake, flash, glitch')
    return s, cx, cy, dx, dy, flash, rgb


def apply(img, st):
    s, cx, cy, dx, dy, flash, rgb = st
    if s > 1.0005:
        w, h = W / s, H / s
        x0 = min(max(cx * W - w / 2 + dx, 0), W - w)
        y0 = min(max(cy * H - h / 2 + dy, 0), H - h)
        img = img.transform((W, H), Image.AFFINE, (w / W, 0, x0, 0, h / H, y0), resample=Image.BICUBIC)
    if rgb:
        r, g, b = img.split()
        img = Image.merge('RGB', (ImageChops.offset(r, rgb, 0), g, ImageChops.offset(b, -rgb, 0)))
    if flash > 0.003:
        img = Image.blend(img, WHITE, min(1.0, flash))
    return img


def render(job, fx):
    """Scrive work/fx.mp4 dal montato. Ritorna il nome del file da usare come base."""
    src, out = job.w('cut.mp4'), job.w('fx.mp4')
    key = hashlib.sha1((json.dumps(fx, sort_keys=True) + str(src.stat().st_mtime)).encode()).hexdigest()
    kf = job.w('fx.key')
    if out.exists() and kf.exists() and kf.read_text() == key:
        print('  effetti: invariati, riuso fx.mp4')
        return 'fx.mp4'
    moves = fx.get('moves', [])
    vf = (GRADE + ',' if fx.get('grade', True) else '') + 'format=rgb24'
    rd = subprocess.Popen([tool('ffmpeg'), '-v', 'error', '-i', str(src), '-vf', vf, '-f', 'rawvideo',
                           '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    tmp = job.w('fx_video.mp4')
    wr = subprocess.Popen([tool('ffmpeg'), '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                           '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', *VENC, str(tmp)], stdin=subprocess.PIPE)
    size, n = W * H * 3, 0
    while True:
        buf = rd.stdout.read(size)
        if len(buf) < size:
            break
        img = Image.frombytes('RGB', (W, H), buf)
        st = state(moves, n / FPS)
        wr.stdin.write(apply(img, st).tobytes() if st != (1.0, 0.5, 0.5, 0.0, 0.0, 0.0, 0) else buf)
        n += 1
    wr.stdin.close()
    if wr.wait() or rd.wait():
        die('render degli effetti fallito')
    ff(['-i', tmp, '-i', src, '-map', '0:v', '-map', '1:a', '-c', 'copy', '-shortest', out])
    tmp.unlink()
    kf.write_text(key)
    print(f'  effetti: {len(moves)} movimenti su {n} fotogrammi -> fx.mp4')
    return 'fx.mp4'
