"""Scontorno locale: toglie lo sfondo da una foto e restituisce un PNG con alpha.

Tre strade, scelte da sole in base alla foto:

  misto  la strada buona per gli scatti da catalogo, anche con l'ombra: la
         rete dice dove sta il prodotto, il flood fill dagli angoli toglie
         fondo e ombra col bordo pixel-preciso del colore.
  tinta  solo flood fill, senza modello: istantaneo, ma si mangia le parti
         chiare del prodotto quando sono del colore del fondo.
  rete   U^2-Net / IS-Net via onnxruntime, per le foto vere (persone, scene,
         fondi sporchi). Il modello si scarica una volta sola in models/.

Gira in locale: nessuna API, nessun credito, nessuna foto che esce da qui.

    python3 scontorno.py foto.jpg                 -> foto-scontornata.png
    python3 scontorno.py *.jpg -o out/ --sfondo bianco
    python3 scontorno.py scarpa.jpg --ombra morbida     # ombra semitrasparente
"""
import argparse, hashlib, os, shutil, sys, time, urllib.request
import numpy as np
from PIL import Image, ImageFilter

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
ALLARGO = 2       # di quanto si allarga la protezione della rete, in pixel
CRESCITA = 3      # di quanto il fondo puo' rientrare in quell'anello, in pixel

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

    Serve a decidere se c'e' un fondo da flood-fillare: sopra ~0.97 lo scatto e'
    da catalogo (fondo bianco o in tinta, con o senza ombra).
    """
    a = np.asarray(img.convert('RGB').resize((256, 256), Image.BILINEAR)).astype(np.int16)
    bordo = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    rif = np.median(bordo, axis=0)
    return float((np.abs(bordo - rif).max(axis=1) <= tolleranza).mean())


def _riferimento(a):
    """Colore del fondo: la mediana del bordo dell'immagine."""
    return np.median(np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]]), axis=0)


def _mappa_ombra(a, rif, neutro=0.10, minimo=0.15):
    """Pixel che sono il fondo moltiplicato per un fattore < 1: cioe' un'ombra.

    Un'ombra non cambia il colore di cio' su cui cade, lo scurisce e basta: il
    rapporto col fondo e' lo stesso sui tre canali. Un pezzo di prodotto o e'
    colorato (rapporti diversi) o e' molto piu' scuro di un'ombra. Resta
    ambiguo il grigio chiaro — una suola bianca sporca somiglia a un'ombra — e
    per quello serve la protezione della rete, che in `misto` vince su questa
    mappa.
    """
    r = a / np.maximum(rif, 1)
    m = r.mean(axis=2)
    return (r.max(axis=2) - r.min(axis=2) <= neutro) & (m < 0.995) & (m > minimo)


def _dilata(maschera, px):
    """Allarga di px pixel una maschera booleana."""
    img = Image.fromarray((maschera * 255).astype(np.uint8), 'L')
    for _ in range(int(px)):
        img = img.filter(ImageFilter.MaxFilter(3))
    return np.asarray(img) > 127


def _tratti(riga):
    """Inizi e fini dei tratti contigui di True in una riga."""
    d = np.diff(np.concatenate(([np.int8(0)], riga.astype(np.int8), [np.int8(0)])))
    return np.flatnonzero(d == 1), np.flatnonzero(d == -1)


def _allaga(simile):
    """Regione di fondo: quel che si raggiunge dai quattro angoli, a 4 vicini.

    Flood fill per tratti di riga invece che per pixel: `ImageDraw.floodfill`
    e' Python puro e su 1024x1024 costa oltre un secondo, qui siamo sui 30 ms
    perche' il lavoro va col numero di tratti, non col numero di pixel.
    """
    h, w = simile.shape
    inizi, fini, visti = [], [], []
    for y in range(h):
        i, f = _tratti(simile[y])
        inizi.append(i); fini.append(f); visti.append(np.zeros(len(i), bool))

    def tratto(y, x):
        k = int(np.searchsorted(inizi[y], x, 'right')) - 1
        return k if k >= 0 and fini[y][k] > x else None

    pila = []
    for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        k = tratto(y, x)
        if k is not None:
            pila.append((y, k))
    while pila:
        y, k = pila.pop()
        if visti[y][k]:
            continue
        visti[y][k] = True
        a, b = inizi[y][k], fini[y][k]
        for ny in (y - 1, y + 1):
            if 0 <= ny < h:
                # i tratti della riga vicina che si sovrappongono a [a, b)
                lo = int(np.searchsorted(fini[ny], a, 'right'))
                hi = int(np.searchsorted(inizi[ny], b, 'left'))
                for k2 in range(lo, hi):
                    if not visti[ny][k2]:
                        pila.append((ny, k2))
    fondo = np.zeros((h, w), bool)
    for y in range(h):
        for k in np.flatnonzero(visti[y]):
            fondo[y, inizi[y][k]:fini[y][k]] = True
    return fondo


def _matte_tinta(img, tolleranza=14, protezione=None, nucleo=None, togli_ombra=False):
    """(alpha 0-1, forza dell'ombra 0-1) dal flood fill del fondo.

    `protezione` e' una maschera booleana in cui il flood non entra: e' cosi'
    che il prodotto bianco su fondo bianco non viene mangiato. `nucleo` e' la
    stessa maschera non allargata: l'anello tra le due va poi ripulito, se no
    il bordo resta punteggiato di fondo.
    """
    a = np.asarray(img.convert('RGB')).astype(np.float32)
    rif = _riferimento(a)
    stretta = np.abs(a - rif).max(axis=2) <= tolleranza
    ombrosi = _mappa_ombra(a, rif)
    simile = stretta | ombrosi if togli_ombra else stretta
    if protezione is None:
        fondo = _allaga(simile)
    else:
        fondo = _allaga(simile & ~protezione)
        if nucleo is not None:
            # L'anello si ripulisce facendo crescere il fondo di un pixel per
            # volta, e solo sul colore esatto del fondo: un secondo flood
            # libero risalirebbe dentro i riflessi chiari del prodotto, e la
            # mappa dell'ombra si mangerebbe il bordo sfumato.
            cresce = stretta & ~nucleo
            for _ in range(CRESCITA):
                fondo = fondo | (_dilata(fondo, 1) & cresce)
    alpha = np.where(fondo, 0, 255).astype(np.uint8)
    a8 = Image.fromarray(alpha, 'L').filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.7))
    alpha = np.clip((np.asarray(a8).astype(np.float32) / 255 - 0.12) / 0.80, 0, 1)
    # quanto scuriva il fondo dove abbiamo tolto l'ombra: serve a poterla tenere
    forza = np.where(fondo & ombrosi, np.clip(1 - a.mean(axis=2) / max(rif.mean(), 1), 0, 1), 0)
    return alpha, forza.astype(np.float32)


def maschera_tinta(img, tolleranza=14):
    """Solo flood fill sul colore del fondo, senza modello."""
    alpha, _ = _matte_tinta(img, tolleranza)
    return Image.fromarray((alpha * 255).astype(np.uint8), 'L')


def matte_misto(img, modello=PREDEFINITO, ombra='via', log=print):
    """Rete come protezione, colore come bordo: la strada per il catalogo.

    La rete dice grosso modo dove sta il prodotto e il flood fill non entra
    li' dentro; fuori, oltre al fondo, se ne va anche l'ombra. Il bordo resta
    quello del colore, che e' pixel-preciso, non quello della rete, che a
    320x320 e' approssimativo.
    """
    rete = np.asarray(maschera_rete(img, modello, log=log)).astype(np.float32) / 255
    a = np.asarray(img.convert('RGB')).astype(np.float32)
    ombrosi = _mappa_ombra(a, _riferimento(a))
    # Sulle ombre dure la rete sbaglia: le vede come parte del soggetto e con
    # punteggi alti (fino a 0.98 misurato). Il prodotto pero' sta a 1.00 pieno,
    # quindi a un pixel che ha anche il colore dell'ombra si chiede la certezza.
    nucleo = (rete > 0.5) & ~(ombrosi & (rete < 0.99))
    alpha, forza = _matte_tinta(img, protezione=_dilata(nucleo, ALLARGO), nucleo=nucleo,
                                togli_ombra=(ombra != 'tieni'))
    return alpha, (forza if ombra == 'morbida' else None)


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


def componi(img, alpha, sfondo=None, ritaglia=False, defringe=True, ombra=None):
    """alpha: immagine L. ombra: mappa 0-1 da appoggiare sotto il soggetto."""
    rgb = np.asarray(img.convert('RGB')).astype(np.float32)
    a = np.asarray(alpha).astype(np.float32) / 255
    if defringe:
        # sui pixel semitrasparenti resta un alone del fondo: scurirli di poco
        # toglie il bordo chiaro tipico degli scatti su bianco.
        rgb[(a > 0.05) & (a < 0.95)] *= 0.93
    if ombra is not None:
        # l'ombra torna come nero semitrasparente: cosi' regge anche su un
        # fondo che non sia quello dello scatto.
        solo_ombra = (ombra > 0.004) & (a < 0.02)
        rgb[solo_ombra] = 0
        a = np.clip(a + np.where(solo_ombra, ombra, 0), 0, 1)
    out = Image.fromarray(rgb.astype(np.uint8), 'RGB')
    out.putalpha(Image.fromarray((a * 255).astype(np.uint8), 'L'))
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
              taglio=0.0, sfuma=0.0, rientra=0.0, ombra='via', log=print):
    """Ritorna (immagine RGBA, strada usata)."""
    img = img.convert('RGB')
    strada = modo
    if modo == 'auto':
        u = fondo_unito(img)
        strada = 'misto' if u >= 0.97 else 'rete'
        log(f"fondo unito al {u*100:.0f}% -> {strada}")
    velo = None
    if strada == 'misto':
        a, velo = matte_misto(img, modello, ombra=ombra, log=log)
        alpha = Image.fromarray((a * 255).astype(np.uint8), 'L')
    elif strada == 'tinta':
        alpha = maschera_tinta(img)
    else:
        alpha = maschera_rete(img, modello, log=log)
    if strada in ('misto', 'tinta') and np.asarray(alpha).mean() > 250:
        # il flood non ha tolto niente: il fondo non era davvero unito
        log('flood fill a vuoto, passo alla rete')
        strada, velo = 'rete', None
        alpha = maschera_rete(img, modello, log=log)
    alpha = rifinisci(alpha, taglio=taglio, sfuma=sfuma, rientra=rientra)
    return componi(img, alpha, sfondo=sfondo, ritaglia=ritaglia, ombra=velo), strada


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
    p.add_argument('--modo', choices=('auto', 'misto', 'rete', 'tinta'), default='auto')
    p.add_argument('--ombra', choices=('via', 'tieni', 'morbida'), default='via',
                   help="via: l'ombra sparisce col fondo. tieni: resta attaccata al "
                        "prodotto. morbida: torna come nero semitrasparente")
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
                                rientra=a.rientra, ombra=a.ombra, log=log)
        base = os.path.splitext(os.path.basename(src))[0] + '-scontornata.png'
        dest = os.path.join(a.out, base) if a.out else os.path.join(os.path.dirname(src) or '.', base)
        os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
        out.save(dest)
        print(f"{dest}  ({strada}, {time.time()-t:.1f}s)")


if __name__ == '__main__':
    main()
