# Spot back to school

Spot verticale 9:16 per il corner scolastico. La presentatrice e' generata su
Artlist e parla; il parlato del modello viene sostituito con la voce italiana
corretta; testi e taglio finale si montano in locale.

## Come e' fatto

| Passo | Strumento | Costo |
|---|---|---|
| Immagine della presentatrice in posa | Nano Banana 2, 9:16 2K | 130 |
| Voce italiana | Eleven v3, voce Grounded, `language: Italian` | 25 |
| Video, 11 s 480p, `startFrame` ancorato | Seedance 2.0 Mini | 550 |
| Sostituzione voce, testi, taglio | locale | 0 |

## L'ordine dei comandi

```bash
pip install Pillow numpy scipy imageio-ffmpeg faster-whisper "rembg[cpu]"
# out/voce.wav  = voce italiana scaricata da Artlist
# out/f11/      = fotogrammi del video generato
# orig_44k.wav  = audio del video generato, 44,1 kHz mono
python3 back-to-school/allinea_voce.py    # posa le frasi vere sugli attacchi
python3 finish.py                          # fondo sala + trattamento + mix
python3 back-to-school/monta_testi.py      # testi, taglio, 1080x1920
```

## Le cose che contano

- **`startFrame`, non un riferimento normale.** Passare l'immagine come
  riferimento a una variante reference-to-video la tratta come ispirazione: e'
  tornato indietro un video con un'altra donna in un altro negozio, 2.200
  crediti buttati. Con `input: { startFrame: ... }` su una variante
  image-to-video l'ancoraggio tiene.
- **Il parlato generato va sostituito sempre.** Qui ha detto *"E timola a
  pensare a scuolo, backpacks, pencil cases, water bottles..."*: storpia e
  traduce in inglese.
- **Allineamento per frase, non per parola.** `place.py` pretende che le parole
  si corrispondano; qui non si corrispondono. Le quattro frasi si', e appoggiate
  sui rispettivi attacchi restano entro 60 ms. Dentro le frasi l'audio non si
  tocca mai.
- **La bocca si ferma prima della voce.** Misurato otticamente: parla fino a
  8,6 s. L'ultima frase va posata sull'ultimo tratto sonoro vero (7,97 s), non
  in coda alla precedente: lo scarto scende da 0,96 a 0,50 s. Il cartello
  `COSA ASPETTI?` entra mezzo secondo prima della voce e copre quel residuo.
- **Il video si taglia a 9,60 s.** Dopo c'e' solo lei ferma che sorride.
- **Il testo non scende sotto y=1400**: sotto ci vanno didascalia e pulsanti di
  TikTok e Instagram. E la velatura sotto il testo va tenuta densa, altrimenti
  il bianco sparisce sulla canotta.

## Da fare prima di pubblicare

- **Musica su licenza.** Lo spot esce con la sola voce.
- **End card** GM Vegasi TikTok Shop, se la si vuole in coda.
- **Etichettatura** come contenuto pubblicitario del negozio.
- **Ispezione a piena risoluzione** di ogni nuova generazione, sempre.

## Materiali in `foto/`

Non versionati (`.gitignore` esclude jpg e png): qui si versiona la pipeline,
non il materiale. Servono `negozio-close.jpg`, `negozio-largo.jpg` e
`avatar-presentazione-9x16.png`.

## La strada alternativa, senza generazione video

`build_bts.py` e `sfoca_avatar.py` montano lo stesso copione a costo zero: la
merce dalle foto vere con carrellata digitale, la presentatrice generata col
fondo sfocato. Utile se la generazione video non e' disponibile o se si vuole
evitare del tutto il rischio dei marchi ridisegnati.
