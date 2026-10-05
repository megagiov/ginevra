"""Passo 2a — Trascrizione con tempi parola per parola (faster-whisper, in locale, gratis).

Scrive work/words.json (parole + frasi) e work/script.md, il copione numerato che
l'agente legge per decidere cosa tagliare.
"""
import re
from .common import Job, ff, die, save, load, PRESETS, fmt_t

# Un prompt iniziale con esitazioni scritte spinge Whisper a trascriverle invece di
# saltarle: senza, le "ehm" spariscono dal testo ma restano nell'audio e non si tagliano.
FILLER_PROMPT = 'Ehm, allora... uhm, cioè, ehm, praticamente.'


def corrections():
    return {k.lower(): v for k, v in load(PRESETS / 'caption-corrections.json', {}).get('parole', {}).items()}


def fix_word(w, corr):
    m = re.match(r'^(\W*)(.*?)(\W*)$', w)
    pre, core, post = m.groups()
    return pre + corr.get(core.lower(), core) + post


def cmd_transcribe(a):
    job = Job(a.job)
    src = job.w('source.mkv')
    wav = job.w('audio16.wav')
    ff(['-i', src, '-vn', '-ac', 1, '-ar', 16000, wav])
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        die('faster-whisper non installato: py -m pip install -r requirements.txt')

    brand = job.brand()
    prompt = ', '.join(brand.get('glossario', [])) + '. ' + FILLER_PROMPT
    print(f'Trascrivo con il modello "{a.model}" (la prima volta lo scarica, ~0,5-1,5 GB)...')
    model = WhisperModel(a.model, device=a.device, compute_type='int8' if a.device == 'cpu' else 'default')
    segs, info = model.transcribe(str(wav), language='it', word_timestamps=True, vad_filter=True,
                                  initial_prompt=prompt, condition_on_previous_text=False)
    corr = corrections()
    words, sentences = [], []
    for seg in segs:
        cur = []
        for w in seg.words or []:
            t = fix_word(w.word.strip(), corr)
            if not t:
                continue
            words.append(dict(w=t, s=round(w.start, 3), e=round(w.end, 3), p=round(w.probability, 2)))
            cur.append(len(words) - 1)
            if t[-1] in '.?!':  # una frase per riga: piu' facile scegliere i ripetuti
                sentences.append(cur)
                cur = []
        if cur:
            sentences.append(cur)
    sents = [dict(i=i + 1, w0=c[0], w1=c[-1], s=words[c[0]]['s'], e=words[c[-1]]['e'],
                  text=' '.join(words[k]['w'] for k in c)) for i, c in enumerate(sentences)]
    save(job.w('words.json'), dict(words=words, sentences=sents))

    speech = sum(w['e'] - w['s'] for w in words)
    kind = 'voice' if speech > 1.5 else 'silent'
    job.update(kind=kind)
    lines = [f'# Copione — {job.name}', '',
             'Frasi numerate. Per tagliare una ripetizione o un errore: py ve.py cut JOB --drop 3,7', '']
    for s in sents:
        low = [words[k]['w'] for k in range(s['w0'], s['w1'] + 1) if words[k]['p'] < 0.5]
        flag = f"   ⚠ incerte: {', '.join(low)}" if low else ''
        lines.append(f"{s['i']:>3}. [{fmt_t(s['s'])}–{fmt_t(s['e'])}] {s['text']}{flag}")
    job.w('script.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'{len(words)} parole, {len(sents)} frasi, parlato {speech:.1f}s -> tipo "{kind}".')
    print(f'Copione: {job.w("script.md")}')
