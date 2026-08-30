# Spot sneaker con zeppa — pacchetto di generazione

Replica del formato analizzato in `FORMATO-SETTE-GIORNI.md`, con il prodotto
sostituito: sneaker alta con zeppa interna, scamosciata color tortora/talpa,
tre strappi a velcro, punta e talloncino in tessuto piu' scuro, suola bianca.

> **Stato: non generato.** Vedi §4 — tre blocchi aperti.

---

## 1. Cosa si eredita dal riferimento

Della griglia originale resta tutto tranne il prodotto e il conteggio dei
giorni. Il riferimento mostra **sette scarpe diverse**; qui il prodotto e' uno
solo, quindi la struttura "sette giorni" non regge: non si possono riempire
sette stacchi con la stessa scarpa senza che sembri un errore di montaggio.

**Adattamento:** stessa scenografia, stessa camera, stessa luce, ma la
progressione diventa **una sola scarpa vista in posizioni successive** invece
che sette prodotti. Le durate decrescenti restano.

| Elemento | Valore ereditato dal riferimento |
|---|---|
| Formato | 9:16 verticale |
| Camera | bloccata, a terra, altezza caviglia |
| Movimento camera | **nessuno** — ne' pan, ne' zoom, ne' carrello |
| Inquadratura | dal ginocchio in giu', volto mai visibile |
| Fondo | parete chiara a sinistra, tenda bianca a velo a destra |
| Pavimento | laminato rovere chiaro, fughe diagonali |
| Luce | naturale diffusa laterale, ombre morbide e corte |
| Styling | jeans dritti a caviglia scoperta |
| Audio | nessun parlato |
| Testo | sovrimpressione aggiunta in post, non generata |

**Differenza obbligata:** il riferimento ha il piede nudo nel tacco. Con una
sneaker alta il collo del piede e' coperto: il gesto di "sollevare il tallone e
puntare la punta" non e' replicabile. Si sostituisce con uno spostamento di peso
e una rotazione della caviglia.

---

## 2. Parametri di generazione

Server: **Artlist** (horacle non raggiungibile, vedi §4).

| | |
|---|---|
| Modello | `3010` — ByteDance Seedance 2.5 I2V 480p |
| `modelGroupId` | 515 |
| `aspect_ratio` | `9:16` |
| `resolution` | `480p` |
| `duration` | `10` |
| `generate_audio` | `false` |
| `input` | `{ assetId }` della foto prodotto caricata |

**480p e non 1080p:** ARTLIST.md §1 — il 1080p costa cinque volte tanto e
TikTok ricomprime comunque. A 10.000 crediti per 10 s il 1080p e' inoltre fuori
budget: il saldo e' 3.740.

**`generate_audio: false`:** l'audio del riferimento e' una base musicale a
-35,9 LUFS, si aggiunge in post. Generarlo e' spesa inutile e rischia parlato
non richiesto.

### Costo

Il gate di conferma scatta sopra soglia e **non spende nulla**: restituisce il
prezzo esatto da riportare prima di procedere (ARTLIST.md §1). Riferimento
misurato in sessioni precedenti: **200 crediti/secondo a 480p**, cioe' circa
**2.000 crediti per 10 s** — oltre meta' del saldo disponibile per tentativo.

Non e' stato possibile ottenere la quotazione esatta in anticipo: Artlist
richiede un asset gia' caricato per quotare un image-to-video.

---

## 3. Prompt

Da passare con la foto prodotto come `input`.

```
Static locked-off camera positioned on the floor at ankle height, never moving:
no pan, no tilt, no zoom, no dolly. Framing shows only a woman's lower legs from
the knee down, seen from the side. She wears straight-leg denim jeans with the
hem breaking just above the ankle.

She is wearing the exact wedge sneakers from the reference image. Keep the shoes
completely unchanged: identical taupe suede upper, identical three hook-and-loop
straps, identical darker toe cap and heel tab, identical white sole and internal
wedge, identical proportions and stitching. Do not restyle, recolour, reshape or
redesign the shoes in any way. Do not add any brand name, logo, lettering, tag
or marking anywhere on the shoes.

Background: a plain pale off-white wall on the left, floor-to-ceiling sheer white
voile curtain on the right, grey skirting board along the base. Floor: light oak
laminate planks with visible seams running diagonally away from camera. Soft
diffused natural daylight from the side, short soft shadows, no artificial
lighting, no lens flare.

Motion: she stands still, then slowly shifts her weight from one foot to the
other and rotates the ankle slightly. Small, calm, natural movement only. The
shoes stay fully in frame at all times and never approach the lens.

Photorealistic, shot on a phone resting on the floor. No text, no captions, no
graphics, no watermarks, no on-screen writing of any kind. No extra objects, no
added props, no visual effects.
```

**Note sul prompt**, dai difetti verificati in ARTLIST.md §2:

- Il divieto sui marchi inventati e' scritto esplicitamente. **Riduce la
  frequenza, non la elimina** — sono comparsi marchi falsi tre volte su tre.
- Il vincolo "mai avvicinare il prodotto all'obiettivo" e' ripetuto perche' e'
  gia' stato disatteso in passato.
- Il divieto di testo a schermo serve a tenere pulita la sovrimpressione, che va
  aggiunta in post con la pipeline locale.

---

## 4. Blocchi aperti

### 4.1 horacle non e' raggiungibile
Il server MCP horacle risulta disconnesso in questa sessione: nessuno dei suoi
tool risponde. La richiesta era di usare solo horacle. Le alternative con
generazione video sono Artlist e Higgsfield.

### 4.2 Higgsfield e' inutilizzabile
Saldo **0,5 crediti**, piano free. Non copre nessuna generazione video.

### 4.3 L'immagine allegata non arriva ai tool remoti
La foto del prodotto e' stata allegata in chat, ma i server MCP remoti non
possono leggere gli allegati della conversazione e il file non e' sul
filesystem. Serve che il prodotto arrivi ad Artlist per una di queste vie:

- un **URL pubblico** della foto (da passare a `upload_image` con `imageUrl`);
- il **file su disco** in questa sessione, da caricare con `upload_image` +
  `confirm_upload`;
- il pannello `upload_widget`, che pero' **non funziona in Claude Code** — la
  documentazione del tool indica esplicitamente di usare `upload_image` nei
  client senza pannelli interattivi.

---

## 5. Il problema di fedelta', da mettere in conto

La richiesta e' "mantieni il prodotto originale al 100%, non alterare forma,
design, colori o logo". **Questo requisito non e' raggiungibile per
costruzione** con image-to-video, ed e' gia' documentato in ARTLIST.md §2:

> Passare la foto del prodotto come semplice riferimento non funziona: il
> modello produce una sosia. Alla prova, una sneaker con tre strappi, finestre
> ritagliate e suola gum sottile e' tornata indietro come stivaletto con due
> strappi e platform carrarmato.

Il prodotto di questo spot e' **una sneaker con tre strappi**: la stessa
categoria del caso di fallimento gia' pagato.

### Le tre strade

1. **Generare e ispezionare.** ~2.000 crediti a tentativo su 3.740 disponibili,
   cioe' un tentativo e mezzo. Ogni output va ispezionato a piena risoluzione
   prima di consegnarlo, strappo per strappo. Probabilita' realistica di
   ottenere il prodotto fedele al 100%: bassa.

2. **Girarlo col telefono.** Il formato e' stato scelto proprio perche' non
   richiede generazione: camera bloccata a terra, luce di finestra, jeans e
   pavimento chiaro. Il prodotto in campo e' quello vero, quindi la fedelta' e'
   totale per definizione, e il costo e' zero crediti. Vedi la checklist in
   `FORMATO-SETTE-GIORNI.md` §7.

3. **Ibrido.** Generare o girare solo la scena (gambe, jeans, fondo, luce) e
   comporre il prodotto reale in post. Con camera bloccata e movimento minimo la
   composizione e' molto piu' semplice che su una ripresa mossa — ma resta
   lavoro di rotoscopia sul piede.

Se l'obiettivo e' davvero la fedelta' al 100%, **la strada 2 e' l'unica che la
garantisce**. La strada 1 puo' produrre un buon video, ma di una scarpa che
somiglia a quella vera senza esserlo.
