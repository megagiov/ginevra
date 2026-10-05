"""Controllo visivo: foglio di provini con i fotogrammi chiave, da guardare prima di consegnare.

Prende un fotogramma a meta' di ogni grafica piu' uno ogni N secondi. L'agente apre
work/check.png e controlla testi tagliati, sovrapposizioni col volto, errori di battitura.
"""
import subprocess
from PIL import Image, ImageDraw, ImageFont
from .common import Job, die, duration, load, tool, fmt_t, OUTPUTS
from .graphics import resolve_times

TW, TH = 270, 480


def frame(path, t):
    raw = subprocess.run([tool('ffmpeg'), '-v', 'error', '-ss', f'{t:.3f}', '-i', str(path), '-frames:v', '1',
                          '-vf', f'scale={TW}:{TH}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True).stdout
    if len(raw) < TW * TH * 3:
        return Image.new('RGB', (TW, TH), (40, 0, 0))
    return Image.frombytes('RGB', (TW, TH), raw[:TW * TH * 3])


def cmd_check(a):
    job = Job(a.job)
    pick = {'source': job.w('source.mkv'), 'cut': job.w('cut.mp4'), 'composite': job.w('composite.mp4'),
            'final': OUTPUTS / f'{job.name}.final.mp4'}
    if a.src not in pick:
        die(f'--src deve essere uno tra: {", ".join(pick)}')
    path = pick[a.src]
    if not path.exists():
        die(f'file non trovato: {path}')
    d = duration(path)
    times = set()
    if a.src in ('composite', 'final'):
        for b in load(job.dir / 'plan.json', {}).get('beats', []):
            s, e = resolve_times(b, d)
            if e > s:
                times.add(round(s + min(0.6, (e - s) / 2), 2))
    step = a.every or max(1.0, d / 12)
    t = 0.3
    while t < d:
        times.add(round(t, 2))
        t += step
    times = sorted(times)[:60]
    cols = 6
    rows = (len(times) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * TW, rows * (TH + 34)), (18, 18, 20))
    dr = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype('arial.ttf', 22)
    except OSError:
        f = ImageFont.load_default()
    for i, t in enumerate(times):
        x, y = i % cols * TW, i // cols * (TH + 34)
        sheet.paste(frame(path, t), (x, y + 34))
        dr.text((x + 8, y + 6), fmt_t(t), fill=(230, 230, 230), font=f)
    out = job.w(f'check_{a.src}.png')
    sheet.save(out)
    print(f'Provini ({len(times)} fotogrammi di {path.name}): {out}')
