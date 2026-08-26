"""Sfoca il fondo dietro la presentatrice generata.

Serve perche' il modello immagine storpia le scritte sui prodotti dello
scaffale: sfocando il fondo le storpiature non sono piu' leggibili e la figura
resta in un negozio riconoscibile.

    python3 back-to-school/sfoca_avatar.py
"""
from PIL import Image, ImageFilter
import numpy as np
from scipy import ndimage
from rembg import remove, new_session
import os

BASE = os.path.dirname(os.path.abspath(__file__))
FOTO = os.path.join(BASE, 'foto')
SRC = os.path.join(FOTO, 'avatar-presentazione-9x16.png')
DST = os.path.join(FOTO, 'avatar-sfocato.png')

MODELLI = ['birefnet-portrait', 'isnet-general-use', 'u2net_human_seg']
BUCO_MAX = 8000      # px: sopra questa soglia il buco e' vero spazio, non rumore
SFOCATURA = 24
SCURIMENTO = 0.90


def maschera(im):
    """Intersezione di tre segmentazioni.

    Ogni modello sbava su oggetti diversi dello scaffale e lascia frammenti di
    prodotto a fuoco attaccati alla sagoma. Quello che tutti e tre chiamano
    persona e' persona.
    """
    ms = []
    for nome in MODELLI:
        m = remove(im, session=new_session(nome), only_mask=True)
        ms.append(np.asarray(m) > 140)
    keep = ms[0] & ms[1] & ms[2]

    lab, n = ndimage.label(keep)
    sizes = ndimage.sum(keep, lab, range(1, n + 1))
    keep = lab == (int(np.argmax(sizes)) + 1)

    # riempire tutti i buchi chiude anche lo spazio fra braccio e busto, e li'
    # dentro resta a fuoco lo scaffale che si vede in mezzo
    holes = ndimage.binary_fill_holes(keep) & ~keep
    hl, hn = ndimage.label(holes)
    if hn:
        hs = ndimage.sum(holes, hl, range(1, hn + 1))
        keep = keep | np.isin(hl, [i + 1 for i, s in enumerate(hs) if s < BUCO_MAX])
    return keep


def main():
    im = Image.open(SRC).convert('RGB')
    keep = maschera(im)
    print('copertura della figura: %.1f %%' % (keep.mean() * 100))

    # bordo sfumato: la maschera esatta al pixel taglia come un ritaglio di
    # carta, sfumarla fa leggere il confine come profondita' di campo
    m = Image.fromarray((keep * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(7))
    a = np.clip((np.asarray(m).astype(np.float32) / 255 - 0.42) / 0.40, 0, 1)[:, :, None]

    bg = np.clip(np.asarray(im.filter(ImageFilter.GaussianBlur(SFOCATURA))).astype(np.float32) * SCURIMENTO, 0, 255)
    out = np.asarray(im).astype(np.float32) * a + bg * (1 - a)
    Image.fromarray(out.astype(np.uint8)).save(DST)
    print('scritto', DST)


if __name__ == '__main__':
    main()
