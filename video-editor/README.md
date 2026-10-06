# Agente video GM Vegasi

Monta i video come un editor: dai file grezzi al video pronto per TikTok e Instagram.
Taglia pause ed esitazioni, aggiunge grafiche col marchio, sottotitoli a parola
evidenziata e musica, ed esporta. Gira sul tuo PC, gratis, senza crediti.

Lo guida Claude Code: tu gli dici cosa vuoi, lui lancia i passi, controlla i
fotogrammi e ti mostra il risultato.

## Installazione (una volta sola, Windows)

1. Installa **Claude Code** sul PC (serve anche Git per Windows) e clona questo repository.
2. Apri la cartella `video-editor`, tasto destro su `setup.ps1` → **Esegui con PowerShell**.
   Se installa Python o FFmpeg, ti chiede di chiudere e riaprire PowerShell e di rilanciarlo.
3. Copia i loghi in `video-editor/assets/` (nomi in `assets/LEGGIMI.md`):
   - `gmvegasi-logo-bianco.png`: logo bianco su fondo trasparente
   - `gmvegasi-logo-blu.png`: logo blu su fondo trasparente
4. Metti i brani con licenza (es. scaricati da Artlist) in `video-editor/music/`.
5. Controllo finale: `py ve.py doctor`. Deve dire **Tutto pronto**.

## Come si usa

Apri Claude Code nella cartella del repository e scrivi, per esempio:

> Monta per TikTok il video in C:\Users\Marco\Desktop\tute.mp4. In sovrimpressione:
> "nuove tute 12-30 mesi", prezzo 10€, link in bio.

> Ho 6 clip della vetrina in C:\Video\vetrina, senza voce: fammi un reel di 15 secondi
> con musica.

> Fai un explainer da questo video in cui spiego come fare un reso.

Prima di montare, Claude guarda il materiale e ti fa qualche domanda a scelta multipla
(su cosa concentrarsi, durata, stile, audio, chiusura): rispondi con un tocco. Poi segue i
7 passi descritti in `.claude/skills/video-editor/SKILL.md` e ti consegna due file in
`video-editor/outputs/`:

- `NOME.final.mp4`: con musica
- `NOME.nomusic.mp4`: senza musica, per mettere un brano di tendenza dall'app

Per le modifiche basta dirlo ("togli la frase sul reso", "la scritta più in alto",
"musica più bassa"): rifà solo il passo che serve.

## I 7 passi

| # | Passo | Comando | Cosa fa |
|---|---|---|---|
| 1 | Intake | `new` | copia il grezzo, porta tutto a 9:16 1080×1920 30 fps; le foto diventano clip con zoom |
| 2 | Rough cut | `transcribe` + `cut` | trascrive parola per parola, toglie "ehm", pause e frasi ripetute, pulisce la voce |
| 3 | Grafiche | piano + `gfx` | aggancio, schede, elenchi, bollini, CTA col marchio |
| 4 | Secondo passaggio | `check` | foglio di provini; Claude li controlla, tu dai le note |
| 5 | Sottotitoli | (dentro `gfx`) | 2-3 parole alla volta, la parola detta in giallo |
| 6 | Musica | `music` | facoltativa; scende da sola quando qualcuno parla |
| 7 | Export | `export` | versione con musica + versione senza in `outputs/` |

Formati: `tiktok` (raw: aggancio → persona, sottotitoli bassi) ed `explainer`
(schede nella metà alta, sottotitoli al centro). Lo **spot prodotto 10 s** dalle foto
del catalogo resta in `../video-prodotto/`.

## Tempi indicativi su un PC normale (solo processore)

Video da 60 s: trascrizione 1-2 min (modello `small`), taglio ~30 s, grafiche e
sottotitoli ~1 min, musica ed export pochi secondi.

## Problemi noti

- **`ffmpeg non trovato` subito dopo l'installazione**: chiudi e riapri il terminale.
- **Nomi storpiati nei sottotitoli** (es. "Vegas" invece di "Vegasi"): aggiungili a
  `presets/caption-corrections.json`, valgono per tutti i video successivi.
- **Trascrizione imprecisa con rumore forte**: `py ve.py transcribe NOME --model medium`.
- **Scheda NVIDIA**: `--device cuda` rende la trascrizione molto più veloce.
