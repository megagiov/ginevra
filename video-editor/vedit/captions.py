"""Passo 5 — Sottotitoli a parola evidenziata (stile TikTok), file .ass impresso da libass.

2-3 parole per volta; la parola che si sta dicendo prende il colore accento.
Le correzioni di nomi e marchi stanno in presets/caption-corrections.json.
"""
import re
from PIL import ImageFont
from .common import load, PRESETS, W, H


def ass_color(rgb, alpha=0):
    r, g, b = rgb
    return f'&H{alpha:02X}{b:02X}{g:02X}{r:02X}'


def ts(t):
    t = max(0.0, t)
    cs = int(round(t * 100))
    return f'{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}'


def clean(w, corr):
    m = re.match(r'^(\W*)(.*?)(\W*)$', w)
    core = corr.get(m.group(2).lower(), m.group(2))
    end = m.group(3) if m.group(3) in ('?', '!') else ''
    return re.sub(r'[{}\\]', '', core + end).upper()


def chunks(words, max_words=3, max_chars=18, gap=0.45):
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        n_chars = sum(len(x['w']) + 1 for x in cur)
        if (nxt is None or len(cur) >= max_words or n_chars >= max_chars
                or w['w'][-1:] in '.,?!;:' or nxt['s'] - w['e'] > gap):
            out.append(cur)
            cur = []
    return out


def build(job):
    words = load(job.w('words_cut.json'), [])
    if not words:
        return False
    br, fmt = job.brand(), job.fmt
    corr = {k.lower(): v for k, v in load(PRESETS / 'caption-corrections.json', {}).get('parole', {}).items()}
    fname = ImageFont.truetype(br['font_files']['caption'], 10).getname()[0]
    c = br['rgb']
    white, accent, dark = ass_color(c['light']), ass_color(c['accent']), ass_color(c['dark'])
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{fname},{fmt['cap_size']},{white},{white},{dark},&H78000000,0,0,0,0,100,100,1,0,1,7,3,{fmt['cap_align']},110,110,{fmt['cap_margin']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    groups = chunks(words)
    for gi, g in enumerate(groups):
        end = g[-1]['e'] + 0.25
        if gi + 1 < len(groups):
            end = min(end, groups[gi + 1][0]['s'])
        texts = [clean(w['w'], corr) for w in g]
        for i, w in enumerate(g):
            s = g[0]['s'] if i == 0 else w['s']
            e = g[i + 1]['s'] if i + 1 < len(g) else end
            if e - s < 0.02:
                continue
            line = ' '.join(f'{{\\c{accent}}}{t}{{\\c{white}}}' if k == i else t for k, t in enumerate(texts))
            ev.append(f'Dialogue: 0,{ts(s)},{ts(e)},Cap,,0,0,0,,{line}')
    job.w('captions.ass').write_text(head + '\n'.join(ev) + '\n', encoding='utf-8')
    return True
