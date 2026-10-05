"""Passi 6 e 7 — Musica (facoltativa, si abbassa sotto la voce) ed export.

L'export produce sempre due file: <job>.final.mp4 con la musica e
<job>.nomusic.mp4 senza, per aggiungere il brano dall'app al momento di pubblicare.
"""
import shutil
from pathlib import Path
from .common import Job, ff, die, duration, OUTPUTS, MUSIC, SR, AENC, fmt_t

TRACKS = {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg'}


def list_tracks():
    return sorted(p for p in MUSIC.glob('**/*') if p.suffix.lower() in TRACKS) if MUSIC.exists() else []


def cmd_music(a):
    job = Job(a.job)
    comp = job.w('composite.mp4')
    if not comp.exists():
        die('manca il composto: lancia prima py ve.py gfx ' + a.job)
    tracks = list_tracks()
    if a.list:
        for t in tracks:
            print(f'  {fmt_t(duration(t)):>8}  {t.relative_to(MUSIC)}')
        print(f'{len(tracks)} brani in {MUSIC}' if tracks else f'Nessun brano in {MUSIC}')
        return
    track = Path(a.track) if a.track else None
    if track and not track.exists():
        track = MUSIC / a.track
    if not track:
        if not tracks:
            die(f'nessun brano: metti file audio con licenza in {MUSIC} o usa --track')
        track = tracks[0]
    if not track.exists():
        die(f'brano non trovato: {a.track}')
    d = duration(comp)
    voice = job.meta.get('kind') == 'voice'
    bed = a.level if a.level is not None else (-24 if voice else -16)
    m = (f'[1:a]aresample={SR},aformat=channel_layouts=stereo,atrim=0:{d:.3f},asetpts=PTS-STARTPTS,'
         f'loudnorm=I={bed}:TP=-2,afade=t=in:d=0.4,afade=t=out:st={max(0, d - 1.5):.3f}:d=1.5[m]')
    if voice:
        # sidechain: la musica scende quando parla qualcuno e risale nelle pause
        mix = ('[0:a]asplit=2[v][k];[m][k]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350[md];'
               '[v][md]amix=inputs=2:duration=first:normalize=0')
    else:
        mix = '[0:a]volume=-12dB[v];[v][m]amix=inputs=2:duration=first:normalize=0'
    filt = f'{m};{mix},loudnorm=I=-14:TP=-1.5:LRA=11,aresample={SR}[a]'
    ff(['-i', comp, '-stream_loop', -1, '-i', track, '-filter_complex', filt,
        '-map', '0:v', '-map', '[a]', '-c:v', 'copy', *AENC, '-t', f'{d:.3f}', job.w('withmusic.mp4')])
    job.update(music=str(track.name))
    print(f'Musica: {track.name} (fondo {bed} LUFS, {"abbassata sotto la voce" if voice else "in primo piano"})')


def cmd_export(a):
    job = Job(a.job)
    comp, wm = job.w('composite.mp4'), job.w('withmusic.mp4')
    if not comp.exists():
        die('manca il composto: lancia prima py ve.py gfx ' + a.job)
    OUTPUTS.mkdir(exist_ok=True)
    outs = []
    if wm.exists() and wm.stat().st_mtime >= comp.stat().st_mtime:
        outs += [(wm, f'{job.name}.final.mp4'), (comp, f'{job.name}.nomusic.mp4')]
    else:
        if wm.exists():
            print('ATTENZIONE: la versione con musica e\' piu\' vecchia delle grafiche, rilancia "music".')
        outs += [(comp, f'{job.name}.final.mp4')]
    for src, name in outs:
        ff(['-i', src, '-map', 0, '-c', 'copy', '-movflags', '+faststart', OUTPUTS / name])
        p = OUTPUTS / name
        print(f'  {p}  {duration(p):.2f}s  {p.stat().st_size / 1e6:.1f} MB')


def cmd_prune(a):
    job = Job(a.job)
    keep = {'words.json', 'words_cut.json', 'cut.json', 'script.md', 'captions.ass', 'source.mkv', 'cut.mp4'}
    if a.all:
        keep -= {'source.mkv', 'cut.mp4'}
    freed = 0
    for p in job.work.iterdir():
        if p.name in keep:
            continue
        if p.is_dir():
            freed += sum(f.stat().st_size for f in p.rglob('*') if f.is_file())
            shutil.rmtree(p)
        else:
            freed += p.stat().st_size
            p.unlink()
    print(f'Liberati {freed / 1e6:.0f} MB in {job.work}')
