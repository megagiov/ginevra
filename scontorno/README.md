# Scontorno — togliere lo sfondo da una foto, in locale

Come remove.bg, ma senza account, senza crediti e senza che la foto esca dalla
macchina. Trascini l'immagine nella pagina e ti torna un PNG con trasparenza.

Tre strade, scelte da sole in base alla foto:

| strada | quando | tempo |
|---|---|---|
| `misto` | scatti da catalogo su fondo unito, **ombra compresa**: la rete dice dove sta il prodotto, il colore taglia il bordo | ~0,8 s a foto |
| `rete` | foto vere — persone, scene, fondi sporchi: U²-Net / IS-Net su onnxruntime, CPU | ~0,3 s a foto |
| `tinta` | solo flood fill sul colore, senza modello: istantaneo, ma tiene l'ombra e si mangia le parti del prodotto che hanno il colore del fondo | ~0,25 s a foto |

Il modo `auto` misura quanto il bordo dell'immagine è di un colore solo: sopra
il 97% va di `misto`, altrimenti di `rete`. Se il flood fill non toglie nulla,
ricade sulla rete da solo.

### L'ombra

Un'ombra non cambia il colore di ciò su cui cade: lo scurisce e basta, allo
stesso modo sui tre canali. È così che viene riconosciuta, e per questo se ne
va insieme al fondo anche quando è molto più scura della tolleranza di colore.

```bash
--ombra via        # sparisce col fondo (predefinito)
--ombra morbida    # torna come nero semitrasparente: regge su qualsiasi fondo
--ombra tieni      # resta attaccata al prodotto, com'era prima
```

Il grigio chiaro resta ambiguo — una suola bianca sporca somiglia a un'ombra —
ed è lì che serve la rete: in `misto` la sua maschera protegge il prodotto e
vince sul test del colore.

## Da usare senza terminale (Windows)

1. [Scarica lo ZIP](https://github.com/megagiov/ginevra/archive/refs/heads/claude/jolly-brown-tw1mcr.zip)
   ed estrailo.
2. Dentro la cartella `scontorno`, doppio clic su **`installa.bat`**. Ci mette
   un paio di minuti: crea l'ambiente, installa le tre librerie e scarica il
   modello.
3. Sul desktop compare l'icona **Scontorno**. Doppio clic e si apre la finestra:
   *Scontorna le foto…* le sfonda e le salva come `nome-scontornata.png`;
   *Cambia solo formato…* le converte e basta. Il menu **salva in** decide il
   formato in uscita per tutti e due i bottoni.

La riga **misura** rimpicciolisce: scrivi `800` oppure `800x800`, lascia vuoto
per non toccare niente. Il menu **come** dice cosa vuol dire quella misura:

- **lato massimo** — ci sta dentro mantenendo le proporzioni: una 1024×768 con
  `800` esce 800×600;
- **tela esatta** — esce proprio di quella misura, con il soggetto centrato e
  il resto riempito (trasparente, o il colore scelto in *sfondo*). È il caso
  del catalogo, dove tutte le foto devono uscire dello stesso formato.

**Non ingrandisce mai**: una foto più piccola della misura chiesta resta com'è
(in *tela esatta* viene centrata sulla tela). Allargare non aggiunge dettaglio,
aggiunge peso e sfocatura.

La riga **le salvo in** decide dove finiscono i file: di partenza accanto alle
originali, con *Cambia…* in una cartella tua (se non esiste la crea). La scelta
resta anche quando chiudi, insieme a formato, ombra e sfondo. Se quella cartella
un giorno non si lascia scrivere — chiavetta tolta, disco pieno — il file viene
messo accanto all'originale o sul desktop e te lo scrive nell'elenco, invece di
perdere il lavoro.

Ci si possono anche **trascinare le foto sopra l'icona**: partono da sole.

`installa.bat` si può rilanciare quando vuoi, non rifà quello che c'è già.
Se il Python installato è senza `tkinter` (capita con certe versioni dallo
Store), l'icona apre la stessa cosa nel browser invece che in una finestra.

## Cambio formato

Lo stesso programma converte e basta, senza toccare lo sfondo: il bottone
*Cambia solo formato…* nella finestra, oppure da riga di comando.

```bash
./venv/bin/python converti.py foto.avif --in jpg
./venv/bin/python converti.py *.webp --in jpg -o convertite/
./venv/bin/python converti.py logo.png --in jpg --sfondo bianco --qualita 90
./venv/bin/python converti.py *.jpg --in jpg --misura 800x800 --tela   # tutto a 800×800
```

`--misura` e `--tela` valgono anche per `scontorno.py`.

**Legge** tutto quello che apre Pillow — JPG, PNG, WEBP, AVIF, TIFF, BMP, GIF,
ICO — e in più **HEIC/HEIF dell'iPhone** se è installato `pillow-heif`
(`installa.bat` ci prova da solo; se quel Python non ce l'ha, il resto funziona
lo stesso). **Scrive** in JPG, PNG, WEBP e AVIF.

Tre cose che fa da sé:

- **raddrizza secondo l'EXIF**: le foto da telefono arrivano coricate, e chi
  converte senza guardare l'orientamento le salva coricate per sempre;
- **non sovrascrive mai l'originale**: se il nome di destinazione è già
  occupato aggiunge `-convertita`;
- **appoggia la trasparenza su un colore quando si va in JPG** (bianco se non
  dici altro), invece di lasciare che diventi nera.

Il profilo colore e i dati di scatto vengono portati dietro quando ci sono.

## Installazione a mano

```bash
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
```

Tre pacchetti: Pillow, numpy, onnxruntime. Al primo uso della rete il modello
viene scaricato in `models/` (176 MB, una volta sola) e verificato con sha256 —
un `.onnx` troncato non dà errore, dà una maschera vuota.

## Uso

```bash
./venv/bin/python server.py          # poi apri http://127.0.0.1:8000
```

Trascini le foto (o clicchi, o incolli con Ctrl+V), le vedi comparire
scontornate su scacchiera e scarichi il PNG. Più foto insieme vanno bene. Il
modello resta caldo in memoria: paga solo la prima richiesta.

Da riga di comando, stessa resa, anche in blocco:

```bash
./venv/bin/python scontorno.py foto.jpg                    # -> foto-scontornata.png
./venv/bin/python scontorno.py *.jpg -o out/ --ritaglia
./venv/bin/python scontorno.py scarpa.jpg --ombra morbida  # ombra semitrasparente
./venv/bin/python scontorno.py foto.jpg --sfondo bianco    # o nero, grigio, ff0055
./venv/bin/python scontorno.py foto.jpg --modo rete --modello isnet
```

| opzione | cosa fa |
|---|---|
| `--modo auto\|misto\|rete\|tinta` | forza la strada invece di lasciarla decidere |
| `--ombra via\|morbida\|tieni` | che fine fa l'ombra (vedi sopra) |
| `--modello u2net\|u2netp\|isnet` | u2net è il default; `u2netp` pesa 4,7 MB ed è più rapido ma più grossolano; `isnet` tiene meglio capelli e dettagli sottili |
| `--sfondo` | riempie il fondo invece di lasciarlo trasparente |
| `--ritaglia` | taglia al riquadro del soggetto |
| `--taglio 0.15` | spinge i mezzi toni dell'alpha a 0/1: bordo più netto, meno alone |
| `--sfuma 1.5` | ammorbidisce il bordo di N px |
| `--rientra 1` | erode il bordo di N px: toglie l'ultimo filo di sfondo |
| `--misura 800x800` | rimpicciolisce dentro quella misura; `800` vale `800x800` |
| `--tela` | esce esattamente di quella misura, soggetto centrato |

### Su Windows

```powershell
py -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python server.py
venv\Scripts\python scontorno.py "*.jpg" -o out --ritaglia
```

Due differenze rispetto a Mac e Linux:

- **gli asterischi vanno tra virgolette**: PowerShell non li espande e passa
  `*.jpg` così com'è. Ci pensa il programma, ma solo se la shell non se lo
  mangia prima;
- **la porta 8000 spesso è vietata** (`WinError 10013`): sta dentro un
  intervallo riservato da Hyper-V o WSL. Il server non si ferma, prova le porte
  successive e stampa quella su cui si è aperto — è quella da aprire nel
  browser.

Il server sta su `127.0.0.1`: non è raggiungibile da fuori. `--host 0.0.0.0` lo
espone alla rete locale — non c'è autenticazione, quindi fallo solo su una rete
di cui ti fidi.

## Note

- I pesi sono quelli pubblicati dal progetto [rembg](https://github.com/danielgatis/rembg)
  (licenza MIT). Qui l'inferenza è fatta a mano con onnxruntime: tre dipendenze
  invece dell'albero completo di rembg.
- **`ImageDraw.floodfill` non scrive su un'immagine creata con `Image.fromarray`**:
  il buffer numpy è di sola lettura, la chiamata fallisce in silenzio riempiendo
  zero pixel e lo scontorno esce tutto opaco. Stessa trappola già pagata in
  `video-prodotto/`. Qui il flood fill è comunque riscritto a tratti di riga:
  quello di PIL è Python puro e costava 1,0 s su 1024×1024 contro i 0,02 s di
  adesso, a parità di risultato su tutti i casi di prova.
- **Il flood fill sul solo colore mangia il prodotto bianco su fondo bianco.**
  Su 24 foto del catalogo succedeva a 2 (una adidas e una ciaodea: mezza suola
  e mezza tomaia sparite). La protezione della rete in `misto` lo risolve, ed è
  il motivo per cui `tinta` non è più la strada predefinita.
- **Sulle ombre dure la rete sbaglia**: le legge come parte del prodotto, con
  punteggi fino a 0,98. Il prodotto però sta a 1,00 pieno, quindi a un pixel
  che ha anche il colore di un'ombra si chiede la certezza prima di proteggerlo.
- Misurato su ombre sintetiche con alpha vero noto (tre prodotti × ombra
  morbida, dura, di contatto): **IoU da 0,984 a 0,994, ombra residua da 0% a
  8,5%** (il caso peggiore è un'ombra dura e molto scura). Lo stesso set con
  `--modo tinta` lascia l'88-93% dell'ombra attaccata.
- Il flood fill parte dagli angoli: lo sfondo chiuso dentro il soggetto (le
  asole di una scarpa, il triangolo tra braccio e fianco) resta opaco. Su quelle
  foto conviene `--modo rete`.
- Sui pixel di bordo semitrasparenti resta un alone del fondo: viene scurito del
  7% in automatico. Se il fondo originale era scuro e il risultato ti sembra
  sporco, prova `--rientra 1`.
- Il server tiene una sola inferenza per volta (onnxruntime non è rientrante su
  una sessione condivisa): con dieci foto insieme le vedrai finire in fila.
- La cartella `models/` è fuori dal versionamento.
- Le scelte della finestra stanno in `%APPDATA%\Scontorno\scelte.json`
  (`~/.config/Scontorno/` altrove), non nella cartella del programma: quella
  può essere di sola lettura.
- **tkinter non si interroga da un altro thread.** Le scelte dei menu vengono
  lette sul thread della finestra e passate al lavoro come valori normali: a
  leggerle da dentro il thread la finestra si pianta sulla prima foto, senza
  errori. Visto succedere.
- Nei comandi qui sopra `foto.jpg` e `scarpa.jpg` sono nomi d'esempio: vanno
  sostituiti con quelli veri. Se non li trova, il programma elenca le immagini
  che ci sono nella cartella.

## Perché sta in questo repository

`video-prodotto/` scontorna già le foto del catalogo per montarle negli spot,
ma solo su fondo bianco e solo dentro la pipeline. Qui la stessa cosa è
utilizzabile su qualunque foto e da sola.
