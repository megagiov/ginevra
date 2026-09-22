# Da completare prima di pubblicare

Elenco chiuso: finche' restano voci aperte, il sito e' pronto tecnicamente ma
non ancora pubblicabile. Tutti i valori stanno in `sito/content.py`, nel
dizionario `AZIENDA`, salvo dove indicato diversamente.

## 1. Obbligatori per legge

| Campo | Stato | Dove |
| --- | --- | --- |
| Partita IVA | vuota | `AZIENDA["piva"]` |
| Ragione sociale | vuota, si usa il nome commerciale | `AZIENDA["ragione_sociale"]` |

Finche' questi campi restano vuoti il sito **non mostra alcun segnaposto**: la
riga si accorcia e basta, quindi il sito e' gia' presentabile in anteprima.
Ma la P.IVA deve comparire prima della pubblicazione: per un'attivita' con
partita IVA, indicarla sul sito e' un obbligo di legge (art. 35 DPR 633/1972 e
art. 7 D.Lgs. 70/2003), e va scritta nel footer di ogni pagina e
nell'informativa privacy. Il posto da cui recuperarla, se non l'avete sotto
mano: una qualunque fattura emessa, la visura camerale, oppure il servizio di
ricerca sul sito dell'Agenzia delle Entrate partendo dal nome dell'impresa.

La ragione sociale serve anche come titolare del trattamento
nell'informativa privacy: finche' manca, l'informativa indica "Sorgente
Traslochi".

`python3 build.py` elenca a ogni generazione i campi ancora vuoti, cosi' non
si pubblica per distrazione senza averli riempiti.

## 2. Necessari perche' il sito funzioni

| Cosa | Stato | Come si risolve |
| --- | --- | --- |
| Coordinate geografiche | Approssimate sul CAP 80144 | `AZIENDA["lat"]` / `["lon"]`: prendi i valori esatti da Google Maps (clic destro sul punto, prima voce) |

Il modulo preventivo e' collegato al form Formspree `mvkgajzy`, che recapita a
sorgentetraslochi@gmail.com. Al primo invio in assoluto Formspree manda una
mail di conferma con un pulsante da cliccare: finche' non lo si clicca, le
richieste non arrivano. Fate quindi un invio di prova appena il sito e'
online.

Gli orari (lunedi' - sabato, 8:00 - 18:00) sono gia' inseriti: compaiono nel
footer, nella pagina preventivo e nei dati strutturati
(`openingHoursSpecification`). Se cambiano, vanno aggiornati in due punti di
`content.py`: `AZIENDA["orari"]` per il testo e `ORARI_SCHEMA` per Google.

Ricordatevi di mettere gli stessi orari anche sulla scheda Google Business:
se i due non coincidono, Google se ne accorge.

Il piano gratuito di Formspree non accetta allegati: per questo il modulo non
ha il campo foto, e al suo posto c'e' un invito a mandare le immagini su
WhatsApp o via email. E' l'unica deviazione rispetto alle specifiche, ed e'
voluta: un campo file sul piano gratuito farebbe fallire l'invio.

## 3. Da confermare con l'azienda

Due informazioni sono state usate nei testi ma erano segnate come da
confermare. Se una delle due non e' esatta va corretta prima della
pubblicazione, perche' compare in evidenza.

1. **"Dal 1965"** — usato nell'H1 della home, nel filo conduttore di chi siamo
   e nei dati strutturati (`foundingDate`). Se l'anno esatto e' un altro si
   cambia in `content.py` (cerca `1965`) e in `schema_azienda()` di
   `build.py`.
2. **Servizio di deposito mobili** — la pagina `/deposito-mobili-napoli/`
   esiste e descrive un servizio di custodia temporanea. Se il deposito non
   viene effettivamente offerto, vanno tolti: la voce da `SERVIZI` e da `NAV`
   in `content.py` e il blocco `SERVIZIO_DEPOSITO` da `PAGINE_SERVIZIO`. Il
   resto del sito si riallinea da solo al prossimo `python3 build.py`.

## 4. Contenuti che migliorano la resa

Non bloccano la pubblicazione, ma il sito rende molto di piu' con questi:

- **Foto reali** al posto dei segnaposto (vedi README, sezione Immagini). Le
  piu' utili: squadra e mezzo, un montaggio in corso, un furgone carico, una
  casa svuotata dopo uno sgombero.
- **Recensioni Google**: nella home ci sono due segnaposto. Vanno sostituiti
  con recensioni reali prese dalla scheda Google, citando nome e data.
  Non inventarle: le recensioni false sono pubblicita' ingannevole.
- **Immagine di anteprima social**: `dist/og-sorgente-traslochi.png` e' ora un
  rettangolo nei colori aziendali. Sostituiscila con una foto reale
  1200 x 630 px (e' l'immagine che compare quando il link viene condiviso su
  WhatsApp o Facebook).

## Cosa non e' stato inventato

Nel sito non compaiono prezzi, certificazioni, coperture assicurative, numero
di dipendenti, numero di traslochi svolti, anni di garanzia o qualunque altro
dato non fornito. Dove serviva un numero e non c'era, la frase e' stata
scritta senza. Se volete aggiungerne (per esempio l'assicurazione sulle merci
trasportata), bastano i dati reali e li inseriamo.
