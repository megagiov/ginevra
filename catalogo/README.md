# Catalogo START UP®

Da un solo archivio di dati escono due stampati:

| File | Cosa e' | A chi va |
|---|---|---|
| `out/catalogo-licenze.pdf` | 16 pagine, A4 | Aziende che possono prendere una categoria in licenza |
| `out/catalogo-prodotti.pdf` | lookbook A4, 13 pagine | Buyer, negozi, e-commerce |

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
python3 genera.py --finestre   # elenca le foto mancanti e la misura che serve
```

I font (SIL OFL: Zilla Slab, Barlow, IBM Plex Mono) si scaricano da soli in
`font/` alla prima esecuzione. I PDF finiscono in `out/`.

## Dove si mette mano

| Cosa cambiare | Dove |
|---|---|
| Colori, tipografia, testi ricorrenti | `dati/marchio.yml` |
| Le otto categorie, la classe, lo stato della licenza | `dati/categorie.yml` |
| Le linee prodotte, i dati, le referenze | `dati/prodotti.yml` |
| I 33 articoli della gamma tipo | `dati/gamma.yml` |
| Le foto | `foto/`, riconosciute dal nome del file |
| L'impaginazione | `genera.py` |

Nessun testo e' scritto dentro il codice: `genera.py` impagina, i contenuti
stanno nei tre file YAML. Cambiare il colore d'accento in un punto solo
ricolora tutte e venti le pagine.

## Produzione reale e gamma tipo: due cose diverse

Il lookbook ha due sezioni, e la distinzione non e' cosmetica.

**In produzione** (`dati/prodotti.yml`) sono le linee realmente prodotte in
licenza e realmente vendute. Oggi c'e' solo la classe 25 con le calzature mare.

**Gamma tipo** (`dati/gamma.yml`) sono 33 articoli distribuiti sulle otto
classi: una proposta di sviluppo, il punto di partenza per il campionario del
licenziatario. Non sono in produzione, non sono mai stati venduti, e la pagina
di apertura della sezione lo dichiara in chiaro prima degli articoli.

Le due sezioni non si mescolano. Un articolo passa da `gamma.yml` a
`prodotti.yml` solo quando esiste davvero: campionario approvato, produzione
partita. Fino a quel momento resta una proposta, e presentarlo a un
licenziatario come produzione in corso sarebbe un'affermazione falsa.

Per lo stesso motivo il campo `prezzo` della gamma resta **vuoto**: un prezzo su
un articolo mai prodotto e' un numero inventato, e in un catalogo che gira tra i
buyer diventa una trattativa impostata male.

Quello che invece resta ancorato ai fatti anche nella gamma: la forma e i
materiali stanno dentro quello che la classe dichiara sul sito, e il punto di
applicazione del marchio e' quello scritto in `categorie.yml`.

### Aggiungere una linea al lookbook

In `dati/prodotti.yml` c'e' una voce `modello-scheda` con tutti i campi vuoti:
copiala, cambia `id`, metti `pubblica: true` e compila. Il catalogo si allunga
da solo, indice compreso.

### Quando arriva una foto

**Salvala in `foto/` col nome che la finestra vuota dichiara, e rilancia.** Non
c'e' altro da fare: nessun file da aprire, nessun YAML da modificare. La
finestra vuota stampa dentro il nome del file che sta aspettando —
`SU-25-TS-01.jpg` — insieme alla misura in millimetri e in pixel a 300 dpi.

I nomi seguono lo schema:

| Finestra | Nome del file |
|---|---|
| Articolo di gamma | il suo codice: `SU-25-TS-01.jpg` |
| Scheda categoria del catalogo licenze | `categoria-t-shirt.jpg` |
| Apertura di una linea nel lookbook | `linea-calzature-mare.jpg` |
| Immagine di apertura, pagina retail | `apertura.jpg`, `retail.jpg` |

Vanno bene `.jpg`, `.jpeg`, `.png` e `.webp`. Un percorso scritto a mano nel
campo `foto:` ha comunque la precedenza sulla ricerca per nome.

Per avere la lista della spesa completa — cosa manca, come va chiamato e quanti
pixel deve avere:

```bash
python3 genera.py --finestre
```

Non genera niente e non spende niente: impagina su un foglio buttato via solo
per misurare le finestre.

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
- **Il rapporto della finestra deve seguire il prodotto, non la pagina.** Le
  finestre degli articoli erano orizzontali (40 × 32 mm) mentre gli scatti di
  capo misurano 0,88 di larghezza su altezza: il ritaglio a riempimento
  tagliava colletto e orlo. Ora la finestra e' verticale a `RAPPORTO_PRODOTTO`.
- **Un capo bianco su fondo chiaro non si ritaglia per contorno.** I bordi
  sfumano nel fondo e il contorno esce stretto: in una griglia regolare
  conviene prendere la misura mediana degli altri capi e centrarla sulla stessa
  colonna, invece di fidarsi della soglia.
- **La didascalia di una finestra foto stretta deborda.** La misura richiesta
  scritta su una riga sola usciva dai bordi della finestra e finiva sopra la
  colonna accanto: va spezzata su due righe quando non ci sta.
- **Un campo che scende in cascata sotto un altro sfonda la fascia.** Nelle
  schede articolo le taglie erano appese sotto le varianti: con tre righe di
  colori scivolavano oltre il filetto della fascia successiva. Ora sono
  ancorate al fondo della fascia.
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
