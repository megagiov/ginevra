# Maschera pubblicitaria per LDV corriere — GM Vegasi

Scarichi la LDV dal corriere come sempre, lanci uno script, ed esce un unico
PDF con l'etichetta originale **e** i due badge TikTok Shop già dentro,
piccoli e centrati come coppia in fondo al foglio. Si stampa una volta sola,
esattamente come si stampava prima il PDF del corriere — nessun doppio
passaggio in stampante.

## Come è nata la misura

Il layout è calcolato su una LDV **GLS** reale (105,0 × 148,2 mm, il classico
foglio adesivo "10x15"): il blocco etichetta — intestazione mittente, città,
barcode, riga GLS — arriva fino a circa 86 mm dall'alto. `maschera-10x15.html`
lascia libera una fascia di 90 mm (5 mm di margine di sicurezza) e mette i
due badge piccoli (14,4mm di altezza ciascuno) in fondo ai restanti ~58 mm,
centrati come coppia, il più lontano possibile dalla zona che il laser del
corriere legge sopra.

**Se usi anche altri corrieri** (BRT, SDA/Poste, ecc.) l'etichetta può avere
un'impaginazione diversa: manda un PDF di esempio così misuro dove cade lo
spazio bianco su quel formato, oppure prova `--zona-ldv` (vedi sotto) e
controlla il risultato prima di stampare in serie.

## Installazione

```bash
pip install PyMuPDF playwright
playwright install chromium
```

## Uso

```bash
python3 applica_maschera.py etichetta.pdf
# crea etichetta_brandizzato.pdf nella stessa cartella

python3 applica_maschera.py etichetta.pdf -o pronta_da_stampare.pdf

# se un corriere diverso da GLS lascia uno spazio bianco più o meno alto:
python3 applica_maschera.py etichetta.pdf --zona-ldv 94
```

Poi si stampa `*_brandizzato.pdf` così com'è, invece del PDF originale del
corriere.

### Impostazioni di stampa

Quando mandi in stampa `*_brandizzato.pdf`, nella finestra di stampa:

- formato carta: quello che usi già per le LDV (105×148mm / "10x15" /
  l'etichetta adesiva dedicata) — il PDF ha già quella dimensione esatta,
  presa dal PDF del corriere;
- scala: **100% / dimensioni reali**, mai "adatta alla pagina" — altrimenti
  rimpicciolisce o ingrandisce tutto, badge compresi, e può disallineare il
  barcode;
- colore: indifferente, il contenuto è già bianco/nero puro.

### Come funziona sotto il cofano

`maschera-10x15.html` è la grafica del logo/badge, con la parte in alto
lasciata volutamente **trasparente** (non bianca): se avesse uno sfondo
bianco coprirebbe l'etichetta invece di lasciarla intravedere. Lo script:

1. legge le dimensioni reali della pagina del PDF scaricato;
2. genera da `maschera-10x15.html` un overlay delle stesse dimensioni
   (Playwright/Chromium headless);
3. fonde l'overlay sopra ogni pagina del PDF originale (PyMuPDF), pixel
   dove c'è grafica, trasparente altrove;
4. salva il risultato come nuovo PDF.

## I loghi

Cartella `loghi/`, tutti convertiti in bianco/nero puro (niente sfumature di
grigio) perché la stampa è in bianco e nero — vedi `loghi/README.md` per come
sono stati ottenuti dai file a colori originali:

- `gm-vegasi-tiktokshop.png` — badge borsa+cartellino (in uso)
- `gm-vegasi-tiktokshop-wordmark.png` — badge scritta "TikTok Shop" (in uso)
- `gm-vegasi-logo.png` — logo GM Vegasi da solo (non usato al momento, tenuto
  per un utilizzo futuro)

## Personalizzare

| Cosa cambiare | Dove |
|---|---|
| Altezza fascia LDV | argomento `--zona-ldv` (mm), oppure `--zona-ldv` di default in `applica_maschera.py` |
| Dimensione dei badge | `.badge-tiktokshop, .badge-tiktokshop-wordmark` in `maschera-10x15.html` (proprietà `height`, ora 14,4mm per entrambi) |
| Spazio fra i due badge | `.zona-brand { gap: ... }` in `maschera-10x15.html` |
| Distanza dal bordo inferiore | `.zona-brand { padding-bottom: ... }` in `maschera-10x15.html` |
| I badge stessi | sostituisci i file in `loghi/`, oppure aggiorna i percorsi `src=` nell'HTML |

## Controllare la grafica da sola

`maschera-10x15.html` si apre anche direttamente nel browser (mostra il
logo/badge su una pagina 105×148mm, con la fascia alta vuota). Per vedere
anche la riga guida di allineamento — utile solo per un controllo visivo,
va sempre tenuta spenta nell'output finale — apri il file con la classe
`guida` aggiunta al tag `<body>`.
