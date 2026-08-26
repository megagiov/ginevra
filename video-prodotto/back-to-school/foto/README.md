# Foto per lo spot back to school

Metti qui la foto del prodotto. Una sola cartella, un file per variante colore.

## Come nominare i file

`<slug>-1024x1024.jpg` — lo slug e' il nome della variante in minuscolo, senza
accenti e senza spazi. Esempi: `grigio-1024x1024.jpg`, `nero-1024x1024.jpg`.

Lo stesso slug va poi riportato nella lista `VARIANTS` di `build.py`.

## Cosa serve alla pipeline locale

Lo scontorno di `build.py` lavora per soglia sul bianco e parte dagli angoli:

- **fondo bianco pieno**, uniforme, senza ombra portata attaccata al bordo;
- prodotto **staccato dai quattro bordi** dell'inquadratura;
- quadrata, almeno 1024x1024, JPG o PNG.

Su fondo non bianco lo scontorno esce opaco e il fondo resta attaccato: in quel
caso serve una maschera fatta a parte, non basta cambiare la soglia.

## Se la foto serve invece per una generazione Artlist

Leggi prima `../../ARTLIST.md`. Li' vale la regola opposta: il prodotto passato
come semplice riferimento torna indietro come sosia, quindi si parte dalla
**foto del negozio** con il prodotto fisicamente sugli scaffali.

## Nota

Il `.gitignore` di `video-prodotto/` esclude `*.jpg` e `*.png`: le foto restano
in locale e non finiscono nel repository. E' voluto — qui si versiona la
pipeline, non il materiale.
