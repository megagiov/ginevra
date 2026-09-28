# Passaggio di consegne

Testo da incollare come primo messaggio in una nuova sessione, per riprendere
il lavoro sul sito di Sorgente Traslochi senza ripartire da zero.

---

Riprendo un lavoro gia' avviato: il sito di **Sorgente Traslochi**, impresa di
traslochi di Napoli. Il sito e' online e funzionante, quindi non si ricomincia
da capo: si continua.

## Dove sta tutto

- **Repository GitHub**: `megagiov/ginevra`, cartella `sito/`
- **Ramo di produzione**: `claude/ui-ux-pro-max-install-6d9bd5` (e' il ramo
  principale del repository, ha un nome strano per ragioni storiche)
- **Sito pubblicato**: https://sorgentetraslochi.pages.dev
- **Hosting**: Cloudflare Pages, progetto `sorgentetraslochi`, pubblica da
  solo a ogni push sul ramo di produzione, directory di output `sito/dist`

**Prima di qualunque cosa, leggi questi file del repository**: `sito/README.md`
(come si genera il sito), `sito/DA-COMPLETARE.md` (cosa manca), `sito/SEO.md`
(stato e piano SEO), `sito/DEPLOY.md` (pubblicazione, Search Console, vecchio
sito Wix), `sito/TESTI-GOOGLE-BUSINESS.md` (testi pronti per la scheda
Google). Se non hai accesso al repository, chiedimeli e te li incollo.

## Com'e' fatto il sito

Sito statico generato da uno script Python senza dipendenze:

- `sito/content.py` — tutti i testi e i dati dell'azienda
- `sito/build.py` — struttura pagine, dati strutturati, modulo
- `sito/src/style.css` — grafica
- `sito/src/img/` — foto in WebP, con gli originali in `originali/`
- `sito/tools/prepara-foto.py` — converte le foto (richiede Pillow, si lancia
  solo quando arrivano foto nuove; `build.py` copia i file gia' pronti)
- `sito/dist/` — output pubblicabile, **committato apposta** perche'
  Cloudflare lo serva senza eseguire build

Si rigenera con `cd sito && python3 build.py`. Il comando elenca in fondo i
dati ancora mancanti.

Dieci pagine: home, traslochi abitazioni, traslochi uffici e negozi,
montaggio mobili, sgomberi, deposito mobili, zone servite, chi siamo,
preventivo, privacy. Piu' una pagina 404.

## Stato attuale

Fatto e verificato:

- sito online, Lighthouse 100 su prestazioni, accessibilita', buone pratiche
  e SEO, sia desktop sia mobile; LCP 1,0-1,5 s su mobile, CLS 0
- dati strutturati: `MovingCompany` (NAP, orari, 12 aree servite, sameAs),
  `Service` su ogni pagina servizio collegato alla stessa azienda,
  `FAQPage`, `BreadcrumbList`
- 11 foto vere dell'azienda, nessun segnaposto
- due recensioni vere dalla scheda Google in home, riportate alla lettera
- modulo preventivo collegato a Formspree (`FORMSPREE_ID = "mvkgajzy"`)
- Google Search Console verificata (tag in `VERIFICA_GOOGLE`), sitemap inviata
- vecchio sito Wix `sorgentetraslochi.wixsite.com/website`: messo in
  `noindex` e dotato di una fascia che rimanda al sito nuovo dopo 6 secondi,
  entrambi via API Wix

## Cosa manca

1. **Partita IVA.** Il numero che mi era stato dato, `09374401211`, **non
   supera il controllo di validita'**: con quelle prime dieci cifre la cifra
   finale dovrebbe essere 5. Va riletta da una fattura. Finche' manca, il sito
   omette la riga invece di mostrare un segnaposto. E' un dato obbligatorio
   per legge: va inserita prima di promuovere il sito.
2. **Ragione sociale** — si ottiene insieme alla P.IVA dal servizio di
   verifica dell'Agenzia delle Entrate.
3. **Testi della scheda Google Business** — pronti in
   `TESTI-GOOGLE-BUSINESS.md`, devo solo incollarli io nella scheda.
4. **Sitemap in Search Console** risultava "Impossibile recuperare" con 0
   pagine, ma il file e' raggiungibile, valido e servito come
   `application/xml` anche a Googlebot: e' un errore lato Google, da
   reinviare e ricontrollare.
5. **Foto dedicate** per le pagine uffici, sgomberi e deposito: adesso usano
   foto riprese da altre pagine.
6. **Recensioni recenti**: delle sei sulla scheda, quattro hanno cinque o sei
   anni e l'unica recente non ha testo.
7. **Proposta aperta**: pagine dedicate ai sei comuni principali (Casoria,
   Afragola, Giugliano, Pozzuoli, Portici, Torre del Greco), da fare solo con
   informazioni vere su ciascun comune, altrimenti sono fotocopie inutili.

## Regole del progetto, da rispettare

- **Non inventare nulla**: niente prezzi, certificazioni, assicurazioni, anni
  di attivita' o numeri che non ti ho dato io. Dove manca un dato, il sito lo
  omette.
- **Recensioni**: solo quelle vere della scheda Google, riportate alla
  lettera, refusi compresi. **Mai** dichiararle come valutazione media nei
  dati strutturati: Google vieta l'auto-attribuzione del punteggio a stelle.
- **NAP identico ovunque**: `Sorgente Traslochi`, `Via Cupa Vicinale
  dell'Arco, 72, 80144 Napoli (NA)`, `347 263 6504`, orari lunedi'-sabato
  8:00-20:00. Devono coincidere con la scheda Google, virgole comprese.
- **Foto**: controlla sempre l'inquadratura prima di pubblicarla. In una foto
  compariva il mezzo di un'altra ditta di traslochi con l'indirizzo del suo
  sito leggibile, ed e' stata ritagliata.
- **Verifica prima di dire che e' fatto**: rigenera, controlla l'HTML, e dopo
  la pubblicazione controlla il sito dal vivo. Piu' volte una risposta
  positiva di un'API non corrispondeva a quello che si vedeva davvero.

## Come lavoriamo

- ogni modifica: commit sul ramo di lavoro, pull request verso il ramo di
  produzione, merge. **Le modifiche di routine** (foto, ritocchi ai testi,
  correzioni) **le unisci tu senza chiedermelo**; per dati aziendali, nuove
  pagine, prezzi o affermazioni commerciali, chiedimi prima.
- messaggi di commit e descrizioni delle PR in italiano, che spieghino
  **perche'**, non solo cosa.
- parlami in italiano, in modo diretto. Se qualcosa che chiedo e' sbagliato,
  dimmelo.

## Note pratiche sull'ambiente

- il server Wix e' collegato via MCP: il vecchio sito e'
  `3bfb5f67-49b2-41ba-bcca-b66006f8cf0c`, la fascia-ponte e' un custom embed
  con id `099c46c1-fb05-4ba6-9886-071228d5dc5c`
- non ho accesso ai miei account Google: Search Console e scheda Google
  Business li tocco io, tu mi guidi passo passo
- per misurare con Lighthouse: servire `sito/dist` in locale, perche' il
  proxy di rete dell'ambiente fa fallire la verifica del certificato sui siti
  esterni
