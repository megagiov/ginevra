# Video musica — equalizzatore virtuale per TikTok

Da un file audio produce un video verticale 9:16 con equalizzatore animato e
sfondo a gradiente che pulsa sul brano. Gira in locale: nessun credito, nessuna
API a pagamento. Serve solo il brano.

## Formato del video

- MP4 1080×1920, 30 fps, H.264 + AAC 192 kbps
- Durata a scelta (default 30 s, il taglio piu' usato per il feed)
- Audio identico all'originale nel tratto scelto, nessuna ricompressione creativa

## Dipendenze

```bash
pip install numpy Pillow imageio-ffmpeg
```

Font consigliato (licenza SIL OFL); senza, usa il DejaVu di sistema:

```bash
mkdir -p fonts out
curl -L -o fonts/Anton.ttf \
  https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/anton/Anton-Regular.ttf
```

## Uso

```bash
python3 eq.py brano.mp3 --start 45 --dur 30 \
        --titolo "Nome brano" --artista "Artista" \
        --preset sunset --out brano.mp4
```

| opzione | cosa fa |
| --- | --- |
| `--start` | secondo di inizio dentro il brano (scegli il ritornello) |
| `--dur` | durata in secondi del clip |
| `--titolo` / `--artista` | testo a schermo, opzionali |
| `--preset` | `sunset`, `ocean`, `neon`, `ember`, `mono` |
| `--out` | nome del file in `out/` |

Il render costa circa 8 s di calcolo per ogni secondo di video: 30 s di clip
sono circa 4 minuti.

## Come funziona

1. `ffmpeg` decodifica il tratto scelto in PCM mono 44,1 kHz.
2. FFT su finestre di 2048 campioni centrate sul frame, energia raccolta in 48
   bande log-spaziate da 30 Hz a 16 kHz — l'orecchio legge le ottave, non gli Hz.
3. Espansione per banda: il fondo di ogni banda va a zero e il picco a uno. Sui
   brani molto compressi (disco, EDM, pop radiofonico) senza questo passaggio
   tutte le barre restano a fondo scala e l'equalizzatore diventa una massa
   piena che non balla.
4. Inviluppo con attacco rapido e rilascio lento: le barre non sfarfallano.
5. Render per frame: gradiente animato a bassa risoluzione ingrandito, alone
   diffuso delle barre disegnato a 1/5 e sfocato, barre nitide sopra, testo e
   barra di avanzamento.
6. I frame RGB vanno per pipe a `ffmpeg`, che li unisce all'audio originale.

## Note per il format

- Il testo sta al 72% dell'altezza: sopra i pulsanti dell'app, sotto
  l'equalizzatore. La colonna destra dell'interfaccia TikTok resta libera.
- Cambia `--preset` fra un post e l'altro ma tieni la stessa impaginazione: e'
  quella che rende il feed riconoscibile.
- Taglia su un tempo forte e su un numero intero di battute: il clip si
  riaggancia da solo quando TikTok lo rimanda in loop. A 126 BPM una battuta
  dura 1,904 s, quindi 16 battute fanno 30,476 s.
- Usa musica di cui hai i diritti, oppure la libreria audio di TikTok.
