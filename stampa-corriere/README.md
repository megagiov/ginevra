# Maschera pubblicitaria per LDV corriere — GM Vegasi

Scarichi la LDV dal corriere come sempre, lanci uno script, ed esce un unico
PDF con l'etichetta originale **e** i due badge TikTok Shop già dentro,
piccoli e centrati come coppia in fondo al foglio. Si stampa una volta sola,
esattamente come si stampava prima il PDF del corriere — nessun doppio
passaggio in stampante.

## Dove finiscono i badge

Non c'è una misura fissa, perché ogni corriere impagina la LDV a modo suo.
Lo script decide leggendo la pagina, in quest'ordine:

1. **Se la pagina è più corta dell'etichetta fisica 10x15, la allarga.** Una
   LDV Poste Delivery Business è 114×104mm: portata a 148mm restano 34mm di
   striscia pulita sul lato lungo, e i badge vanno lì, impilati.
2. **Altrimenti cerca il riquadro bianco più in basso.** Una LDV GLS
   105×148mm lascia libero il fondo: lì i badge stanno affiancati a 14,4mm,
   lontani dai barcode.
3. **Se non c'è spazio, lascia la pagina intatta.** Meglio un'etichetta senza
   badge che una con i badge sopra la lettera di vettura.

Verificato su LDV reali GLS (2 esemplari) e Poste Delivery Business. Se un
altro corriere dà un risultato storto, mandami quel PDF: il caso si aggiunge.

## Installazione

Su Windows: doppio click su `installa.bat`, che installa le librerie, scarica
Chromium e verifica che tutto parta. Richiede che Python sia già installato
(da python.org).

A mano, o fuori da Windows:

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

### Automatico: sorveglia i Download da solo

`avvia_osservatore.bat` è il modo con meno passaggi: lo apri una volta,
lasci quella finestra aperta, e da quel momento ogni LDV che scarichi da un
corriere (finisce nei Download come sempre) viene brandizzata da sola e si
apre già pronta per Ctrl+P — non devi più trascinare né lanciare niente per
ogni spedizione.

Quali PDF tocca e quali no:

- **automatico** — i PDF che il gestionale nomina come
  `49313-1-1-20260916143218.pdf` (numero spedizione, due contatori, data e
  ora a 14 cifre): riconosciuti da soli, non devi rinominare niente;
- **a mano** — qualsiasi altro PDF che rinomini mettendoci dentro la parola
  `ldv`, per le volte che ti serve brandizzarne uno fuori dal solito giro;
- **mai** — tutto il resto, più qualsiasi file con una pagina troppo grande
  per essere un'etichetta (oltre 200mm di lato): così se il gestionale nomina
  allo stesso modo anche fatture o DDT in A4, quelli restano fuori.

I due criteri sono in `osserva_cartella.py` (`NOME_GESTIONALE` e
`PAROLA_MANUALE`): se un giorno il gestionale cambia il formato dei nomi,
si aggiorna lì.

Per fermarlo, chiudi la finestra. Se vuoi che riparta da solo ogni volta che
accendi il PC, metti un collegamento a `avvia_osservatore.bat` nella cartella
di avvio di Windows (tasto Windows+R, scrivi `shell:startup`, Invio, e
trascina lì il collegamento).

### Trascina-e-rilascia, un file alla volta

Se preferisci decidere file per file invece di lasciare la sorveglianza
sempre accesa: `stampa_brandizzata.bat` fa lo stesso lavoro ma solo quando
trascini un PDF sopra la sua icona.

Entrambi richiedono comunque l'installazione una tantum di
Python/PyMuPDF/Playwright descritta sopra, e che `py` sia disponibile da riga
di comando (l'installer di Python lo mette sul PATH di default).

Nessuno dei due stampa da solo: aprono il risultato e la stampa la lanci tu,
così hai sempre modo di controllarlo prima — o di chiudere senza stampare se
quella volta non ti serve la versione brandizzata.

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
| Dimensione dei badge affiancati | `BADGE_H_MM` in `applica_maschera.py` (ora 14,4mm) |
| Dimensione dei badge impilati | `BADGE_W_MAX_MM` in `applica_maschera.py` (ora 32mm) |
| Spazio fra i due badge | `GAP_BADGE_MM` in `applica_maschera.py` |
| Aria fra badge e contenuto | `MARGINE_MM` in `applica_maschera.py` |
| Misura dell'etichetta fisica | `ETICHETTA_LATO_CORTO_MM` / `ETICHETTA_LATO_LUNGO_MM` in `applica_maschera.py` |
| I badge stessi | sostituisci i file in `loghi/`, oppure aggiorna i percorsi `src=` nell'HTML |

## Controllare la grafica da sola

`maschera-10x15.html` si apre anche direttamente nel browser (mostra il
logo/badge su una pagina 105×148mm, con la fascia alta vuota). Per vedere
anche la riga guida di allineamento — utile solo per un controllo visivo,
va sempre tenuta spenta nell'output finale — apri il file con la classe
`guida` aggiunta al tag `<body>`.
