"""Passo 2b — Rough cut: toglie esitazioni, pause lunghe e frasi ripetute, poi pulisce l'audio.

Il taglio e' quantizzato al fotogramma: il video si seleziona per numero di fotogramma
e l'audio per blocchi di 1600 campioni (48000/30), cosi' labiale e voce non si
scollano mai, nemmeno dopo cento tagli.
"""
import difflib, re, subprocess
import numpy as np
from .common import Job, ff, die, duration, load, save, tool, FPS, SR, SPF, VENC, AENC

FILLERS = {'ehm', 'eh', 'ehmm', 'emh', 'uhm', 'um', 'uh', 'mmm', 'mm', 'hmm', 'ah', 'eeh', 'ehh'}
# catena voce: via il rombo, rumore di fondo leggero, compressione morbida, -14 LUFS (TikTok/IG)
VOICE_CHAIN = ('highpass=f=80,afftdn=nf=-25,'
               'acompressor=threshold=-18dB:ratio=3:attack=5:release=120:makeup=2,'
               f'loudnorm=I=-14:TP=-1.5:LRA=9,aresample={SR}')


def norm(t):
    return re.sub(r'[^\wàèéìòù]', '', t.lower())


def suggest_retakes(sents):
    """Una frase seguita da una quasi-copia e' un ripetuto: si tiene l'ultima versione."""
    out = []
    for a, b in zip(sents, sents[1:]):
        ta, tb = [norm(x) for x in a['text'].split()], [norm(x) for x in b['text'].split()]
        if len(ta) < 2:
            continue
        head = tb[:len(ta)]
        if difflib.SequenceMatcher(None, ta, head).ratio() >= 0.6 or ta[:3] == tb[:3]:
            out.append(a['i'])
    return out


def _parse(s):
    return {int(x) for x in s.split(',') if x.strip()} if s else set()


def plan_spans(words, sents, drop, gap, pad_in, pad_out, total):
    sent_of = {}
    for s in sents:
        for k in range(s['w0'], s['w1'] + 1):
            sent_of[k] = s['i']
    keep = [i for i, w in enumerate(words) if sent_of.get(i) not in drop and norm(w['w']) not in FILLERS]
    groups = []
    for i in keep:
        if groups and i == groups[-1][-1] + 1 and words[i]['s'] - words[i - 1]['e'] <= gap:
            groups[-1].append(i)
        else:
            groups.append([i])
    spans = []
    for g in groups:
        a, b = g[0], g[-1]
        s = words[a]['s'] - pad_in
        e = words[b]['e'] + pad_out
        if a > 0:  # mai rientrare dentro la parola scartata prima
            s = max(s, words[a - 1]['e'] + 0.02)
        if b + 1 < len(words):
            e = min(e, words[b + 1]['s'] - 0.02)
        s, e = max(0.0, s), min(total, e)
        fs, fe = round(s * FPS), round(e * FPS)
        if fe - fs < 4:
            continue
        if spans and fs <= spans[-1][1] + 1:
            spans[-1][1] = max(spans[-1][1], fe)
        else:
            spans.append([fs, fe])
    return spans, keep


def _read_audio(path):
    raw = subprocess.run([tool('ffmpeg'), '-v', 'error', '-i', str(path), '-f', 'f32le', '-ac', '2',
                          '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2)


def _write_wav(path, x):
    p = subprocess.run([tool('ffmpeg'), '-v', 'error', '-y', '-f', 'f32le', '-ac', '2', '-ar', str(SR),
                        '-i', '-', '-c:a', 'pcm_s16le', str(path)], input=x.astype(np.float32).tobytes())
    if p.returncode:
        die('scrittura audio fallita')


def render(job, spans):
    src = job.w('source.mkv')
    audio = _read_audio(src)
    fade = int(0.008 * SR)  # 8 ms di dissolvenza a ogni taglio: niente click
    ramp = np.linspace(0, 1, fade, dtype=np.float32)[:, None]
    chunks = []
    for fs, fe in spans:
        c = audio[fs * SPF:fe * SPF].copy()
        if len(c) > 2 * fade:
            c[:fade] *= ramp
            c[-fade:] *= ramp[::-1]
        chunks.append(c)
    _write_wav(job.w('cut_audio.wav'), np.concatenate(chunks) if chunks else audio[:SPF])
    sel = '+'.join(f'between(n,{fs},{fe - 1})' for fs, fe in spans)
    job.w('cut_select.txt').write_text(sel, encoding='utf-8')
    ff(['-i', src, '-i', job.w('cut_audio.wav'), '-filter_complex',
        f"[0:v]select='{sel}',setpts=N/FRAME_RATE/TB[v];[1:a]{VOICE_CHAIN}[a]",
        '-map', '[v]', '-map', '[a]', *VENC, *AENC, job.w('cut.mp4')])


def remap(words, keep, spans):
    """Riporta i tempi delle parole tenute sulla timeline del montato."""
    out, off, k = [], [], 0
    for fs, fe in spans:
        off.append(k)
        k += fe - fs
    for i in keep:
        w = words[i]
        for (fs, fe), o in zip(spans, off):
            if fs / FPS - 0.05 <= w['s'] < fe / FPS:
                ns = (o + (w['s'] * FPS - fs)) / FPS
                ne = min((o + (w['e'] * FPS - fs)) / FPS, (o + fe - fs) / FPS)
                out.append(dict(w=w['w'], s=round(max(ns, o / FPS), 3), e=round(ne, 3)))
                break
    return out


def cmd_cut(a):
    job = Job(a.job)
    src = job.w('source.mkv')
    total = duration(src)
    tr = load(job.w('words.json'))
    if a.none or not tr or job.meta.get('kind') == 'silent':
        # niente parlato (giro auto, foto): il montato e' il sorgente, solo audio normalizzato
        ff(['-i', src, '-af', f'loudnorm=I=-20:TP=-2,aresample={SR}', *VENC, *AENC, job.w('cut.mp4')])
        save(job.w('words_cut.json'), [])
        if job.meta.get('kind') == 'unknown':
            job.update(kind='silent')
        print(f'Nessun taglio sul parlato. Montato: {job.w("cut.mp4")} ({total:.1f}s)')
        return
    words, sents = tr['words'], tr['sentences']
    auto = [] if a.no_auto else suggest_retakes(sents)
    drop = (set(auto) | _parse(a.drop)) - _parse(a.keep)
    spans, keep = plan_spans(words, sents, drop, a.gap, a.pad_in, a.pad_out, total)
    if not spans:
        die('dopo i tagli non resta nulla: controlla --drop')
    render(job, spans)
    wc = remap(words, keep, spans)
    save(job.w('words_cut.json'), wc)
    save(job.w('cut.json'), dict(drop=sorted(drop), auto=auto, gap=a.gap,
                                 spans=[[fs / FPS, fe / FPS] for fs, fe in spans]))
    new = sum(fe - fs for fs, fe in spans) / FPS
    fill = sum(1 for w in words if norm(w['w']) in FILLERS)
    if auto:
        print(f'Ripetuti trovati e tolti (frasi): {auto}  -> se sbagliato: --keep {",".join(map(str, auto))}')
    print(f'Tolte {len(drop)} frasi, {fill} esitazioni, {len(spans)} pezzi tenuti.')
    print(f'Durata: {total:.1f}s -> {new:.1f}s. Montato: {job.w("cut.mp4")}')
