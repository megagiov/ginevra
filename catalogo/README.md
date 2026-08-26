# Catalogo START UP®

Da un solo archivio di dati escono due stampati:

| File | Cosa e' | A chi va |
|---|---|---|
| `out/catalogo-licenze.pdf` | 16 pagine, A4 | Aziende che possono prendere una categoria in licenza |
| `out/catalogo-prodotti.pdf` | lookbook A4, cresce con le linee | Buyer, negozi, e-commerce |

Gira tutto in locale: nessun servizio a pagamento, nessuna API, nessun credito.
Il marchio finisce nel PDF come **tracciato vettoriale**, non come immagine:
si stampa nitido a qualunque formato e si ricolora senza rigenerare nulla.

## Come si usa

```bash
pip install reportlab PyYAML pillow

python3 genera.py              # tutti e due i cataloghi
python3 genera.py licenze      # solo il catalogo licenze
python3 genera.py prodotti     # solo il lookbook
python3 genera.py --anno 2027  # cambia l'anno in copertina
```

I font (SIL OFL: Zilla Slab, Barlow, IBM Plex Mono) si scaricano da soli in
`font/` alla prima esecuzione. I PDF finiscono in `out/`.

## Dove si mette mano

| Cosa cambiare | Dove |
|---|---|
| Colori, tipografia, testi ricorrenti | `dati/marchio.yml` |
| Le otto categorie, la classe, lo stato della licenza | `dati/categorie.yml` |
| Le linee prodotte, i dati, le referenze | `dati/prodotti.yml` |
| Le foto | `foto/`, richiamate dal campo `foto:` |
| L'impaginazione | `genera.py` |

Nessun testo e' scritto dentro il codice: `genera.py` impagina, i contenuti
stanno nei tre file YAML. Cambiare il colore d'accento in un punto solo
ricolora tutte e venti le pagine.

### Aggiungere una linea al lookbook

In `dati/prodotti.yml` c'e' una voce `modello-scheda` con tutti i campi vuoti:
copiala, cambia `id`, metti `pubblica: true` e compila. Il catalogo si allunga
da solo, indice compreso.

### Quando arriva una foto

Mettila in `foto/` e scrivi il nome nel campo `foto:`. Finche' non c'e', la
pagina si stampa lo stesso con una finestra che dichiara la misura richiesta in
millimetri e in pixel a 300 dpi: sono le specifiche da passare al fotografo.

## Regole di contenuto

Valgono anche qui le regole del `CLAUDE.md` di progetto:

- **Nessuna affermazione inventata.** Ogni riga dei file `dati/` viene dalle
  pagine pubblicate su startupmoda.com o dall'utente, e la fonte e' annotata
  nel file. Un dato non verificato si lascia vuoto e resta vuoto anche in
  stampa.
- **Prezzi, taglie e numeri si riverificano prima di ogni stampa.** Sono i
  primi a invecchiare.
- I contatti in `dati/marchio.yml` sono **vuoti**: il sito non li espone. Vanno
  compilati prima di mandare il catalogo a un licenziatario.

## Trappole gia' pagate

- **La spaziatura tra lettere resta attaccata al canvas.** In reportlab
  `setCharSpace` non si azzera da solo quando finisce il blocco di testo: il
  valore usato per un'etichetta si trascinava su tutti i paragrafi successivi e
  li allargava del 27%, mandandoli oltre il margine destro senza che nessun
  errore lo segnalasse. Ora `scrivi()` dichiara sempre la spaziatura, anche a
  zero.
- **`setCharSpace` non esiste sul canvas**, solo sull'oggetto testo
  (`beginText`). Sul canvas la chiamata solleva `AttributeError`.
- **Due colonne affiancate scendono a velocita' diverse.** Il blocco che viene
  dopo va agganciato alla piu' bassa delle due, non a una quota fissa,
  altrimenti si sovrappone: nel lookbook la gamma prodotto finiva sopra la
  colonna dei dati.
- **Le pagine con pochi elementi restano vuote a meta'.** Il passo verticale
  degli elenchi si calcola sull'altezza disponibile (`passo()`), non a
  millimetri fissi.
- **Le foto vanno riempite e tagliate, non adattate.** Con
  `preserveAspectRatio` restano bande vuote dentro la finestra e in un catalogo
  si vedono tutte. Il ritaglio si fa con un tracciato di clip, senza toccare il
  file sorgente.
- **I font statici di Google Fonts non stanno tutti nel ramo `main`.** Molte
  famiglie hanno ormai solo il variabile, che reportlab incorpora rendendo la
  sola istanza Regular: Zilla Slab, Barlow e IBM Plex Mono sono state scelte
  anche perche' i file statici esistono davvero.

## Il marchio

`dati/bollo.json` contiene i tracciati del bollo circolare estratti da
`LOGOCLASSICO.ai`, in coordinate normalizzate: si disegna a qualunque misura e
in qualunque colore con `BOLLO.disegna()`. Gli stessi tracciati, esportati come
file, stanno in `../brand/logo/`.

**Manca il lettering orizzontale** (`STARTUP` + `MADE IN ITALY`): il file .ai
consegnato contiene solo il bollo. Quando arriva il vettoriale del lettering va
aggiunto qui e usato in copertina.
