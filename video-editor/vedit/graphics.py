"""Passo 3 — Grafiche: dal piano (plan.json) a sovrimpressioni PNG, poi composizione.

Ogni "beat" del piano diventa una PNG trasparente 1080x1920 che entra con una
dissolvenza e una piccola salita. Nello stesso passaggio si imprimono i
sottotitoli (passo 5), cosi' il video si ricodifica una volta sola. Cambiare il
piano e rilanciare rifa' solo questo passo: il montato resta com'e'.
Lo schema dei beat e' in docs/PIANO.md.
"""
import re, shutil
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from .common import Job, ff, die, duration, load, W, H, SR, VENC, AENC, FONTS
from . import captions, fx

SAFE_X = 80          # margine laterale: a destra TikTok mette i pulsanti
TOP = 250            # sopra ci sono "Seguiti / Per te"
_F = {}


def font(path, size):
    k = (path, int(size))
    if k not in _F:
        _F[k] = ImageFont.truetype(path, int(size))
    return _F[k]


def size(d, s, f):
    # sempre textbbox, mai font.size: le maiuscole accentate (PIU') salgono oltre l'altezza nominale
    b = d.textbbox((0, 0), s, font=f, anchor='ls')
    return b[2] - b[0], b[3] - b[1], b


def runs(text):
    """'*3 ERRORI* da evitare' -> [('3 ERRORI', True), (' da evitare', False)]"""
    parts = re.split(r'(\*[^*]+\*)', text)
    return [(p[1:-1], True) if p.startswith('*') else (p, False) for p in parts if p]


def wrap(d, text, f, maxw):
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if cur and size(d, t.replace('*', ''), f)[0] > maxw:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    # un * aperto su una riga e chiuso sulla successiva va richiuso a fine riga
    fixed, open_ = [], False
    for ln in lines:
        if open_:
            ln = '*' + ln
        open_ = ln.count('*') % 2 == 1
        fixed.append(ln + '*' if open_ else ln)
    return fixed


def shadow(img, box, radius, blur=24, alpha=110, dy=12):
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((box[0], box[1] + dy, box[2], box[3] + dy), radius, fill=(0, 0, 0, alpha))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))


def rich_line(img, cx, y, text, f, col, hl_bg, hl_fg, outline=True):
    """Una riga centrata in cx, con le parti *evidenziate* su fascia del colore accento."""
    d = ImageDraw.Draw(img)
    rs = runs(text)
    widths = [size(d, t, f)[0] for t, _ in rs]
    x = cx - sum(widths) / 2
    asc = f.getmetrics()[0]
    for (t, hl), wdt in zip(rs, widths):
        if hl:
            _, _, b = size(d, t.strip(), f)
            pad = int(f.size * 0.16)
            lead = size(d, t[:len(t) - len(t.lstrip())], f)[0]
            tw = size(d, t.strip(), f)[0]
            d.rounded_rectangle((x + lead - pad, y + b[1] - pad, x + lead + tw + pad, y + b[3] + pad),
                                int(pad * 0.8), fill=hl_bg)
            d.text((x, y), t, font=f, fill=hl_fg, anchor='ls')
        else:
            kw = dict(stroke_width=max(2, f.size // 18), stroke_fill=(0, 0, 0, 200)) if outline else {}
            d.text((x, y), t, font=f, fill=col, anchor='ls', **kw)
        x += wdt
    return asc


def text_block(img, cx, y, text, f, maxw, col, hl_bg, hl_fg, gap=1.12, outline=True):
    d = ImageDraw.Draw(img)
    lines = wrap(d, text, f, maxw)
    lh = int(f.size * gap)
    for i, ln in enumerate(lines):
        rich_line(img, cx, y + f.size + i * lh, ln, f, col, hl_bg, hl_fg, outline)
    return y + f.size + (len(lines) - 1) * lh + int(f.size * 0.3)


# ---- tipi di beat ---------------------------------------------------------------------

def b_hook(img, b, br):
    c = br['rgb']
    head = br['font_files']['heading']
    if b.get('full'):
        ImageDraw.Draw(img).rectangle((0, 0, W, H), fill=c['primary'] + (255,))
        y = H * 0.36
    else:
        y = b.get('y', 0.15) * H
    f = font(head, b.get('size', 124))
    hb, hf = (c['light'], c['primary']) if b.get('full') else (c['primary'], c['light'])
    y = text_block(img, W / 2, y, b['text'].upper(), f, W - 2 * SAFE_X, c['light'], hb, hf, gap=1.08)
    if b.get('sub'):
        text_block(img, W / 2, y + 20, b['sub'], font(br['font_files']['body'], b.get('sub_size', 58)), W - 2 * SAFE_X,
                   c['light'], hb, hf)


def b_card(img, b, br):
    """Scheda nella meta' alta: numero, titolo, testo. Per gli explainer."""
    c = br['rgb']
    x0, x1, y0 = SAFE_X - 10, W - SAFE_X + 10, b.get('y', 0.13) * H
    d = ImageDraw.Draw(img)
    ft, fb = font(br['font_files']['heading'], b.get('size', 84)), font(br['font_files']['body'], 44)
    inner = x1 - x0 - 2 * 56
    tl = wrap(d, b.get('title', '').upper(), ft, inner - (130 if 'n' in b else 0))
    bl = wrap(d, b.get('text', ''), fb, inner) if b.get('text') else []
    h = 56 + len(tl) * int(ft.size * 1.05) + (24 + len(bl) * int(fb.size * 1.3) if bl else 0) + 50
    box = (x0, y0, x1, y0 + h)
    shadow(img, box, 40)
    d.rounded_rectangle(box, 40, fill=c['light'] + (250,))
    tx = x0 + 56
    if 'n' in b:
        d.ellipse((tx, y0 + 50, tx + 104, y0 + 154), fill=c['primary'])
        d.text((tx + 52, y0 + 102), str(b['n']), font=font(br['font_files']['heading'], 60), fill=c['light'], anchor='mm')
        tx += 130
    y = y0 + 56
    for ln in tl:
        y += ft.size
        d.text((tx, y), ln.replace('*', ''), font=ft, fill=c['dark'], anchor='ls')
        y += int(ft.size * 0.05)
    y += 24
    for ln in bl:
        y += int(fb.size * 1.3)
        d.text((x0 + 56, y), ln.replace('*', ''), font=fb, fill=c['muted'], anchor='ls')


def b_list(img, b, br):
    """Elenco a righe numerate con la riga attiva evidenziata (come la "pipeline" del riferimento)."""
    c = br['rgb']
    d = ImageDraw.Draw(img)
    y = b.get('y', 0.12) * H
    fe, fi = font(br['font_files']['body'], 38), font(br['font_files']['heading'], 58)
    if b.get('title'):
        t = b['title'].upper()
        tw, _, tb = size(d, t, fe)
        d.rounded_rectangle((SAFE_X - 10, y, SAFE_X + tw + 26, y + 58), 14, fill=c['dark'] + (230,))
        d.text((SAFE_X + 8, y + 29 - (tb[1] + tb[3]) / 2), t, font=fe, fill=c['accent'], anchor='ls')
        y += 76
    active = b.get('active', [])
    active = [active] if isinstance(active, int) else active
    for i, it in enumerate(b['items'], 1):
        on = i in active
        box = (SAFE_X - 10, y, W - SAFE_X + 10, y + 108)
        shadow(img, box, 24, blur=14, alpha=80, dy=6)
        d.rounded_rectangle(box, 24, fill=(c['primary'] if on else c['light']) + (250,))
        d.rounded_rectangle((box[0] + 22, y + 20, box[0] + 90, y + 88), 16, fill=c['light'] if on else c['primary'])
        d.text((box[0] + 56, y + 54), str(i), font=font(br['font_files']['heading'], 44),
               fill=c['primary'] if on else c['light'], anchor='mm')
        d.text((box[0] + 116, y + 54), it.upper(), font=fi, fill=c['light'] if on else c['dark'], anchor='lm')
        y += 126


STYLES = dict(primary=lambda c: (c['primary'], c['light']), accent=lambda c: (c['accent'], c['dark']),
              light=lambda c: (c['light'], c['dark']), dark=lambda c: (c['dark'], c['light']))


def b_label(img, b, br):
    """Fascia con testo e riga sotto (nome prodotto, prezzo, dettaglio)."""
    c = br['rgb']
    d = ImageDraw.Draw(img)
    y = b.get('y', 0.54) * H  # sopra la fascia dei sottotitoli (TikTok: ~0,70-0,73 H)
    f = font(br['font_files']['body'], b.get('size', 56))
    tw, th, bb = size(d, b['text'].upper(), f)
    px, py = 36, 22
    box = (W / 2 - tw / 2 - px, y, W / 2 + tw / 2 + px, y + th + 2 * py)
    shadow(img, box, 18, blur=14, alpha=90, dy=6)
    bg, fg = STYLES[b.get('style', 'primary')](c)
    d.rounded_rectangle(box, 18, fill=bg)
    d.text((W / 2, y + py - bb[1]), b['text'].upper(), font=f, fill=fg, anchor='ms')
    if b.get('sub'):
        d.text((W / 2, box[3] + 62), b['sub'], font=font(br['font_files']['body'], 44), fill=c['light'],
               anchor='ms', stroke_width=3, stroke_fill=(0, 0, 0, 200))


def b_cta(img, b, br):
    bb = dict(b, y=b.get('y', 0.54), size=b.get('size', 76), style=b.get('style', 'accent'))
    b_label(img, bb, br)


def b_text(img, b, br):
    c = br['rgb']
    f = font(br['font_files']['heading' if b.get('heading', True) else 'body'], b.get('size', 96))
    col = c[b.get('color', 'light')]
    text_block(img, W / 2, b.get('y', 0.2) * H, b['text'], f, W - 2 * SAFE_X, col, c['primary'], c['light'])


def b_badge(img, b, br):
    """Bollino a stella smerlata del marchio (NEW, -40%, PREZZO): testo grande + riga piccola."""
    import math
    c = br['rgb']
    r = b.get('r', 165)
    S = 2 * r + 40
    tile = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    cx = cy = S / 2
    pts = [(cx + (r * (1 + 0.075 * math.cos(8 * a))) * math.cos(a), cy + (r * (1 + 0.075 * math.cos(8 * a))) * math.sin(a))
           for a in (i * 2 * math.pi / 720 for i in range(720))]
    d = ImageDraw.Draw(tile)
    bg, fg = STYLES[b.get('style', 'primary')](c)
    d.polygon(pts, fill=bg)
    ft = font(br['font_files']['heading'], b.get('size', 104))
    tw = size(d, b['text'].upper(), ft)[0]
    if tw > 1.6 * r:
        ft = font(br['font_files']['heading'], int(ft.size * 1.6 * r / tw))
    y = cy + ft.size * 0.36 - (24 if b.get('sub') else 0)
    d.text((cx, y), b['text'].upper(), font=ft, fill=fg, anchor='ms')
    if b.get('sub'):
        d.text((cx, y + 62), b['sub'].upper(), font=font(br['font_files']['body'], 38), fill=fg, anchor='ms')
    tile = tile.rotate(b.get('angle', -8), resample=Image.BICUBIC)
    x, y = int(b.get('x', 0.76) * W - S / 2), int(b.get('y', 0.52) * H - S / 2)
    shadow(img, (x + 40, y + 40, x + S - 40, y + S - 40), S // 2, blur=20, alpha=90)
    img.alpha_composite(tile, (x, y))


def b_image(img, b, br, jobdir):
    """Immagine (foto prodotto, screenshot) in una scheda arrotondata nella meta' alta."""
    src = jobdir / b['src']
    if not src.exists():
        die(f'immagine del beat non trovata: {src}')
    pic = Image.open(src).convert('RGBA')
    maxw, maxh = W - 2 * SAFE_X, int(b.get('h', 0.38) * H)
    pic.thumbnail((maxw, maxh))
    x, y = (W - pic.width) // 2, int(b.get('y', 0.13) * H)
    box = (x, y, x + pic.width, y + pic.height)
    shadow(img, box, 36)
    m = Image.new('L', pic.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, *pic.size), 36, fill=255)
    pic.putalpha(m)
    img.alpha_composite(pic, (x, y))


KINDS = dict(hook=b_hook, card=b_card, list=b_list, label=b_label, cta=b_cta, text=b_text, badge=b_badge)


def logo_png(br, where):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    lg = Image.open(br['logo_path']).convert('RGBA')
    lg.thumbnail((240, 120))
    y = TOP - 10 if where == 'top' else H - 330
    img.alpha_composite(lg, (SAFE_X, y))
    return img


def resolve_times(b, total):
    s, e = b['start'], b['end']
    s = total + s if s < 0 else s
    e = total + e if e <= 0 else e
    return max(0.0, s), min(total, e)


def render_beats(job, total):
    br = job.brand()
    plan = load(job.dir / 'plan.json', {'beats': []})
    gdir = job.w('gfx')
    shutil.rmtree(gdir, ignore_errors=True)
    gdir.mkdir()
    out = []
    for i, b in enumerate(plan.get('beats', []), 1):
        t = b.get('type')
        if t != 'image' and t not in KINDS:
            die(f'beat {i}: tipo "{t}" sconosciuto. Tipi: {", ".join(list(KINDS) + ["image"])}')
        s, e = resolve_times(b, total)
        if e - s < 0.3:
            print(f'  beat {i} ({t}) saltato: dura meno di 0,3 s')
            continue
        img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        b_image(img, b, br, job.dir) if t == 'image' else KINDS[t](img, b, br)
        p = gdir / f'{i:02d}_{t}.png'
        img.save(p)
        out.append(dict(png=p.name, s=s, e=e, anim=not b.get('full')))
        print(f'  beat {i:02d} {t:6s} {s:6.2f}-{e:6.2f}s')
    if plan.get('logo') and br['logo_path']:
        p = gdir / 'logo.png'
        logo_png(br, plan['logo'] if isinstance(plan['logo'], str) else 'top').save(p)
        out.append(dict(png=p.name, s=0, e=total, anim=False))
    elif plan.get('logo'):
        print('  logo richiesto ma assente: metti il file indicato in presets/brands/<marchio>.json')
    return out


def cmd_gfx(a):
    job = Job(a.job)
    base = job.w('cut.mp4')
    if not base.exists():
        die('manca il montato: lancia prima py ve.py cut ' + a.job)
    total = duration(base)
    plan = load(job.dir / 'plan.json', {})
    src = fx.render(job, plan['fx']) if plan.get('fx') else 'cut.mp4'
    beats = render_beats(job, total)
    inputs, chain, last = ['-i', src], [], '0:v'
    for k, g in enumerate(beats, 1):
        inputs += ['-loop', 1, '-framerate', 30, '-t', f"{g['e']:.3f}", '-i', f"gfx/{g['png']}"]
        s, e = g['s'], g['e']
        if g['anim']:
            chain.append(f"[{k}:v]format=rgba,fade=t=in:st={s:.3f}:d=0.2:alpha=1,"
                         f"fade=t=out:st={max(s, e - 0.18):.3f}:d=0.18:alpha=1[g{k}]")
            y = f"'if(lt(t-{s:.3f},0.28),46*pow(1-(t-{s:.3f})/0.28,3),0)'"
        else:
            chain.append(f'[{k}:v]format=rgba[g{k}]')
            y = '0'
        chain.append(f"[{last}][g{k}]overlay=x=0:y={y}:enable='between(t,{s:.3f},{e:.3f})':eof_action=pass[o{k}]")
        last = f'o{k}'
    use_caps = not a.no_captions and captions.build(job)
    if use_caps:
        wf = job.w('fonts')
        shutil.rmtree(wf, ignore_errors=True)
        # i font vanno accanto al file .ass e si passano con percorso relativo:
        # un percorso Windows (C:\...) dentro un filtro ffmpeg rompe la sintassi dei ':'
        shutil.copytree(FONTS, wf) if FONTS.exists() else wf.mkdir()
        chain.append(f'[{last}]ass=captions.ass:fontsdir=fonts[vout]')
    else:
        chain.append(f'[{last}]null[vout]')
    job.w('compose_filter.txt').write_text(';\n'.join(chain), encoding='utf-8')
    if plan.get('mute'):
        # versione muta: traccia silenziosa invece dell'audio originale (TikTok vuole comunque un audio)
        inputs += ['-f', 'lavfi', '-t', f'{total:.3f}', '-i', f'anullsrc=r={SR}:cl=stereo']
        audio = [f'{len(beats) + 1}:a', *AENC]
    else:
        audio = ['0:a', '-c:a', 'copy']
    ff([*inputs, '-filter_complex', ';'.join(chain), '-map', '[vout]', '-map', audio[0],
        *VENC, *audio[1:], '-t', f'{total:.3f}', 'composite.mp4'], cwd=job.work)
    print(f'Composto: {job.w("composite.mp4")}  ({len(beats)} grafiche, sottotitoli: {"si" if use_caps else "no"}'
          f'{", muto" if plan.get("mute") else ""})')
