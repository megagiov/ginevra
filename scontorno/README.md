# Scontorno — togliere lo sfondo da una foto, in locale

Come remove.bg, ma senza account, senza crediti e senza che la foto esca dalla
macchina. Trascini l'immagine nella pagina e ti torna un PNG con trasparenza.

Due strade, scelte da sole in base alla foto:

| strada | quando | tempo |
|---|---|---|
| `tinta` | scatti da catalogo su fondo unito (bianco, grigio, in tinta): flood fill dai quattro angoli | istantaneo, nessun modello |
| `rete` | foto vere — persone, scene, fondi sporchi: U²-Net / IS-Net su onnxruntime, CPU | ~0,5–1 s a foto |

Il modo `auto` misura quanto il bordo dell'immagine è di un colore solo: sopra
il 97% va di flood fill, altrimenti di rete. Se il flood fill non toglie nulla,
ricade sulla rete da solo.

## Installazione

```bash
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
```

Tre pacchetti: Pillow, numpy, onnxruntime. Al primo uso della rete il modello
viene scaricato in `models/` (176 MB, una volta sola) e verificato con sha256 —
un `.onnx` troncato non dà errore, dà una maschera vuota.

## Uso

```bash
./venv/bin/python server.py          # poi apri http://127.0.0.1:8000
```

Trascini le foto (o clicchi, o incolli con Ctrl+V), le vedi comparire
scontornate su scacchiera e scarichi il PNG. Più foto insieme vanno bene. Il
modello resta caldo in memoria: paga solo la prima richiesta.

Da riga di comando, stessa resa, anche in blocco:

```bash
./venv/bin/python scontorno.py foto.jpg                    # -> foto-scontornata.png
./venv/bin/python scontorno.py *.jpg -o out/ --ritaglia
./venv/bin/python scontorno.py foto.jpg --sfondo bianco    # o nero, grigio, ff0055
./venv/bin/python scontorno.py foto.jpg --modo rete --modello isnet
```

| opzione | cosa fa |
|---|---|
| `--modo auto\|rete\|tinta` | forza la strada invece di lasciarla decidere |
| `--modello u2net\|u2netp\|isnet` | u2net è il default; `u2netp` pesa 4,7 MB ed è più rapido ma più grossolano; `isnet` tiene meglio capelli e dettagli sottili |
| `--sfondo` | riempie il fondo invece di lasciarlo trasparente |
| `--ritaglia` | taglia al riquadro del soggetto |
| `--taglio 0.15` | spinge i mezzi toni dell'alpha a 0/1: bordo più netto, meno alone |
| `--sfuma 1.5` | ammorbidisce il bordo di N px |
| `--rientra 1` | erode il bordo di N px: toglie l'ultimo filo di sfondo |

Il server sta su `127.0.0.1`: non è raggiungibile da fuori. `--host 0.0.0.0` lo
espone alla rete locale — non c'è autenticazione, quindi fallo solo su una rete
di cui ti fidi.

## Note

- I pesi sono quelli pubblicati dal progetto [rembg](https://github.com/danielgatis/rembg)
  (licenza MIT). Qui l'inferenza è fatta a mano con onnxruntime: tre dipendenze
  invece dell'albero completo di rembg.
- **`ImageDraw.floodfill` non scrive su un'immagine creata con `Image.fromarray`**:
  il buffer numpy è di sola lettura, la chiamata fallisce in silenzio riempiendo
  zero pixel e lo scontorno esce tutto opaco. Serve `.copy()` — stessa trappola
  già pagata in `video-prodotto/`.
- Il flood fill parte dagli angoli: lo sfondo chiuso dentro il soggetto (le
  asole di una scarpa, il triangolo tra braccio e fianco) resta opaco. Su quelle
  foto conviene `--modo rete`.
- Sui pixel di bordo semitrasparenti resta un alone del fondo: viene scurito del
  7% in automatico. Se il fondo originale era scuro e il risultato ti sembra
  sporco, prova `--rientra 1`.
- Il server tiene una sola inferenza per volta (onnxruntime non è rientrante su
  una sessione condivisa): con dieci foto insieme le vedrai finire in fila.
- La cartella `models/` è fuori dal versionamento.

## Perché sta in questo repository

`video-prodotto/` scontorna già le foto del catalogo per montarle negli spot,
ma solo su fondo bianco e solo dentro la pipeline. Qui la stessa cosa è
utilizzabile su qualunque foto e da sola.
