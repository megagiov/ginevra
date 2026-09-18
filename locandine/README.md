# Locandine — On The Road Napoli

Locandine social composte in locale a partire da una foto del negozio.
Nessun modello generativo, nessun credito: il testo è disegnato con font veri,
quindi è esatto al pixel. Non può comparire un marchio inventato sulla moto né
una parola italiana storpiata, che sono i due difetti ricorrenti documentati in
`../video-prodotto/ARTLIST.md`.

## Cosa produce

`locandina_san_gennaro.py` — chiusura per la festa patronale di San Gennaro,
sabato 19 settembre.

| File | Dimensioni | Dove si usa |
|---|---|---|
| `out/san-gennaro-story.jpg` | 1080×1920 | storie e reel, 9:16 |
| `out/san-gennaro-feed.jpg` | 1080×1350 | post in bacheca, 4:5 |
| `out/san-gennaro-quadro.jpg` | 1080×1080 | quadrato, 1:1 |
| `out/san-gennaro-story-senza-riapertura.jpg` | 1080×1920 | 9:16 senza la data di rientro |

## Esecuzione

```bash
pip install Pillow numpy
python3 locandina_san_gennaro.py                      # tutti i formati
python3 locandina_san_gennaro.py story feed           # solo alcuni
python3 locandina_san_gennaro.py --riapertura=""      # senza riga di rientro
python3 locandina_san_gennaro.py --riapertura="Torniamo domenica 20"
```

I font (licenza SIL OFL) stanno in `fonts/`. La foto sorgente in `assets/`.

## Impianto grafico

- **La fascia del logo resta intatta.** Viene ripresa dall'originale e
  incollata in cima, con un filetto oro e un innesto rosso a separarla.
- **Il faro è il perno.** Il taglio della foto si ancora al faro, non a una
  riga fissa: da lì partono la raggiera e l'aureola dorata, e il faro della
  moto fa da nimbo.
- **Palette dal marchio.** Il rosso `#DA0411` è campionato dalle fiamme del
  logo, non scelto a occhio. L'oro richiama il busto del santo.
- **Niente testo critico nella fascia bassa.** È la zona che Instagram e TikTok
  coprono con la loro interfaccia: lì c'è solo la fascia rossa di chiusura, che
  ripete informazioni già presenti nell'header.

## Trappole già pagate

- **La raggiera sbordava sulla fascia del logo e la velava di grigio.** Si vede
  solo nei formati corti, dove il faro è vicino all'header. Gli strati di luce
  vanno azzerati sopra `header_h` (`_proteggi_logo`).
- **Il blocco di testo su una `y` fissa finiva fuori quadro.** Con font adattati
  alla larghezza l'altezza non è nota in anticipo: va misurata prima di
  disegnare, e il blocco ancorato dal basso alla fascia rossa.
- **I bordi netti dei raggi bandeggiavano sul carroponte.** Servono
  sovracampionamento 2× e una sfocatura gaussiana sulla maschera.
- **L'aureola va composta dopo la velatura scura**, altrimenti la velatura la
  spegne proprio dove serve. Ma questo vale solo se il faro sta sul bordo alto
  della sfumatura: se finisce sotto, si spalma dietro al testo e sembra nebbia.
- **La riga unita dei formati compatti si gonfiava** fino a sovrastare il resto:
  l'adattamento alla larghezza vuole un tetto alla dimensione nominale.

## Note editoriali

- Il 19 settembre 2026 cade **di sabato**: verificato, non dedotto.
- **«Vi aspettiamo lunedì 21» è l'unica riga da confermare col negozio.** Il 20
  è domenica; se la concessionaria apre anche la domenica la riga va cambiata,
  ed è per questo che esiste l'opzione `--riapertura`.
- Sulla locandina non compaiono orari, indirizzi o recapiti: non li abbiamo, e
  scriverli a intuito sarebbe un'affermazione falsa.
- Il marchio visibile sul serbatoio è quello reale della moto fotografata, non
  un marchio generato.
