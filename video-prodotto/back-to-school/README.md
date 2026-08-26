# Spot back to school

Spot verticale 9:16 per il corner scolastico del negozio. Metodo ibrido: la
presentatrice e' generata, la merce no.

## Perche' ibrido

Sullo scaffale scolastico ci sono decine di prodotti su licenza. Generando la
scena col modello immagine, le scritte tornano indietro storpiate: `KUROMI` ->
`ROIRCHMI`, `Mickey Mouse` -> `Mickey eHouse`, `HUNTRIX` -> `FUNFOO`, piu'
scritte illeggibili su astucci e borracce. Il divieto scritto nel prompt riduce
la frequenza ma non la elimina — vale la stessa regola gia' a quaderno per le
sneakers.

Un'inserzione del negozio con `Mickey eHouse` stampato sullo zaino sembra merce
contraffatta. Quindi:

- **la merce si vede solo nelle foto vere del negozio**, ferme, con carrellata
  digitale: pixel fotografati, nessun marchio inventabile;
- **la presentatrice e' l'unica immagine generata**, e ha il fondo sfocato in
  post, cosi' le scritte storpiate dietro di lei non sono leggibili.

## Struttura

Gli stacchi cadono dentro le pause vere della voce, misurate sull'onda.

| Da | A | Immagine | Testo a schermo |
|---|---|---|---|
| 0,00 | 2,18 | presentatrice | È TEMPO DI PENSARE ALLA SCUOLA |
| 2,18 | 5,04 | foto parete | ZAINI · ASTUCCI · BORRACCE |
| 5,04 | 7,21 | foto campo largo | ANCHE CON I PERSONAGGI DEI CARTONI |
| 7,21 | 10,37 | presentatrice, piu' stretta | DA NOI TROVI TUTTO / COSA ASPETTI? |

Voce fuori campo: *"È tempo di pensare alla scuola. Zaini, astucci, borracce,
anche con i personaggi dei cartoni. Da noi trovi tutto. Cosa aspetti?"*

## Materiali attesi in `foto/`

Non sono versionati (`.gitignore` esclude jpg e png): qui si versiona la
pipeline, non il materiale.

| File | Cos'e' |
|---|---|
| `negozio-close.jpg` | foto vera, parete del corner |
| `negozio-largo.jpg` | foto vera, corsia in campo largo |
| `avatar-presentazione-9x16.png` | presentatrice generata, 9:16 |
| `avatar-sfocato.png` | la stessa col fondo sfocato, prodotta da `sfoca_avatar.py` |

## Esecuzione

```bash
pip install Pillow numpy scipy imageio-ffmpeg "rembg[cpu]"
python3 back-to-school/sfoca_avatar.py     # maschera + sfocatura del fondo
python3 back-to-school/build_bts.py        # voce, montaggio, codifica
```

La voce va generata prima su Artlist (Eleven v3, voce Grounded, lingua
`Italian`) e salvata in `out/voce.wav`. Piper non va bene qui: elide una
consonante.

## Trappole gia' pagate

- **La segmentazione della persona sbava sugli oggetti dello scaffale.** Un solo
  modello lascia frammenti di prodotto a fuoco attaccati alla sagoma. Serve
  l'intersezione di tre maschere: cio' che tutti e tre chiamano persona e'
  persona.
- **`binary_fill_holes` chiude anche lo spazio tra braccio e busto**, e li'
  dentro resta a fuoco lo scaffale che si vede in mezzo. Vanno richiusi solo i
  buchi piccoli (< 8000 px).
- **La foto sorgente e' 3:4, lo spot e' 9:16.** Il ritaglio va fatto ai lati:
  far estendere il quadro al modello significa fondo inventato. Nel campo largo
  il ritaglio esclude anche la persona reale sul bordo destro e il volantino a
  terra.
- **Il testo non scende sotto y=1400**: sotto ci vanno didascalia e pulsanti di
  TikTok e Instagram.

## Da fare prima di pubblicare

- **Musica**: lo spot esce con la sola voce. Serve un brano su licenza.
- **End card**: gli ultimi secondi sono la presentatrice. Se si usa l'end card
  GM Vegasi TikTok Shop, va montata in coda.
- **Etichettatura**: contenuto pubblicitario del negozio.
