# Video prodotto — pipeline locale

Genera spot verticali 9:16 di 10 secondi dalle foto del catalogo gmvegasi.com,
con voce narrante italiana. Gira interamente in locale: nessun servizio di
generazione AI, nessun credito, nessuna API a pagamento.

Output corrente: **Sneakers Donna Isa — BELLAMICA, cod. RA159I26**, tutte e
cinque le varianti colore (grigio, beige, marrone, bordeaux, nero).

## Cosa produce

- MP4 1080×1920, 30 fps, H.264 + AAC, 10,00 s esatti, ~14 MB
- Voce fuori campo in italiano (Piper, voce `it_IT-paola-medium`)
- Cinque stacchi: aggancio → claim → suola → finiture → call to action

## Dipendenze

```bash
pip install Pillow numpy imageio-ffmpeg piper-tts
```

Font (licenza SIL OFL) e voce italiana:

```bash
mkdir -p fonts voices out
curl -L -o fonts/Anton.ttf \
  https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/anton/Anton-Regular.ttf
curl -L -o fonts/ArchivoBlack.ttf \
  https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/archivoblack/ArchivoBlack-Regular.ttf

V=https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium
curl -L -o voices/it-paola.onnx      $V/it_IT-paola-medium.onnx
curl -L -o voices/it-paola.onnx.json $V/it_IT-paola-medium.onnx.json
```

Nota: i raw di `github.com` possono essere bloccati da un proxy aziendale;
`cdn.jsdelivr.net` serve gli stessi file. La CSS API di Google Fonts con uno
user-agent vecchio restituisce EOT, non TTF, e Pillow non lo apre.

## Esecuzione

```bash
# 1. immagini prodotto dal catalogo, una per variante
B=https://www.gmvegasi.com/image/cache/catalog/products
for c in grigio-a26_3 beige-a26_2 marrone-a26_4 bordeaux-a26_5 nero-a26_1; do
  curl -L -o "${c%%-*}-1024x1024.jpg" \
    "$B/bellamica-ra159i26-${c}-scarpe_alte-0000-1024x1024.jpg"
done

# 2. voce fuori campo, una battuta per file (testi in cima ad audio.py)
piper -m voices/it-paola.onnx -c voices/it-paola.onnx.json \
      -f out/seg0.wav --length_scale 0.95 <<< "Okay, fermati un secondo."
# ... idem per seg1, seg2, seg3

# 3. mix audio (stampa la durata di ogni battuta)
python3 audio.py

# 4. render + codifica di tutte le varianti, oppure di una sola
python3 build.py
python3 build.py nero
```

## Adattarlo a un altro prodotto

| Cosa cambiare | Dove |
|---|---|
| Varianti e immagini | lista `VARIANTS` in `build.py` |
| Etichette dei primi piani | campi `label` / `sub` di ogni variante |
| Testi parlati | testi passati a piper; `starts` in `audio.py` per il timing |
| Testi a schermo | rami delle scene in `build.py` |
| Nome, taglie, prezzo | scena finale in `build.py` |
| Colore accento | costante `ACID` in `build.py` |

Il tempo del parlato va misurato **prima** di montare la grafica: `audio.py`
stampa la durata di ogni battuta, e gli stacchi (`A1`, `B1`, `C1`, `D1`, `E0`)
vanno allineati a quei valori.

## Trappole già pagate

- **`ImageDraw.floodfill` non scrive su un'immagine creata con
  `Image.fromarray`**: il buffer numpy è di sola lettura e la chiamata fallisce
  in silenzio riempiendo zero pixel, quindi lo scontorno esce completamente
  opaco e il fondo bianco resta attaccato. Serve `.copy()`.
- **Le fasce di testo vanno dimensionate su `textbbox`, non su `font.size`**:
  le maiuscole accentate (PIÙ) salgono più in alto dell'altezza nominale e
  vengono tagliate.
- **Il de-fringe del bordo deve scalare col guadagno** applicato al prodotto:
  schiarendo una variante scura si schiarisce anche l'alone di fondo rimasto
  sui pixel semitrasparenti.
- **Le varianti scure spariscono sul fondo carbone**: il campo `lift` schiarisce
  il fondo per colore (nero 62, bordeaux 28, marrone 20).

## Note editoriali

- La scheda prodotto **non dichiara i materiali**. Le etichette a schermo
  descrivono quindi solo ciò che è visibile ("effetto camoscio"), non la
  composizione. Non aggiungere affermazioni sul materiale senza una fonte.
- La suola gum è reale solo su grigio, beige e nero; su marrone e bordeaux è in
  tinta, e lì l'etichetta parla della zeppa interna.
- Il ritmo sotto la voce sono kick sintetizzati sugli stacchi, un segnaposto:
  per la pubblicazione va sostituito con un brano su licenza.
- Prezzo e taglie sono quelli letti dalla scheda al momento del montaggio e
  vanno riverificati prima di ogni pubblicazione.

## Sostituire il parlato di un video generato (`align.py` + `finish.py`)

I modelli video generativi pronunciano male l'italiano: nel primo spot in
negozio storpiavano "venduto" in "venditi", "finiture" in "finituri" e
"sfuggire" in "sfiggere". Questi due script rimpiazzano la traccia con una voce
italiana corretta, senza rigenerare il video e senza spendere crediti.

Verifica del difetto prima di intervenire: si trascrive l'audio generato **e**
una voce italiana di controllo con lo stesso riconoscitore. Se la controprova
esce corretta e il generato no, l'errore e' nel parlato, non nella misura.

```bash
pip install faster-whisper scipy
# 1. tempi di parola del parlato generato -> gen_words.json
# 2. una battuta per file con piper -> out/nat0..3.wav, tempi -> my_words.json
python3 align.py     # deforma parola per parola sui tempi di lei
python3 finish.py    # fondo sala + trattamento voce + mix
ffmpeg -i video.mp4 -i out/mix_finale.wav -map 0:v -map 1:a -c:v copy -c:a aac out.mp4
```

Come funziona l'allineamento:

- i punti di taglio stanno sugli **attacchi di parola**, non sui silenzi, e ogni
  segmento viene portato alla durata del corrispondente con `atempo` (che
  preserva l'intonazione, a differenza del ricampionamento);
- la durata totale di ogni frase viene **forzata sulla campata di lei** dopo il
  montaggio dei segmenti: senza questo passo le dissolvenze ai giunti
  accorciano la frase e l'errore si accumula (da 68 ms a 162 ms di scarto);
- resta una correzione costante per frase, misurata sul risultato e reiniettata
  in `corr.json`: una seconda passata porta lo scarto medio da 68 a 53 ms.

Risultato misurato sullo spot in negozio: **scarto medio 53 ms, mediano 30 ms,
23 parole su 24 entro 150 ms**. Lo standard di trasmissione ITU-R BT.1359
considera impercettibile una desincronizzazione tra -125 e +45 ms.

`finish.py` ricostruisce anche il fondo sala: stima lo spettro medio del 10% di
fotogrammi piu' silenziosi dell'audio originale e ne sintetizza rumore della
stessa forma. Senza, la voce sostituita suona staccata dalla stanza. Poi
passa-alto a 85 Hz, taglio degli acuti da microfono di telefono, compressione
morbida e un riverbero corto al 11%.

Nota: agganciare la frase all'attacco di energia invece che al tempo di parola
peggiora le cose (162 ms contro 103 ms) — provato e scartato.
