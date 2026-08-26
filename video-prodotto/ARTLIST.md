# Artlist — quaderno di bordo GM Vegasi

Tutto quello che segue e' **misurato**, non stimato: ogni numero viene da una
generazione realmente pagata, ogni difetto da un output realmente uscito male.
Aggiornare questo file ogni volta che si scopre qualcosa di nuovo.

---

## 1. Costi reali

| Cosa | Costo |
|---|---|
| Video Seedance 2.5, immagine→video 9:16, **480p** | **200 crediti al secondo** (8 s = 1.600, 10 s = 2.000) |
| Stesso video a **1080p**, 10 s | **10.000** |
| Voce ElevenLabs Multilingual v2, copione da ~10 s | **29** |
| Stessa voce, frase da ~4 s | **11** |
| Immagine Nano Banana 2, ritocco 2K | **130** |
| Creazione e modifica di uno style kit | **gratis** |

**Il formato non incide sul prezzo.** 1:1, 9:16 e 16:9 costano uguale. Le uniche
leve sono **durata** e **risoluzione**. Il 1080p costa cinque volte il 480p: per
Instagram e TikTok, che ricomprimono comunque, il 480p e' sufficiente.

### Il gate del costo, e quando non scatta

Le generazioni costose restituiscono `confirmation_required` **senza spendere
nulla**: e' l'occasione per riportare il prezzo esatto all'utente e aspettare.

Ma sotto una certa soglia il gate **non scatta e la generazione parte subito**.
Verificato: 11, 29 e 130 crediti sono partiti da soli; 1.600, 2.000 e 10.000
hanno aperto il gate. Per le generazioni piccole quindi non c'e' rete di
protezione: vanno annunciate prima o rendicontate subito dopo.

Per conoscere un prezzo senza spendere basta lanciare la chiamata e leggere il
gate — ma solo se si e' sopra soglia, altrimenti si paga davvero.

---

## 2. Difetti dei modelli, verificati sul campo

### Il prodotto viene reinventato
Passare la foto del prodotto come semplice riferimento **non funziona**: il
modello produce una sosia. Alla prova, una sneaker con tre strappi, finestre
ritagliate e suola gum sottile e' tornata indietro come stivaletto con due
strappi e platform carrarmato.

**Cosa funziona:** partire dalla **foto del negozio** dove il prodotto e'
fisicamente sugli scaffali. Cosi' il prodotto in campo e' fotografato, non
generato, e resta fedele.

### I marchi inventati
Il modello stampa nomi di marca inesistenti sui prodotti — sulla linguetta, sul
fianco, sulla punta. **E' successo tre volte su tre**, anche col divieto scritto
esplicitamente nel prompt. Il divieto riduce la frequenza, non la elimina.

**Conseguenza operativa:** ogni video va ispezionato a piena risoluzione prima
della consegna. Un marchio inventato su un'inserzione commerciale non e' un
dettaglio estetico.

### L'italiano parlato e' inaffidabile
Errori raccolti: *venduto→venditi*, *finiture→finituri*, *sfuggire→sfiggere*,
*fortissimo→fortemissimo*, *zeppa→zecca*, *prezzo→prezio*, *Ferma→Fermo*.

**L'ipotesi "parole piu' semplici" e' stata verificata ed e' falsa.** "Zeppa" e
"fortissimo" sono elementari e le ha sbagliate lo stesso. E "zecca" non e' una
storpiatura: e' un'altra parola italiana. Sbaglia in modo diverso a ogni
tentativo — nello stesso identico copione una volta ha detto "zeppa" giusto e
la volta dopo no.

**Regola:** i claim commerciali non si fanno pronunciare. Vanno a schermo.

### La traccia audio allegata viene ignorata
Passare un file vocale come riferimento con la generazione audio attiva non
produce sincronia labiale sulla propria voce: il modello si inventa il parlato
lo stesso. Verificato confrontando gli inviluppi: correlazione 0,06.

### Le istruzioni di inquadratura vengono disattese
"Mai avvicinare il prodotto all'obiettivo" e' stato ignorato: scarpa incollata
alla lente e presentatrice tagliata fuori dal bordo. Ripetere il vincolo in piu'
punti del prompt aiuta ma non garantisce.

### Nano Banana 2 allarga il quadro
Il formato predefinito e' 16:9 **anche partendo da un'immagine verticale**: il
modello estende la scena e si inventa lo sfondo. Passare **sempre**
`aspect_ratio` esplicito e scrivere nel prompt di non estendere ne' inventare
parti della scena.

---

## 3. Voce

Impostare **sempre** la lingua su italiano: il valore predefinito resta inglese
anche quando il testo e' palesemente italiano.

Voce scelta dall'utente: **Grounded**, timbro adulto e caldo. Provate e
scartate: Everyday, Bright, Flair.

Durate del copione standard con Grounded: **8,80 s a velocita' 1,0**, **10,03 s
a 0,9**. La velocita' nativa e' preferibile a qualunque manipolazione
successiva.

Il sintetizzatore locale gratuito (Piper) elide una consonante — dice
"lasciatelo" per "lasciartelo". Usarlo solo per prove, non per la consegna.

---

## 4. Sostituire il parlato in un video generato

Il metodo e i motivi stanno nel README. Le due regole che contano:

- **Non deformare mai l'audio.** Stirare i segmenti per inseguire il labiale
  misura bene (53 ms di scarto) ma suona male: la velocita' che cambia in
  continuazione si sente come tono instabile. L'utente l'ha respinto.
- **Tagliare solo dentro i silenzi veri**, misurati sull'onda. Tagliare a filo
  di parola ne mangia la coda e il risultato sembra balbuziente.

---

## 5. Il prodotto

**Sneakers Donna Isa — BELLAMICA, cod. RA159I26.** Taglie 36-41,
autunno-inverno. Cinque colori: grigio, beige, marrone, bordeaux, nero.

- La scheda del sito **non dichiara i materiali**. Scrivere "effetto camoscio",
  mai "scamosciato": e' un'affermazione sulla composizione che non e'
  verificabile.
- La **suola gum e' reale solo su grigio, beige e nero**. Su marrone e bordeaux
  e' in tinta: li' l'etichetta parla della zeppa interna.
- Prezzo sul sito: **23,00 €**. Nelle inserzioni l'utente usa **28,00 €
  spedizione inclusa**. Lo scarto e' voluto, ma va riverificato prima di ogni
  pubblicazione: annuncio e pagina di destinazione che dicono cifre diverse
  possono essere contestati in fase di review.

---

## 6. Grafica e sicurezza dei margini

Il file montato dall'utente e' **1080x1920 a 60 fps, incorniciato**: l'immagine
occupa le righe 241-1679, sopra e sotto restano due bande nere.

- **Non mettere testo nella banda inferiore.** E' esattamente dove TikTok e
  Instagram sovrappongono didascalia, nome utente e pulsanti. Il testo va dentro
  l'immagine, con una velatura scura sotto per la leggibilita'.
- Il montaggio dell'utente ha un **lampo bianco a 7,7-7,85 s** nella transizione:
  la zona del prezzo arriva a 254 su 255. Chiudere le sovrimpressioni **prima**,
  a 7,62.
- L'**end card GM Vegasi TikTok Shop** occupa da 8,0 s alla fine e non va
  toccata: la call to action c'e' gia'. Eventuali sottotitoli li' vanno **sotto
  il logo**, non sopra.
- Colori coordinati all'end card: bianco, rosa `#FE2C55`, ciano `#25F4EE`.
- Anticipare di mezzo secondo il sottotitolo del richiamo all'azione: l'occhio
  legge, poi l'orecchio conferma.

---

## 7. Gli style kit gia' pronti

Quattro kit stagionali, uno per look, tutti con la stessa presentatrice:

- **GM Vegasi — Presentatrice Inverno** (camicia azzurra)
- **GM Vegasi — Presentatrice Estate** (canotta bianca)
- **GM Vegasi — Presentatrice Mezza Stagione** (maglia crema)
- **GM Vegasi — Presentatrice Street** (felpa grigia)

Ognuno contiene il look, la foto del negozio e le regole scritte di ripresa.

**Un kit per stagione, non un kit unico:** le immagini di un kit si fondono tutte
nella generazione, quindi quattro vestiti diversi nello stesso kit darebbero al
modello segnali contraddittori su cosa far indossare alla presentatrice.

I kit alzano molto la probabilita' che sia la stessa persona ma **non la
garantiscono**: la somiglianza e' buona, non fotografica. E il divieto sui
marchi inventati scritto nelle regole **e' un'istruzione, non un lucchetto**.

---

## 8. Regole editoriali

- I claim sono **solo quelli forniti dall'utente**, parola per parola. Non
  rafforzarli, non dedurne altri.
- La presentatrice e' una **dimostratrice**: non e' una cliente, non e' una
  dipendente reale. Non puo' dire di aver comprato o usato il prodotto, ne'
  raccontare risultati o esperienze.
- Il contenuto va etichettato come pubblicitario del negozio.
- Superlativi assoluti come "il piu' venduto del web" sono dell'utente e restano
  suoi; vanno segnalati una volta perche' in advertising a pagamento possono
  richiedere di essere sostanziati.
