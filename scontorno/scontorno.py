"""Scontorno locale: toglie lo sfondo da una foto e restituisce un PNG con alpha.

Due strade, scelte da sole in base alla foto:

  tinta  flood fill dai quattro angoli, per gli scatti da catalogo su fondo
         unito. Istantaneo, nessun modello da scaricare, bordo pixel-preciso.
  rete   U^2-Net / IS-Net via onnxruntime, per le foto vere (persone, scene,
         fondi sporchi). Il modello si scarica una volta sola in models/.

Gira in locale: nessuna API, nessun credito, nessuna foto che esce da qui.

    python3 scontorno.py foto.jpg                 -> foto-scontornata.png
    python3 scontorno.py *.jpg -o out/ --sfondo bianco
    python3 scontorno.py foto.jpg --modo rete --modello isnet
"""
import argparse, hashlib, os, shutil, sys, time, urllib.request
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

QUI = os.path.dirname(os.path.abspath(__file__))
CARTELLA_MODELLI = os.environ.get('SCONTORNO_MODELS', os.path.join(QUI, 'models'))
BASE = 'https://github.com/danielgatis/rembg/releases/download/v0.0.0'

# Pesi pubblicati dal progetto rembg (MIT). Lo sha256 va verificato dopo lo
# scaricamento: un .onnx troncato non da' errore, da' una maschera vuota.
MODELLI = {
    'u2net':  dict(file='u2net.onnx',
                   sha='8d10d2f3bb75ae3b6d527c77944fc5e7dcd94b29809d47a739a7a728a912b491',
                   lato=320,  media=(0.485, 0.456, 0.406), dev=(0.229, 0.224, 0.225),
                   nota='generico, 176 MB, ~1 s a foto — il default'),
    'u2netp': dict(file='u2netp.onnx',
                   sha='309c8469258dda742793dce0ebea8e6dd393174f89934733ecc8b14c76f4ddd8',
                   lato=320,  media=(0.485, 0.456, 0.406), dev=(0.229, 0.224, 0.225),
                   nota='leggero, 4,7 MB, ~0,2 s — bordo piu\' grossolano'),
    'isnet':  dict(file='isnet-general-use.onnx',
                   sha='60920e99c45464f2ba57bee2ad08c919a52bbf852739e96947fbb4358c0d964a',
                   lato=1024, media=(0.5, 0.5, 0.5), dev=(1.0, 1.0, 1.0),
                   nota='bordi migliori su capelli e dettagli sottili, 179 MB, ~4 s'),
}
PREDEFINITO = os.environ.get('SCONTORNO_MODEL', 'u2net')

COLORI = {'bianco': (255, 255, 255), 'nero': (0, 0, 0), 'grigio': (240, 240, 240),
          'trasparente': None}


# ---------------------------------------------------------------- modello

def percorso_modello(nome, scarica=True, log=print):
    """Ritorna il path del .onnx, scaricandolo alla prima chiamata."""
    if nome not in MODELLI:
        raise SystemExit(f"modello sconosciuto: {nome} (scegli tra {', '.join(MODELLI)})")
    m = MODELLI[nome]
    dest = os.path.join(CARTELLA_MODELLI, m['file'])
    if os.path.exists(dest) and _sha(dest) == m['sha']:
        return dest
    if not scarica:
        raise SystemExit(f'manca {dest}: serve una connessione al primo avvio')
    os.makedirs(CARTELLA_MODELLI, exist_ok=True)
    url = f"{BASE}/{m['file']}"
    log(f"scarico {m['file']} da {url} (una volta sola)")
    tmp = dest + '.parziale'
    with urllib.request.urlopen(url, timeout=120) as r, open(tmp, 'wb') as f:
        shutil.copyfileobj(r, f, 1 << 20)
    if _sha(tmp) != m['sha']:
        os.remove(tmp)
        raise SystemExit('sha256 non corrisponde: scaricamento interrotto o file sostituito')
    os.replace(tmp, dest)
    log(f"salvato in {dest}")
    return dest


def _sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for blocco in iter(lambda: f.read(1 << 20), b''):
            h.update(blocco)
    return h.hexdigest()


_sessioni = {}


def sessione(nome=PREDEFINITO, log=print):
    """Sessione onnxruntime tenuta in memoria: caricarla costa piu' dell'inferenza."""
    if nome not in _sessioni:
        import onnxruntime as ort
        path = percorso_modello(nome, log=log)
        opt = ort.SessionOptions()
        opt.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opt.log_severity_level = 3
        t = time.time()
        _sessioni[nome] = ort.InferenceSession(path, opt, providers=ort.get_available_providers())
        log(f"modello {nome} pronto in {time.time()-t:.1f}s")
    return _sessioni[nome]


def maschera_rete(img, nome=PREDEFINITO, log=print):
    """Maschera 0-255 alla risoluzione dell'originale."""
    m = MODELLI[nome]
    lato = m['lato']
    piccola = img.convert('RGB').resize((lato, lato), Image.LANCZOS)
    a = np.asarray(piccola).astype(np.float32)
    a /= max(a.max(), 1e-6)
    a = (a - np.array(m['media'], np.float32)) / np.array(m['dev'], np.float32)
    x = np.transpose(a, (2, 0, 1))[None].astype(np.float32)
    s = sessione(nome, log=log)
    pred = s.run(None, {s.get_inputs()[0].name: x})[0][:, 0, :, :]
    lo, hi = float(pred.min()), float(pred.max())
    pred = (pred - lo) / max(hi - lo, 1e-6)
    out = Image.fromarray((np.squeeze(pred) * 255).astype(np.uint8), 'L')
    return out.resize(img.size, Image.LANCZOS)


# ---------------------------------------------------------------- fondo unito

def fondo_unito(img, tolleranza=14):
    """Quanto il bordo dell'immagine e' di un colore solo, tra 0 e 1.

    Serve a decidere se basta il flood fill: sopra ~0.97 lo scatto e' da
    catalogo (fondo bianco o in tinta) e la rete non aggiunge niente.
    """
    a = np.asarray(img.convert('RGB').resize((256, 256), Image.BILINEAR)).astype(np.int16)
    bordo = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    rif = np.median(bordo, axis=0)
    return float((np.abs(bordo - rif).max(axis=1) <= tolleranza).mean())


def maschera_tinta(img, tolleranza=14):
    """Flood fill dai quattro angoli sul colore di fondo."""
    a = np.asarray(img.convert('RGB')).astype(np.int16)
    bordo = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    rif = np.median(bordo, axis=0)
    simile = (np.abs(a - rif).max(axis=2) <= tolleranza).astype(np.uint8) * 255
    # .copy() indispensabile: floodfill non scrive su un'immagine che condivide
    # il buffer di sola lettura di numpy, fallisce in silenzio riempiendo 0 pixel
    # e lo scontorno esce tutto opaco (trappola gia' pagata in video-prodotto).
    m = Image.fromarray(simile, 'L').copy()
    w, h = m.size
    for xy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if m.getpixel(xy) == 255:
            ImageDraw.floodfill(m, xy, 128, thresh=0)
    alpha = np.where(np.asarray(m) == 128, 0, 255).astype(np.uint8)
    a8 = Image.fromarray(alpha, 'L').filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.7))
    return Image.fromarray((np.clip((np.asarray(a8).astype(np.float32) / 255 - 0.12) / 0.80, 0, 1) * 255).astype(np.uint8), 'L')


# ---------------------------------------------------------------- rifinitura

def rifinisci(alpha, taglio=0.0, sfuma=0.0, rientra=0.0):
    """taglio: spinge a 0/1 i mezzi toni. sfuma: bordo morbido. rientra: erode."""
    a = np.asarray(alpha).astype(np.float32) / 255
    if rientra > 0:
        img = Image.fromarray((a * 255).astype(np.uint8), 'L')
        for _ in range(int(round(rientra))):
            img = img.filter(ImageFilter.MinFilter(3))
        a = np.asarray(img).astype(np.float32) / 255
    if taglio > 0:
        a = np.clip((a - taglio) / max(1e-6, 1 - 2 * taglio), 0, 1)
    img = Image.fromarray((a * 255).astype(np.uint8), 'L')
    if sfuma > 0:
        img = img.filter(ImageFilter.GaussianBlur(sfuma))
    return img


def componi(img, alpha, sfondo=None, ritaglia=False, defringe=True):
    rgb = img.convert('RGB')
    if defringe:
        # sui pixel semitrasparenti resta un alone del fondo: scurirli di poco
        # toglie il bordo chiaro tipico degli scatti su bianco.
        a = np.asarray(alpha).astype(np.float32) / 255
        px = np.asarray(rgb).astype(np.float32)
        bordo = (a > 0.05) & (a < 0.95)
        px[bordo] *= 0.93
        rgb = Image.fromarray(px.astype(np.uint8), 'RGB')
    out = rgb.copy()
    out.putalpha(alpha)
    if ritaglia:
        bb = out.getbbox()
        if bb:
            out = out.crop(bb)
    if sfondo is not None:
        piano = Image.new('RGBA', out.size, tuple(sfondo) + (255,))
        piano.alpha_composite(out)
        out = piano
    return out


def scontorna(img, modo='auto', modello=PREDEFINITO, sfondo=None, ritaglia=False,
              taglio=0.0, sfuma=0.0, rientra=0.0, log=print):
    """Ritorna (immagine RGBA, strada usata)."""
    img = img.convert('RGB')
    strada = modo
    if modo == 'auto':
        u = fondo_unito(img)
        strada = 'tinta' if u >= 0.97 else 'rete'
        log(f"fondo unito al {u*100:.0f}% -> {strada}")
    alpha = maschera_tinta(img) if strada == 'tinta' else maschera_rete(img, modello, log=log)
    if strada == 'tinta' and np.asarray(alpha).mean() > 250:
        # il flood non ha tolto niente: il fondo non era davvero unito
        log('flood fill a vuoto, passo alla rete')
        strada = 'rete'
        alpha = maschera_rete(img, modello, log=log)
    alpha = rifinisci(alpha, taglio=taglio, sfuma=sfuma, rientra=rientra)
    return componi(img, alpha, sfondo=sfondo, ritaglia=ritaglia), strada


# ---------------------------------------------------------------- CLI

def _colore(s):
    if s in COLORI:
        return COLORI[s]
    s = s.lstrip('#')
    if len(s) == 6:
        return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))
    raise argparse.ArgumentTypeError("colore: bianco, nero, grigio, trasparente o esadecimale tipo ff0055")


def main(argv=None):
    p = argparse.ArgumentParser(description='Scontorna una foto in locale.')
    p.add_argument('foto', nargs='+')
    p.add_argument('-o', '--out', default=None, help='cartella di destinazione')
    p.add_argument('--modo', choices=('auto', 'rete', 'tinta'), default='auto')
    p.add_argument('--modello', choices=tuple(MODELLI), default=PREDEFINITO)
    p.add_argument('--sfondo', type=_colore, default=None,
                   help='riempie il fondo invece di lasciarlo trasparente')
    p.add_argument('--ritaglia', action='store_true', help='taglia al riquadro del soggetto')
    p.add_argument('--taglio', type=float, default=0.0, help='0-0.4: spinge i mezzi toni a 0/1')
    p.add_argument('--sfuma', type=float, default=0.0, help='raggio di sfocatura del bordo, px')
    p.add_argument('--rientra', type=float, default=0.0, help='erode il bordo di N px')
    p.add_argument('--zitto', action='store_true')
    a = p.parse_args(argv)
    log = (lambda *x: None) if a.zitto else (lambda *x: print(*x, file=sys.stderr))

    for src in a.foto:
        t = time.time()
        img = Image.open(src)
        out, strada = scontorna(img, modo=a.modo, modello=a.modello, sfondo=a.sfondo,
                                ritaglia=a.ritaglia, taglio=a.taglio, sfuma=a.sfuma,
                                rientra=a.rientra, log=log)
        base = os.path.splitext(os.path.basename(src))[0] + '-scontornata.png'
        dest = os.path.join(a.out, base) if a.out else os.path.join(os.path.dirname(src) or '.', base)
        os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
        out.save(dest)
        print(f"{dest}  ({strada}, {time.time()-t:.1f}s)")


if __name__ == '__main__':
    main()
