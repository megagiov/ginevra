# Il piano grafico — `projects/<job>/plan.json`

L'agente lo scrive dopo il rough cut, leggendo i tempi in `work/words_cut.json`
(sono già sulla timeline del montato). `py ve.py gfx JOB` lo trasforma in grafiche.

```json
{
  "logo": false,
  "beats": [
    {"type": "hook", "start": 0, "end": 2.0, "text": "Le *nuove tute* sono arrivate", "sub": "da 12 a 30 mesi"},
    {"type": "cta",  "start": -1.5, "end": 0, "text": "Link in bio", "sub": "gmvegasi.com"}
  ]
}
```

- `start` / `end` in secondi. Valori negativi = dalla fine (`-1.5, 0` = ultimo secondo e mezzo).
- `*parole*` tra asterischi = evidenziate su fascia blu del marchio (in hook e text).
- `y` (0–1) sposta verticalmente qualsiasi beat; `size` cambia il corpo del testo.
- `logo`: `false`, `"top"` o `"bottom"` (serve il PNG in `assets/`).
- Le foto aggiunte a mano vanno in `projects/<job>/img/`: restano anche se rifai `new --force`.
- `hook` con `full: true` è una scheda a tutto schermo blu: ottima come chiusura, con
  sopra `logo`, `image` scontornate e `badge` numerati.

## Tipi

| tipo | a cosa serve | campi | posizione standard |
|---|---|---|---|
| `hook` | aggancio dei primi 1-2 s | `text`, `sub`, `full` (true = schermo blu pieno) | alto (0,15) |
| `card` | scheda explainer: un punto chiave | `title`, `text`, `n` (numero) | metà alta (0,13) |
| `list` | elenco a passi, uno attivo | `title`, `items` [..], `active` (n o [n]) | metà alta (0,12) |
| `label` | nome prodotto, taglie, dettaglio | `text`, `sub`, `style` | 0,54 |
| `badge` | bollino a stella: NEW, -40%, 10€ | `text`, `sub`, `x`, `r`, `angle`, `style` | destra, 0,52 |
| `cta` | invito finale | `text`, `sub`, `style` (default accent) | 0,54 |
| `text` | testo libero | `text`, `color` (light/dark/primary/accent), `heading` | 0,20 |
| `image` | foto o screenshot in scheda arrotondata | `src` (relativo al progetto, es. `raw/02_foto.jpg`), `h` | metà alta |
| `image` + `cutout: true` | prodotto scontornato da foto su fondo bianco, con ombra | `src` (es. `img/foto-nero.jpg`), `x`, `y`, `w`, `h` | — |
| `logo` | logo del marchio dal PNG in `assets/` | `x`, `y`, `w`, `variant` (`blu` per fondi chiari) | alto, 0,12 |

`style` per label, badge e cta: `primary` (blu, testo bianco), `accent` (giallo, testo
scuro), `light` (bianco), `dark` (nero).

## Zone sicure 9:16 (1080×1920)

- Sopra 250 px: barra "Seguiti / Per te". Niente testo.
- Destra ~150 px: pulsanti like/commenti/condividi. Margine laterale 80 px già applicato.
- Sotto ~400 px: nome account e descrizione. I sottotitoli TikTok stanno a ~0,70–0,74 H.
- `label` e `cta` stanno a 0,54 per non toccare i sottotitoli: se il volto è lì, spostali
  con `y` e ricontrolla i provini.

## Regole di ritmo

- **TikTok raw**: hook entro 0,3 s, massimo 6–7 parole. Poi poche grafiche (una ogni 3–4 s),
  il protagonista è la persona. CTA nell'ultimo secondo e mezzo.
- **Explainer**: una `card` o `list` per ogni punto del discorso, che entra sulla parola
  che lo introduce e resta finché se ne parla. Il volto resta nella metà bassa.
- Una grafica entra **sulla parola** (tempo `s` in `words_cut.json`), non a caso.
- Due grafiche nella stessa zona non si sovrappongono mai nel tempo.

## Effetti sul video — voce `"fx"`

Girano dentro `gfx`, prima delle grafiche, e si ricalcolano solo se cambiano.
`"mute": true` nel piano toglie l'audio (versione muta, traccia silenziosa).

```json
"fx": {
  "grade": true,
  "moves": [
    {"type": "punch", "at": 0.0, "amount": 0.18},
    {"type": "flash", "at": 0.9},
    {"type": "zoom",  "start": 1.6, "end": 3.0, "to": 1.45,
     "at": [[1.4, 0.51, 0.55], [2.2, 0.66, 0.58], [3.0, 0.45, 0.48]]}
  ]
}
```

| tipo | effetto | campi |
|---|---|---|
| `zoom` | entra sul dettaglio e resta (`out: true` per uscire) | `start`, `end`, `to`, `ramp`, `at` |
| `push` | avvicinamento lento per tutta la durata | `start`, `end`, `from`, `to`, `at` |
| `punch` | colpo di zoom sullo stacco, si apre in `dur` | `at`, `amount`, `dur` |
| `shake` | tremolio | `start`, `end`, `amp` (px) |
| `flash` | lampo bianco, picco su `at` | `at`, `dur`, `peak` |
| `glitch` | sdoppiamento dei colori | `start`, `end`, `amp` (px) |

- `at` è il punto da inquadrare (0–1 sul fotogramma): `[x, y]` fisso, oppure
  `[[t, x, y], ...]` per seguire il dettaglio mentre la camera si muove. I punti si
  leggono dai provini del montato (`check --src cut`); poi si verifica sui provini del
  composto che il dettaglio sia davvero al centro.
- `grade` (default sì): un po' più di contrasto e saturazione, più nitidezza, vignetta.
- Su video compressi (WhatsApp) non superare zoom 1,4–1,5: oltre si vedono i quadretti.
- Stacchi tipici: `flash` + `punch` sullo stesso istante.

## Suoni — voce `"sfx"`

`"sfx": true` aggiunge suoni sintetizzati in locale (nessuna licenza): fruscio quando entra
un testo, pop per foto, bollini e logo, colpo sugli stacchi con `flash` e sulle schede a
tutto schermo, disturbo sui `glitch`. Con `"mute": true` resta solo questa traccia; senza,
si somma all'audio originale. Per aggiungerne a mano o cambiare il volume:
`"sfx": {"extra": [{"type": "pop", "at": 2.0}], "gain": -3}` (tipi: whoosh, pop, impact, glitch).
