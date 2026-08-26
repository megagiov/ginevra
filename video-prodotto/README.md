# Video prodotto — pipeline locale

Genera uno spot verticale 9:16 di 10 secondi da una foto prodotto del catalogo
gmvegasi.com, con voce narrante italiana. Gira interamente in locale: nessun
servizio di generazione AI, nessun credito, nessuna API a pagamento.

Primo output: **Sneakers Donna Isa — BELLAMICA, cod. RA159I26** (variante "grigio").

## Cosa produce

- MP4 1080×1920, 30 fps, H.264 + AAC, 10,00 s esatti
- Voce fuori campo in italiano (Piper, voce `it_IT-paola-medium`)
- Quattro stacchi: aggancio → claim → suola → scamosciato → call to action

## Dipendenze

```bash
pip install Pillow numpy imageio-ffmpeg piper-tts fonttools brotli
```

Font (licenza SIL OFL, scaricabili senza account):

```bash
mkdir -p fonts
curl -L -o fonts/Anton.ttf \
  https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/anton/Anton-Regular.ttf
curl -L -o fonts/ArchivoBlack.ttf \
  https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/archivoblack/ArchivoBlack-Regular.ttf
```

Voce italiana:

```bash
mkdir -p voices
V=https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium
curl -L -o voices/it-paola.onnx      $V/it_IT-paola-medium.onnx
curl -L -o voices/it-paola.onnx.json $V/it_IT-paola-medium.onnx.json
```

## Esecuzione

```bash
# 1. immagine prodotto dal catalogo (sostituire lo slug per un altro articolo)
curl -L -o grigio-1024x1024.jpg \
  "https://www.gmvegasi.com/image/cache/catalog/products/bellamica-ra159i26-grigio-a26_3-scarpe_alte-0000-1024x1024.jpg"

# 2. scontorno dal fondo bianco + rifinitura del bordo
python3 cutout.py && python3 refine.py     # -> shoe.png

# 3. voce fuori campo, una battuta per file
for i in 0 1 2 3; do :; done               # vedi audio.py per i quattro testi
piper -m voices/it-paola.onnx -c voices/it-paola.onnx.json \
      -f out/seg0.wav --length_scale 0.95 <<< "Okay, fermati un secondo."

# 4. frame e mix audio
python3 render.py && python3 audio.py

# 5. codifica
ffmpeg -y -framerate 30 -i frames/f%04d.jpg -i out/mix.wav \
  -c:v libx264 -pix_fmt yuv420p -crf 19 -preset slow \
  -c:a aac -b:a 192k -movflags +faststart -shortest video.mp4
```

## Adattarlo a un altro prodotto

| Cosa cambiare | Dove |
|---|---|
| Immagine sorgente | nome file in `cutout.py` |
| Testi parlati | lista `SEGS` (vedi `audio.py`, array `starts` per il timing) |
| Testi a schermo | rami delle scene in `render.py` |
| Nome prodotto e prezzo | scena finale in `render.py` |
| Colore accento | costante `ACID` in `render.py` |

Il tempo del parlato va misurato **prima** di montare la grafica: `audio.py`
stampa la durata di ogni battuta, e gli stacchi in `render.py` (`A1`, `B1`,
`C1`, `D1`, `E0`) vanno allineati a quei valori.

## Note

- Lo scontorno assume fondo bianco uniforme, come le foto del catalogo. Il
  riempimento parte dai quattro angoli, quindi le zone chiare *interne* al
  prodotto (fodera, inserti) non vengono bucate.
- Il ritmo sotto la voce sono kick sintetizzati sugli stacchi, un segnaposto:
  per la pubblicazione va sostituito con un brano su licenza.
- Il prezzo a schermo è quello letto dalla scheda prodotto al momento del
  montaggio e va riverificato prima di ogni pubblicazione.
