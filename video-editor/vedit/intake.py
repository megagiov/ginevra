"""Passo 1 — Intake: copia il grezzo nel progetto e lo porta tutto a 1080x1920, 30 fps, 48 kHz.

Accetta video e foto, anche mescolati. Ogni pezzo viene normalizzato e poi unito in
work/source.mp4: da li' in avanti la pipeline vede sempre un solo file.
"""
import shutil
from pathlib import Path
from .common import Job, ff, die, duration, has_audio, video_size, save, load, W, H, FPS, SR, VENC, FORMATS

VIDEO = {'.mp4', '.mov', '.m4v', '.avi', '.mkv', '.webm', '.3gp'}
PHOTO = {'.jpg', '.jpeg', '.png', '.webp', '.heic'}


def _expand(paths):
    out = []
    for p in map(Path, paths):
        if p.is_dir():
            out += sorted(f for f in p.iterdir() if f.suffix.lower() in VIDEO | PHOTO)
        elif p.exists():
            out.append(p)
        else:
            die(f'file non trovato: {p}')
    if not out:
        die('nessun video o foto da importare')
    return out


def _vf(fit, crop_x, src_w, src_h):
    """cover = riempie tagliando i bordi; blur = mostra tutto su fondo sfocato."""
    if fit == 'auto':
        fit = 'cover' if src_w / src_h < 0.7 else 'blur'
    tail = f'setsar=1,fps={FPS},format=yuv420p'
    if fit == 'cover':
        return (f'scale={W}:{H}:force_original_aspect_ratio=increase,'
                f'crop={W}:{H}:x=(iw-{W})*{crop_x}:y=(ih-{H})/2,{tail}')
    return (f'split=2[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},'
            f'boxblur=40:2,eq=brightness=-0.08[bg];[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];'
            f'[bg][fg]overlay=(W-w)/2:(H-h)/2,{tail}')


def _photo_vf(d):
    # composizione a doppia risoluzione e poi zoompan: cosi' lo zoom lento non scatta
    n = max(1, int(d * FPS))
    return (f'split=2[a][b];[a]scale={2*W}:{2*H}:force_original_aspect_ratio=increase,crop={2*W}:{2*H},'
            f'boxblur=60:2,eq=brightness=-0.10[bg];[b]scale={int(2*W*0.92)}:{int(2*H*0.80)}:'
            f'force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,'
            f"zoompan=z='1+0.06*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},"
            f'setsar=1,format=yuv420p')


def _normalize(item, out, fit, crop_x, photo_dur):
    src = Path(item['file'])
    aud = ['-af', f'aresample={SR},aformat=channel_layouts=stereo']
    if src.suffix.lower() in PHOTO:
        d = item.get('dur', photo_dur)
        ff(['-loop', 1, '-framerate', FPS, '-t', d, '-i', src,
            '-f', 'lavfi', '-t', d, '-i', f'anullsrc=r={SR}:cl=stereo',
            '-filter_complex', f'[0:v]{_photo_vf(d)}[v]', '-map', '[v]', '-map', '1:a',
            *VENC, '-c:a', 'pcm_s16le', '-t', d, out])
        return d
    sw, sh = video_size(src)
    cut = []
    if 'in' in item:
        cut += ['-ss', item['in']]
    if 'out' in item:
        cut += ['-t', item['out'] - item.get('in', 0)]
    vf = _vf(item.get('fit', fit), item.get('crop_x', crop_x), sw, sh)
    if has_audio(src):
        ff([*cut, '-i', src, '-filter_complex', f'[0:v]{vf}[v]', '-map', '[v]', '-map', '0:a:0',
            *aud, *VENC, '-c:a', 'pcm_s16le', out])
    else:
        ff([*cut, '-i', src, '-f', 'lavfi', '-i', f'anullsrc=r={SR}:cl=stereo',
            '-filter_complex', f'[0:v]{vf}[v]', '-map', '[v]', '-map', '1:a',
            *VENC, '-c:a', 'pcm_s16le', '-shortest', out])
    return duration(out)


def cmd_new(a):
    if a.format not in FORMATS:
        die(f'formato sconosciuto: {a.format}. Disponibili: {", ".join(FORMATS)}')
    job = Job(a.job, must_exist=False)
    if job.dir.exists():
        if not a.force:
            die(f'il progetto {a.job} esiste gia\'. Usa --force per ricrearlo.')
        shutil.rmtree(job.dir)
    job.raw.mkdir(parents=True)
    (job.work / 'parts').mkdir(parents=True)

    # elenco dei pezzi: da --edl (scelta dei punti di entrata/uscita) o tutti i file interi
    if a.edl:
        edl = load(a.edl)
        items = [dict(e, file=str(Path(a.edl).parent / e['file'])) for e in edl]
    else:
        items = [{'file': str(f)} for f in _expand(a.files)]
        if a.each:
            for it in items:
                if Path(it['file']).suffix.lower() in VIDEO:
                    d = duration(it['file'])
                    if d > a.each:
                        it['in'] = round((d - a.each) / 2, 2)
                        it['out'] = round(it['in'] + a.each, 2)

    log, total = [], 0.0
    for i, it in enumerate(items, 1):
        src = Path(it['file'])
        dst = job.raw / f'{i:02d}_{src.name}'
        shutil.copy2(src, dst)
        part = job.work / 'parts' / f'{i:02d}.mkv'
        d = _normalize(dict(it, file=str(dst)), part, a.fit, a.crop_x, a.photo_dur)
        log.append(dict(it, file=dst.name, part=part.name, start=round(total, 3), dur=round(d, 3)))
        total += d
        print(f'  {i:02d}  {src.name:40s} {d:6.2f}s')

    lst = job.work / 'parts.txt'
    lst.write_text(''.join(f"file 'parts/{p['part']}'\n" for p in log), encoding='utf-8')
    ff(['-f', 'concat', '-safe', 0, '-i', 'parts.txt', '-c:v', 'copy', '-c:a', 'pcm_s16le',
        'source.mkv'], cwd=job.work)
    save(job.dir / 'job.json', dict(name=a.job, format=a.format, brand=a.brand, parts=log,
                                    kind='unknown', duration=round(total, 3)))
    if not (job.dir / 'plan.json').exists():
        save(job.dir / 'plan.json', {'logo': False, 'beats': []})
    print(f'Progetto {a.job}: {len(log)} pezzi, {total:.1f}s, formato {a.format}.')
    print(f'Prossimo passo: py ve.py transcribe {a.job}   (o "cut" se non c\'e\' parlato)')
