# Spot 5 s — "Squat & Rise" (Seedance 2.5, senza audio)

Formato richiesto dall'utente: **5 secondi, 9:16, nessun audio, nessuna voce**.
Il prodotto e' indossato da una modella che scende in squat e si rialza.

---

## 1. Costo (preventivo Artlist, nessun credito speso)

Seedance 2.5 image-to-video, 5 s, 9:16, `generate_audio: false`:

| Risoluzione | Crediti |
|---|---|
| 480p | **1.000** |
| 720p | **2.500** |
| 1080p | **5.000** |

Coerente con i 200 crediti/secondo a 480p gia' misurati in `ARTLIST.md`.
Il formato non incide: incidono solo durata e risoluzione.

Saldo al momento del preventivo: **3.740 crediti** (piano AI Suite 16500, rinnovo
26/09). Il 1080p da solo **non e' coperto** dal saldo.

**Consigliata: 480p.** TikTok ricomprime comunque, e a 1.000 crediti restano
margini per un secondo tentativo — che serve, vedi sezione 3.

### Gate del costo
In `ARTLIST.md` risultano: 130 crediti partiti da soli, 1.600 hanno aperto il
gate. **1.000 e' in mezzo e non e' mai stato verificato**: non si sa se il gate
scatti. Va quindi annunciato prima, non lasciato al gate.

---

## 2. Piano di produzione consigliato (due passaggi, 1.130 crediti)

Generare direttamente il video dalla foto del prodotto **non funziona**: e' il
difetto numero uno registrato in `ARTLIST.md`, e proprio su questa sneaker
(tre strappi, finestre ritagliate, suola sottile → tornata indietro come
stivaletto con due strappi e platform carrarmato).

Con la modella in squat il rischio peggiora: il prodotto e' piccolo nel quadro,
in movimento e lontano dal riferimento — la condizione in cui il modello
reinventa di piu'.

| # | Passo | Strumento | Crediti |
|---|---|---|---|
| 0 | Caricare la foto prodotto originale | `upload_image` | 0 |
| 1 | **Fotogramma di partenza**: modella nella posa di squat, con la scarpa del riferimento montata sul piede | Nano Banana 2 **1K**, `aspect_ratio: "9:16"` esplicito | 90 |
| 2 | **Ispezione del fermo immagine**: forma, tre strappi, finestre, suola, assenza di marchi inventati | — | 0 |
| 3 | Animazione 5 s dal fotogramma approvato | Seedance 2.5 I2V, 480p, `generate_audio: false` | 1.000 |
| 4 | **Ispezione fotogramma per fotogramma** a piena risoluzione | — | 0 |

Totale **1.090**, ne restano ~2.650 per un secondo giro.

Il passo 1 e' quello che salva i crediti: correggere una scarpa sbagliata costa
130, correggerla dopo il video ne costa 1.000.

Nano Banana 2 va sempre chiamato con `aspect_ratio` esplicito e con il divieto
scritto di estendere o inventare parti della scena: il default resta 16:9 anche
partendo da un'immagine verticale.

---

## 3. Concept

**CONCEPT** — La scarpa regge un movimento vero: la modella scende fino in fondo
e risale senza che il piede ceda. Nessuna posa da vetrina, una prova di tenuta.

**HOOK (0–1,2 s)** — Si parte gia' in discesa. Camera bassa, all'altezza della
caviglia: il primo fotogramma e' la scarpa che scende verso l'obiettivo mentre
il ginocchio piega. Niente stacco iniziale, niente logo, nessuna posa ferma.
Lo spettatore vede un movimento gia' in corso e resta per vedere dove finisce.

**PERCHE' FUNZIONA IN 5 SECONDI** — Un'unica inquadratura continua, non tre tagli
compressi. Il gesto ha un inizio e una fine dentro la clip, quindi il video
**cicla**: il rialzarsi finale riporta esattamente alla posizione del primo
fotogramma. Su TikTok il loop pulito e' una leva di retention che non costa un
secondo in piu'.

**RUOLO DELLA MODELLA** — Dimostratrice. Non compra, non racconta, non parla.
Nessuna affermazione commerciale nel video: i claim, se servono, vanno a schermo
in post-produzione.

---

## 4. Storyboard

Inquadratura unica, 5,0 s, 9:16, camera a terra, obiettivo 35 mm.

| Tempo | Azione | Camera | Prodotto in quadro |
|---|---|---|---|
| 0,0–1,2 s | Discesa in squat, gia' iniziata al primo fotogramma | statica bassa, leggerissimo push-in | scarpa che entra verso il basso, terzo inferiore del quadro |
| 1,2–2,3 s | Punto piu' basso: tallone a terra, zeppa compressa, caviglia stabile | ferma, messa a fuoco sulla scarpa | scarpa al centro, la piu' grande di tutta la clip |
| 2,3–2,8 s | Micro-pausa in tenuta | ferma | scarpa nitida, ferma, leggibile |
| 2,8–4,4 s | Risalita fluida, il peso passa sull'avampiede | il push-in si chiude, l'inquadratura si allarga alla figura intera | scarpa piu' piccola, silhouette completa visibile |
| 4,4–5,0 s | In piedi, posizione di partenza, un ultimo appoggio | ferma | scarpa a terra, entrambe visibili — chiude il loop |

- **Ambiente**: fondo cemento chiaro, superficie liscia, luce laterale morbida.
  Niente scenografia: la scarpa deve staccare sul fondo.
- **Luce**: chiave laterale morbida + una riflessa a terra che apre le ombre
  sotto la suola. Contrasto controllato, nessuna alta luce bruciata.
- **Testo a schermo**: **nessuno nella generazione.** Va aggiunto in post con la
  pipeline locale — Seedance sbaglia i caratteri accentati e nel montaggio il
  testo si controlla al fotogramma. Regole di sicurezza dei margini in
  `ARTLIST.md`, sezione 6.
- **Audio**: nessuno, come richiesto. Coincide con la regola editoriale: cosi'
  non c'e' italiano parlato da sbagliare.
- **Vincolo di inquadratura**: la scarpa non deve mai toccare il bordo del quadro
  ne' incollarsi all'obiettivo. Il vincolo e' ripetuto tre volte nel prompt
  perche' e' gia' stato disatteso una volta.

---

## 5. Prompt Seedance 2.5 (image-to-video, dal fotogramma approvato)

```
Continuous single-take vertical fashion shot, 9:16, 5 seconds, no cuts.

SUBJECT: a tall athletic female model, full body, wearing the exact taupe
suede-effect high-top wedge sneakers shown in the reference frame. Neutral
fitted activewear in warm sand tones, nothing branded, nothing printed.

ACTION: the model is already descending into a deep squat at the first frame.
She lowers smoothly until heels stay flat on the ground and the wedge sole is
fully compressed, holds for a beat with a stable ankle, then rises back up in
one fluid movement and returns to a standing position identical to the opening
pose. The motion is controlled and athletic, never bouncy, never rushed.

CAMERA: locked low angle at ankle height, lens 35mm, almost static, with a very
slow push-in that settles at the bottom of the squat and eases back out during
the rise. Smooth, physically plausible camera behaviour. No handheld shake, no
whip pans, no orbit, no random moves.

FRAMING: the sneakers occupy the lower third of the frame and are the sharpest
element throughout. The sneakers must never touch or cross the frame edge. The
sneakers must never come close to the lens. Keep the full body inside the frame
at all times.

LIGHTING: soft directional key from camera left, bounced fill from the floor
that opens the shadow under the sole, clean pale concrete background, controlled
highlights, realistic contact shadows that track the foot.

MATERIAL REALISM: matte suede-effect nap that catches the key light without
gloss, visible stitching, three hook-and-loop straps in their exact reference
positions, cut-out side windows kept open and correctly shaped, thin sole with
its exact reference profile and colour, internal wedge silhouette unchanged.

CONTINUITY: the sneakers must remain pixel-consistent with the reference frame
in every single frame — shape, proportions, strap count and placement, cut-out
geometry, stitching, colour, texture, sole thickness and colour, silhouette.
Both shoes must match each other exactly.

NEGATIVE CONSTRAINTS: NO product redesign. NO product deformation. NO logo
alteration. NO added logos, brand names, wordmarks, tags or lettering of any
kind on the shoe, tongue, side panel, toe or sole. NO typography alteration.
NO color changes. NO material changes. NO shape changes. NO additional
branding. NO missing details. NO duplicated product. NO floating objects.
NO warped geometry. NO inconsistent proportions. NO AI artifacts. NO unnatural
reflections. NO unrealistic shadows. NO flickering. NO texture crawling.
NO morphing. NO object identity changes. NO inconsistent product details.
NO random camera movements. NO unnecessary CGI effects. NO cartoon look.
NO plastic-looking materials. NO generic stock advertising aesthetic. NO text
overlays. NO on-screen writing. NO speech. NO extra people. NO strap count
changes. NO platform or chunky sole substitution.
```

Impostazioni: `aspect_ratio: "9:16"`, `duration: "5"`, `resolution: "480p"`,
`generate_audio: "false"`, fotogramma approvato come `image_url` (start frame).

Il divieto sui marchi inventati e' scritto due volte, sull'elenco negativo e
nella riga materiali. **Resta un'istruzione, non un lucchetto**: e' successo tre
volte su tre. Il controllo a video e' obbligatorio comunque.

---

## 6. Controlli prima della consegna

- [ ] Tre strappi, non due — contati su almeno cinque fotogrammi
- [ ] Finestre laterali ritagliate presenti e della forma giusta
- [ ] Suola dello spessore del riferimento, nessun platform
- [ ] Zeppa interna, profilo invariato
- [ ] Nessun marchio, scritta o logo inventato su linguetta, fianco, punta, suola
- [ ] Le due scarpe identiche fra loro
- [ ] Scarpa mai a filo del bordo, mai incollata all'obiettivo
- [ ] Colore coerente con la variante che si sta pubblicizzando
- [ ] Nessun testo generato dal modello
- [ ] Ultimo fotogramma sovrapponibile al primo (loop pulito)

---

## 7. Da confermare con l'utente

- **Variante colore.** La foto di riferimento mostra una tomaia taupe/marrone
  con suola chiara. In `ARTLIST.md` la suola gum e' data per reale solo su
  grigio, beige e nero; su marrone e bordeaux e' in tinta. Va confermato di
  quale delle cinque varianti si parla, perche' la suola nel video deve essere
  quella vera.
- **Formato definitivo.** 5 secondi sono una inquadratura sola. La struttura
  completa del brief (hook → curiosita' → reveal → desiderabilita' → CTA)
  richiede 3-4 generazioni, circa 3.000-4.000 crediti a 480p.

---

## 8. Esito della prima esecuzione (variante beige)

Speso: **1.090 crediti** — 90 il fotogramma di partenza, 1.000 il video.
Il gate a 1.000 **non e' scattato**: la generazione e' partita da sola.

Riferimento usato: la foto di catalogo `bellamica-ra159i26-beige-a26_2`, non lo
screenshot — stessa scarpa, risoluzione piena.

Output: MP4 478x856, 24 fps, 5,04 s, **senza traccia audio**.

**Prodotto: fedele.** Controllati 40 fotogrammi campionati a 8 fps e i dettagli
ingranditi a inizio, meta' e fine:

- [x] tre strappi per scarpa, mai due
- [x] finestre laterali aperte, forma corretta
- [x] suola gum sottile, spessore e profilo del riferimento
- [x] zeppa interna, silhouette invariata
- [x] **nessun marchio, scritta o logo inventato** in nessun fotogramma
- [x] le due scarpe identiche fra loro
- [x] colore e nap del camoscio stabili, nessun flicker
- [x] nessun testo generato dal modello

**Difetto: il push-in ha stretto troppo.** Chiesto "molto lento" con la figura
intera sempre in quadro, il modello ha chiuso fino a lasciare solo le gambe
nell'ultimo secondo: la modella e' tagliata alla coscia sul finale. Il gesto
squat→risalita c'e' tutto ed e' pulito, e la scarpa chiude grande e nitida —
ma non e' l'inquadratura chiesta e il video non cicla.

**Correzione per il prossimo giro** (1.000 crediti): descrivere l'inquadratura
**finale** invece della velocita' del movimento — "the final frame is a full
body wide shot with the model standing, head and feet both inside the frame" —
e togliere del tutto la parola push-in.
