"""Percorsi, ffmpeg, job e marchi: tutto quello che i passi condividono."""
import json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / 'projects'
OUTPUTS = ROOT / 'outputs'
PRESETS = ROOT / 'presets'
FONTS = ROOT / 'fonts'
MUSIC = ROOT / 'music'
ASSETS = ROOT / 'assets'

W, H, FPS, SR = 1080, 1920, 30, 48000
SPF = SR // FPS  # campioni audio per fotogramma: tiene il taglio a/v allineato

VENC = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
        '-pix_fmt', 'yuv420p', '-r', str(FPS)]
AENC = ['-c:a', 'aac', '-b:a', '192k', '-ar', str(SR), '-ac', '2']

# Formati: cambiano solo grafiche e sottotitoli, il resto della pipeline e' identico
FORMATS = {
    'tiktok':    dict(label='TikTok/Reels raw 9:16', cap_align=2, cap_margin=500, cap_size=94),
    'explainer': dict(label='Explainer 9:16',        cap_align=2, cap_margin=760, cap_size=82),
}


def die(msg):
    print('ERRORE: ' + msg, file=sys.stderr)
    sys.exit(1)


def tool(name):
    p = shutil.which(name)
    if not p:
        die(f'{name} non trovato. Installa FFmpeg (vedi README, setup.ps1) e riapri il terminale.')
    return p


def ff(args, cwd=None):
    cmd = [tool('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-nostats', '-y', *map(str, args)]
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode:
        die('ffmpeg fallito:\n  ' + ' '.join(cmd)[:2000])


def probe(path):
    out = subprocess.run([tool('ffprobe'), '-v', 'error', '-show_streams', '-show_format',
                          '-of', 'json', str(path)], capture_output=True, text=True)
    if out.returncode:
        die(f'ffprobe non legge {path}')
    return json.loads(out.stdout)


def duration(path):
    return float(probe(path)['format']['duration'])


def has_audio(path):
    return any(s['codec_type'] == 'audio' for s in probe(path)['streams'])


def video_size(path):
    """Larghezza e altezza come appaiono, cioe' gia' ruotate (i telefoni salvano la rotazione a parte)."""
    v = next(s for s in probe(path)['streams'] if s['codec_type'] == 'video')
    w, h = int(v['width']), int(v['height'])
    rot = int(v.get('tags', {}).get('rotate', 0) or 0)
    for sd in v.get('side_data_list', []):
        if 'rotation' in sd:
            rot = int(sd['rotation'])
    return (h, w) if abs(rot) % 180 == 90 else (w, h)


def load(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding='utf-8'))


def save(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def fmt_t(t):
    return f'{int(t // 60)}:{t % 60:05.2f}'


class Job:
    def __init__(self, name, must_exist=True):
        self.name = name
        self.dir = PROJECTS / name
        self.raw = self.dir / 'raw'
        self.work = self.dir / 'work'
        if must_exist and not (self.dir / 'job.json').exists():
            die(f'progetto "{name}" non trovato in {PROJECTS}. Crealo con: py ve.py new {name} <file...>')

    @property
    def meta(self):
        return load(self.dir / 'job.json', {})

    def update(self, **kw):
        m = self.meta
        m.update(kw)
        save(self.dir / 'job.json', m)

    @property
    def fmt(self):
        return FORMATS[self.meta.get('format', 'tiktok')]

    def brand(self):
        return load_brand(self.meta.get('brand', 'gmvegasi'))

    def w(self, name):
        return self.work / name


def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


_FALLBACK = ['C:/Windows/Fonts/arialbd.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
             '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']


def font_path(name):
    p = FONTS / name
    if p.exists():
        return str(p)
    for f in _FALLBACK:
        if Path(f).exists():
            print(f'ATTENZIONE: font {name} mancante in fonts/, uso {f}. Lancia setup.ps1.')
            return f
    die(f'font {name} mancante in {FONTS}')


def load_brand(slug):
    b = load(PRESETS / 'brands' / f'{slug}.json')
    if not b:
        die(f'marchio "{slug}" non trovato in presets/brands/')
    b['slug'] = slug
    b['rgb'] = {k: hex_rgb(v) for k, v in b['colors'].items()}
    b['font_files'] = {k: font_path(v) for k, v in b['fonts'].items()}
    logo = b.get('logo')
    b['logo_path'] = str(ROOT / logo) if logo and (ROOT / logo).exists() else None
    return b
