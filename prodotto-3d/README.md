# START UP — Everyday Sweatpants, Winter Collection

Render di prodotto del pantalone felpato START UP. Due viste consegnate su
dieci richieste dal brief: **fronte e retro**. Le altre otto (fianchi, tre
quarti, primi piani di vita, logo, triangolo, tasca) non sono state generate su
richiesta esplicita dell'utente, per non consumare crediti.

## Cosa c'e' qui

| File | Cosa |
|---|---|
| `render/01-fronte.png` | Vista frontale, 1792x2400 — **da consegnare** |
| `render/02-retro.png` | Vista posteriore, 1792x2400 — **da consegnare** |
| `render/01-fronte-grezzo.png` | Uscita cruda del modello, con il logo sbagliato |
| `render/02-retro-grezzo.png` | Idem, retro |
| `logo/startup-logo-classico.png` | Logo ufficiale, 496x496, preso dal sito |
| `logo_esatto.py` | Rimette il logo ufficiale sui render |
| `SCHEDA-TECNICA.md` | Specifica del capo e scarti dal brief |

I file `-grezzo` non sono materiale di scarto: sono l'ingresso di
`logo_esatto.py`. Cancellandoli la pipeline non si riproduce piu'.

## Come sono stati fatti

1. Il logo ufficiale viene dalla libreria media di startupmoda.com
   (allegato ID 18, `startup-logo-classico.png`). E' lo stesso file caricato
   dall'utente, quindi il marchio non e' stato ridisegnato ne' ricostruito.
2. Il fronte e' stato generato su Artlist con Nano Banana Pro image-to-image a
   2K, passando il logo come riferimento. **160 crediti.**
3. Il retro e' stato derivato dal fronte, passando come riferimenti sia il
   render frontale sia il logo, cosi' il capo resta lo stesso e non diventa un
   secondo pantalone simile. **160 crediti.**
4. `logo_esatto.py` ha sostituito il marchio inventato dal modello con il file
   ufficiale. **Zero crediti.**

Totale speso: **320 crediti**.

## Rigenerare

```
python3 logo_esatto.py
```

Legge i due `-grezzo`, riscrive i due file finali. Serve `pillow`, `numpy` e
`scipy`. Le coordinate dei piazzamenti sono misurate su questi due render
specifici: rigenerando le immagini su Artlist vanno rimisurate.
