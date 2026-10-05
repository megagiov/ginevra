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
