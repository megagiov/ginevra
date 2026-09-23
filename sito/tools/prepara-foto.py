#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Converte le foto dell'azienda in WebP per il sito.

    pip install Pillow
    python3 tools/prepara-foto.py

Legge i file in src/img/originali/ e scrive i WebP in src/img/, che build.py
si limita a copiare: cosi' la generazione del sito resta senza dipendenze e
questo strumento serve solo quando arrivano foto nuove.

Ogni voce di FOTO dice come va trattata l'immagine. Le foto non vengono
ingrandite, salvo l'anteprima social che ha una misura minima imposta dai
social: se l'originale e' piu' piccolo, resta com'e' (meglio un po' piccola
che sgranata).
"""

import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Serve Pillow:  pip install Pillow")

QUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(QUI, "src", "img")
ORIG = os.path.join(SRC, "originali")

# nome originale -> (nome finale, larghezza, ritaglio, ingrandisci, riquadro)
# Il riquadro (x0, y0, x1, y1) e' un ritaglio fisso applicato per primo, in
# pixel sull'originale: serve quando bisogna togliere qualcosa di preciso
# dall'inquadratura, non semplicemente centrare.
# Il ritaglio e' il rapporto larghezza/altezza voluto: l'immagine viene
# tagliata al centro fino a quel rapporto, senza deformarla.
QUATTRO_TERZI = 4 / 3

FOTO = [
    ("trasloco-autoscala-palazzo-napoli.jpg",
     "trasloco-autoscala-palazzo-napoli.webp", 1200, None, False, None),
    ("mezzi-sorgente-traslochi-napoli.jpg",
     "mezzi-sorgente-traslochi-napoli.webp", 1200, None, False, None),
    ("montaggio-letto-arredo-design-napoli.jpg",
     "montaggio-letto-arredo-design-napoli.webp", 1000, QUATTRO_TERZI,
     False, None),
    ("cucina-bianca-montata-napoli.jpg",
     "cucina-bianca-montata-napoli.webp", 1000, QUATTRO_TERZI, False, None),
    ("cucina-montata-napoli.jpg",
     "cucina-montata-napoli.webp", 800, QUATTRO_TERZI, False, None),
    ("cucina-isola-montata-napoli.jpg",
     "cucina-isola-montata-napoli.webp", 800, QUATTRO_TERZI, False, None),
    # Il riquadro esclude il mezzo di un'altra ditta, che nell'originale
    # compare sulla destra con l'indirizzo del suo sito ben leggibile.
    ("carico-furgone-centro-storico-napoli.jpg",
     "carico-furgone-centro-storico-napoli.webp", 1000, None, False,
     (20, 250, 560, 655)),
    # Stessa foto, inquadratura piu' larga sul palazzo e sulla strada: serve
    # alla pagina degli uffici, dove non abbiamo ancora uno scatto dedicato.
    ("carico-furgone-centro-storico-napoli.jpg",
     "carico-mezzi-strada-napoli.webp", 1000, None, False,
     (0, 140, 535, 665)),
    # Anteprima social. Unico caso in cui si ingrandisce: sotto i 600x315
    # WhatsApp e Facebook mostrano una miniatura quadratina invece della
    # scheda grande, e una foto un po' morbida rende comunque meglio di un
    # rettangolo colorato. Da rifare quando arrivano gli originali.
    ("trasloco-autoscala-palazzo-napoli.jpg",
     "og-sorgente-traslochi.jpg", 1200, 1200 / 630, True, None),
]

QUALITA = 82


def ritaglia(im, rapporto):
    largo, alto = im.size
    if largo / alto > rapporto:          # troppo larga: taglio ai lati
        nuovo = int(alto * rapporto)
        x = (largo - nuovo) // 2
        return im.crop((x, 0, x + nuovo, alto))
    nuovo = int(largo / rapporto)        # troppo alta: taglio sopra e sotto
    y = (alto - nuovo) // 2
    return im.crop((0, y, largo, y + nuovo))


def main():
    if not os.path.isdir(ORIG):
        sys.exit("Manca la cartella %s" % ORIG)
    for (sorgente, destinazione, larghezza, rapporto, ingrandisci,
         riquadro) in FOTO:
        percorso = os.path.join(ORIG, sorgente)
        if not os.path.exists(percorso):
            print("  salto %s (non c'e')" % sorgente)
            continue
        im = Image.open(percorso).convert("RGB")
        prima = im.size
        if riquadro:
            im = im.crop(riquadro)
        if rapporto:
            im = ritaglia(im, rapporto)
        if im.width > larghezza or (ingrandisci and im.width < larghezza):
            altezza = round(im.height * larghezza / im.width)
            im = im.resize((larghezza, altezza), Image.LANCZOS)
        uscita = os.path.join(SRC, destinazione)
        if destinazione.endswith(".jpg"):
            im.save(uscita, "JPEG", quality=QUALITA, optimize=True,
                    progressive=True)
        else:
            im.save(uscita, "WEBP", quality=QUALITA, method=6)
        print("  %s  %dx%d -> %dx%d  %.0f kB"
              % (destinazione, prima[0], prima[1], im.width, im.height,
                 os.path.getsize(uscita) / 1024))


if __name__ == "__main__":
    main()
