"""Agente video — comando unico per tutti i passi.

    py ve.py new JOB file_o_cartella... [--format tiktok|explainer]
    py ve.py transcribe JOB
    py ve.py cut JOB [--drop 3,5] [--keep 2]
    py ve.py gfx JOB
    py ve.py tempi JOB        (ogni testo resta a schermo il tempo di leggerlo?)
    py ve.py music JOB [--track nome.mp3 | --list]
    py ve.py export JOB
    py ve.py check JOB [--src composite|final|source|cut]
    py ve.py all JOB          (gfx -> music se c'e' un brano -> export -> check)
    py ve.py doctor           (controlla che sia tutto installato)

I passi sono spiegati in .claude/skills/video-editor/SKILL.md e in README.md.
"""
import argparse, shutil, subprocess, sys

for s in (sys.stdout, sys.stderr):  # la console di Windows non e' UTF-8 di default
    try:
        s.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

from vedit import common
from vedit.common import FORMATS, FONTS, MUSIC, PROJECTS


def cmd_doctor(a):
    ok = True
    def line(good, msg, fix=''):
        nonlocal ok
        ok &= good
        print(('  OK   ' if good else '  NO   ') + msg + ('' if good else f'\n         -> {fix}'))
    ffm = shutil.which('ffmpeg')
    line(bool(ffm), 'ffmpeg', 'winget install -e --id Gyan.FFmpeg  (poi riapri il terminale)')
    if ffm:
        filters = subprocess.run([ffm, '-hide_banner', '-filters'], capture_output=True, text=True).stdout
        for f in ('ass', 'sidechaincompress', 'loudnorm', 'afftdn'):
            line(f' {f} ' in filters, f'filtro ffmpeg "{f}"', 'serve una build completa di FFmpeg (Gyan.FFmpeg)')
    for mod, pkg in (('PIL', 'Pillow'), ('numpy', 'numpy'), ('faster_whisper', 'faster-whisper')):
        try:
            __import__(mod)
            line(True, pkg)
        except ImportError:
            line(False, pkg, 'py -m pip install -r requirements.txt')
    b = common.load(common.PRESETS / 'brands' / 'gmvegasi.json', {})
    for k, f in b.get('fonts', {}).items():
        line((FONTS / f).exists(), f'font {k}: {f}', 'lancia setup.ps1 (scarica i font)')
    logo = b.get('logo')
    line(bool(logo) and (common.ROOT / logo).exists(), f'logo: {logo}', 'copia il PNG del logo in assets/ (vedi assets/LEGGIMI.md)')
    n = len([p for p in MUSIC.glob('**/*') if p.suffix.lower() in {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg'}])
    print(f'  --   brani in music/: {n}')
    print('Tutto pronto.' if ok else 'Sistema le voci NO e rilancia py ve.py doctor.')


def cmd_colors(a):
    """Colori dominanti di un'immagine (es. il logo): per confermare gli esadecimali del marchio."""
    from PIL import Image
    im = Image.open(a.image).convert('RGBA')
    im.thumbnail((300, 300))
    px = [p[:3] for p in im.getdata() if p[3] > 200]
    q = Image.new('RGB', (len(px), 1))
    q.putdata(px)
    pal = q.quantize(colors=6)
    counts = sorted(pal.getcolors(), reverse=True)
    rgb = pal.getpalette()
    for n, i in counts:
        r, g, b = rgb[3 * i:3 * i + 3]
        print(f'  #{r:02X}{g:02X}{b:02X}  {100 * n / len(px):5.1f}%')


def cmd_all(a):
    from vedit import graphics, finish, check
    graphics.cmd_gfx(argparse.Namespace(job=a.job, no_captions=a.no_captions))
    if a.track or (not a.no_music and finish.list_tracks()):
        finish.cmd_music(argparse.Namespace(job=a.job, track=a.track, level=None, list=False))
    finish.cmd_export(argparse.Namespace(job=a.job))
    check.cmd_check(argparse.Namespace(job=a.job, src='composite', every=None))


def cmd_list(a):
    if not PROJECTS.exists():
        print('Nessun progetto.')
        return
    for p in sorted(PROJECTS.iterdir()):
        m = common.load(p / 'job.json', {})
        print(f"  {p.name:30s} {m.get('format', '?'):10s} {m.get('kind', '?'):8s} {m.get('duration', 0):6.1f}s")


def main():
    ap = argparse.ArgumentParser(prog='ve.py', description='Agente video GM Vegasi')
    sp = ap.add_subparsers(dest='cmd', required=True)

    p = sp.add_parser('new', help='passo 1: importa il grezzo')
    p.add_argument('job')
    p.add_argument('files', nargs='*')
    p.add_argument('--format', default='tiktok', choices=list(FORMATS))
    p.add_argument('--brand', default='gmvegasi')
    p.add_argument('--fit', default='auto', choices=['auto', 'cover', 'blur'],
                   help='cover = riempie 9:16 tagliando; blur = intero su fondo sfocato; auto = sceglie da solo')
    p.add_argument('--crop-x', type=float, default=0.5, help='con cover su video orizzontale: 0 = sinistra, 1 = destra')
    p.add_argument('--each', type=float, help='tieni solo N secondi centrali di ogni clip')
    p.add_argument('--edl', help='json con [{file, in, out}] per scegliere i pezzi a mano')
    p.add_argument('--photo-dur', type=float, default=2.5)
    p.add_argument('--force', action='store_true')

    p = sp.add_parser('transcribe', help='passo 2a: trascrizione parola per parola')
    p.add_argument('job')
    p.add_argument('--model', default='small', help='small (veloce) | medium (piu\' preciso) | large-v3')
    p.add_argument('--device', default='cpu', help='cpu | cuda (scheda NVIDIA)')

    p = sp.add_parser('cut', help='passo 2b: rough cut')
    p.add_argument('job')
    p.add_argument('--drop', help='frasi da togliere, es. 3,5')
    p.add_argument('--keep', help='frasi da tenere anche se sembrano ripetute')
    p.add_argument('--no-auto', action='store_true', help='non togliere i ripetuti da solo')
    p.add_argument('--gap', type=float, default=0.35, help='pause piu\' lunghe di cosi\' vengono tagliate')
    p.add_argument('--pad-in', type=float, default=0.08)
    p.add_argument('--pad-out', type=float, default=0.14)
    p.add_argument('--none', action='store_true', help='nessun taglio sul parlato (video senza voce)')

    p = sp.add_parser('gfx', help='passi 3+5: grafiche dal piano e sottotitoli')
    p.add_argument('job')
    p.add_argument('--no-captions', action='store_true')

    p = sp.add_parser('tempi', help='controlla che ogni testo resti a schermo il tempo di leggerlo')
    p.add_argument('job')

    p = sp.add_parser('music', help='passo 6: musica sotto la voce')
    p.add_argument('job')
    p.add_argument('--track')
    p.add_argument('--level', type=float, help='LUFS del fondo musicale (default -24 con voce, -16 senza)')
    p.add_argument('--list', action='store_true')

    p = sp.add_parser('export', help='passo 7: outputs/JOB.final.mp4 (+ .nomusic.mp4)')
    p.add_argument('job')

    p = sp.add_parser('prune', help='pulisce i file intermedi')
    p.add_argument('job')
    p.add_argument('--all', action='store_true')

    p = sp.add_parser('check', help='foglio di provini da controllare')
    p.add_argument('job')
    p.add_argument('--src', default='composite')
    p.add_argument('--every', type=float)

    p = sp.add_parser('all', help='gfx -> music -> export -> check')
    p.add_argument('job')
    p.add_argument('--track')
    p.add_argument('--no-music', action='store_true')
    p.add_argument('--no-captions', action='store_true')

    sp.add_parser('doctor', help='controlla l\'installazione')
    sp.add_parser('list', help='elenca i progetti')
    p = sp.add_parser('colors', help='colori dominanti di un\'immagine')
    p.add_argument('image')

    a = ap.parse_args()
    if a.cmd == 'new':
        from vedit.intake import cmd_new as f
    elif a.cmd == 'transcribe':
        from vedit.transcribe import cmd_transcribe as f
    elif a.cmd == 'cut':
        from vedit.roughcut import cmd_cut as f
    elif a.cmd == 'gfx':
        from vedit.graphics import cmd_gfx as f
    elif a.cmd == 'tempi':
        from vedit.graphics import cmd_tempi as f
    elif a.cmd == 'music':
        from vedit.finish import cmd_music as f
    elif a.cmd == 'export':
        from vedit.finish import cmd_export as f
    elif a.cmd == 'prune':
        from vedit.finish import cmd_prune as f
    elif a.cmd == 'check':
        from vedit.check import cmd_check as f
    else:
        f = dict(doctor=cmd_doctor, all=cmd_all, list=cmd_list, colors=cmd_colors)[a.cmd]
    f(a)


if __name__ == '__main__':
    main()
