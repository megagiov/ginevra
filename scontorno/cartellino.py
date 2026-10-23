"""Dalla scansione di un cartellino alla foto prodotto per il sito.

Il cartellino ha la foto del prodotto stampata in mezzo a logo, QR e testi.
Qui si trova la foto, la si ritaglia, si toglie il fondo e la si mette su una
tela bianca quadrata col prodotto centrato, come le foto del catalogo.

    python cartellino.py scansione.pdf            # -> scansione-sito.jpg 800x800
    python cartellino.py *.pdf -o sito/ --misura 1000

Legge PDF (serve pypdfium2) e immagini.
"""
import argparse
import os
import sys
import time

import numpy as np
from PIL import Image

import scontorno as S

DPI = 300


def apri_scansione(percorso):
    """Ritorna una lista di immagini RGB: una per pagina se e' un PDF."""
    if percorso.lower().endswith('.pdf'):
        try:
            import pypdfium2 as pdfium
        except ImportError:
            raise SystemExit("per leggere i PDF serve pypdfium2: pip install pypdfium2")
        doc = pdfium.PdfDocument(percorso)
        return [doc[i].render(scale=DPI / 72).to_pil().convert('RGB') for i in range(len(doc))]
    import converti as C
    return [C.apri(percorso).convert('RGB')]


def _componenti(m):
    """Etichetta 4-connessa a tratti di riga su una maschera piccola.
    Ritorna lista di (area, y0, y1, x0, x1)."""
    h, w = m.shape
    lab = np.zeros((h, w), np.int32)
    pezzi = []
    n = 0
    for y in range(h):
        for x in range(w):
            if not m[y, x] or lab[y, x]:
                continue
            n += 1
            pila = [(y, x)]
            lab[y, x] = n
            area, y0, y1, x0, x1 = 0, y, y, x, x
            while pila:
                cy, cx = pila.pop()
                area += 1
                y0, y1, x0, x1 = min(y0, cy), max(y1, cy), min(x0, cx), max(x1, cx)
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and not lab[ny, nx]:
                        lab[ny, nx] = n
                        pila.append((ny, nx))
            pezzi.append((area, y0, y1 + 1, x0, x1 + 1))
    return pezzi


def trova_prodotto(img, log=print):
    """Riquadro (x0, y0, x1, y1) della foto prodotto dentro la scansione.

    Il prodotto e' la macchia colorata piu' grande che non sia una striscia:
    la fascia col logo del marchio e' alta e stretta (o larga e bassa), il QR
    e i testi sono piccoli o grigi."""
    passo = 8
    hsv = np.asarray(img.convert('HSV').reduce(passo)).astype(np.float32) / 255
    s, v = hsv[..., 1], hsv[..., 2]
    # tutto cio' che si stacca dal bianco del cartellino: colori, ma anche
    # grigi e neri (una felpa grigia ha saturazione zero)
    pezzi = _componenti((s > 0.22) | (v < 0.80))
    buoni = []
    for area, y0, y1, x0, x1 in pezzi:
        hh, ww = y1 - y0, x1 - x0
        allungato = max(hh, ww) / max(1, min(hh, ww))
        pieno = area / (hh * ww)
        bordo = y0 == 0 or x0 == 0 or y1 == hsv.shape[0] or x1 == hsv.shape[1]
        # via: briciole, strisce (fascia del marchio), cornici sparse e tutto
        # cio' che tocca il bordo della scansione (ombra del coperchio)
        if (area < 30 or allungato > 3.2 or (allungato > 2.2 and pieno < 0.5)
                or pieno < 0.2 or bordo):
            continue
        buoni.append((area, y0, y1, x0, x1))
    if not buoni:
        log('non trovo la foto del prodotto: uso tutta la pagina')
        return (0, 0) + img.size, (0, 0) + img.size
    buoni.sort(reverse=True)
    grande = buoni[0][0]
    # si parte dal pezzo piu' grande e si aggiungono quelli grossi che lo
    # toccano quasi (felpa + pantalone): il QR e i testi stanno piu' lontani
    _, y0, y1, x0, x1 = buoni[0]
    tenuti = [buoni[0]]
    vicino = 4
    cambiato = True
    while cambiato:
        cambiato = False
        for b in buoni:
            if b in tenuti or b[0] < grande * 0.05:
                continue
            if (b[1] <= y1 + vicino and b[2] >= y0 - vicino
                    and b[3] <= x1 + vicino and b[4] >= x0 - vicino):
                tenuti.append(b)
                y0, y1 = min(y0, b[1]), max(y1, b[2])
                x0, x1 = min(x0, b[3]), max(x1, b[4])
                cambiato = True
    m = 6  # un po' di fondo attorno, in celle
    box = (max(0, (x0 - m) * passo), max(0, (y0 - m) * passo),
           min(img.width, (x1 + m) * passo), min(img.height, (y1 + m) * passo))
    # il riquadro stretto, con appena un filo: fuori da qui non c'e' prodotto
    stretto = (max(0, (x0 - 1) * passo), max(0, (y0 - 1) * passo),
               min(img.width, (x1 + 1) * passo), min(img.height, (y1 + 1) * passo))
    log(f'prodotto in {stretto}, {len(tenuti)} pezzi')
    return box, stretto


def su_tela(rgba, lato=800, margine=0.045, sfondo=(255, 255, 255)):
    """Prodotto centrato su tela quadrata, con un margine come il catalogo."""
    bb = rgba.getbbox()
    if bb:
        rgba = rgba.crop(bb)
    utile = int(lato * (1 - 2 * margine))
    f = min(utile / rgba.width, utile / rgba.height)
    if f < 1:  # mai ingrandire
        rgba = rgba.resize((max(1, round(rgba.width * f)), max(1, round(rgba.height * f))),
                           Image.LANCZOS)
    tela = Image.new('RGBA', (lato, lato), tuple(sfondo) + (255,))
    tela.alpha_composite(rgba, ((lato - rgba.width) // 2, (lato - rgba.height) // 2))
    return tela.convert('RGB')


def da_cartellino(img, lato=800, sfondo=(255, 255, 255), modo='misto', log=print):
    box, stretto = trova_prodotto(img, log=log)
    pezzo = img.crop(box)
    # sul cartellino non ci sono ombre vere: col test dell'ombra un prodotto
    # grigio sembrerebbe ombra e perderebbe i bordi
    out, strada = S.scontorna(pezzo, modo=modo, ombra='tieni', log=log)
    # il ritaglio largo serve a non tagliare il prodotto, ma puo' prendere il
    # bordo del cartellino o un pezzo di testo: quello fuori dal riquadro
    # stretto si cancella
    a = np.asarray(out.getchannel('A')).copy()
    sx0, sy0 = stretto[0] - box[0], stretto[1] - box[1]
    sx1, sy1 = stretto[2] - box[0], stretto[3] - box[1]
    tieni = np.zeros_like(a, bool)
    tieni[sy0:sy1, sx0:sx1] = True
    a[~tieni] = 0
    out.putalpha(Image.fromarray(a, 'L'))
    return su_tela(out, lato=lato, sfondo=sfondo), strada


def main(argv=None):
    p = argparse.ArgumentParser(description='Foto per il sito dalla scansione di un cartellino.')
    p.add_argument('scansioni', nargs='+')
    p.add_argument('-o', '--out', default=None, help='cartella di destinazione')
    p.add_argument('--misura', type=int, default=800, help='lato della tela quadrata')
    p.add_argument('--sfondo', type=S._colore, default=(255, 255, 255))
    p.add_argument('--in', dest='formato', choices=('jpg', 'png', 'webp'), default='jpg')
    p.add_argument('--modo', choices=('misto', 'rete', 'tinta', 'auto'), default='misto')
    a = p.parse_args(argv)
    log = lambda *x: print(*x, file=sys.stderr)
    for src in S._espandi(a.scansioni):
        t = time.time()
        pagine = apri_scansione(src)
        for i, pagina in enumerate(pagine):
            out, strada = da_cartellino(pagina, a.misura, a.sfondo, a.modo, log=log)
            base = os.path.splitext(os.path.basename(src))[0]
            base += (f'-{i+1}' if len(pagine) > 1 else '') + '-sito.' + a.formato
            cartella = a.out or os.path.dirname(src) or '.'
            os.makedirs(cartella, exist_ok=True)
            dest = os.path.join(cartella, base)
            if a.formato == 'jpg':
                out.save(dest, quality=92, optimize=True)
            else:
                out.save(dest)
            print(f'{dest}  ({strada}, {time.time()-t:.1f}s)')


if __name__ == '__main__':
    main()
