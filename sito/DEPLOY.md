# Pubblicazione e passaggi successivi

Tre parti: mettere online il sito, farlo indicizzare da Google, spegnere il
vecchio sito Wix. Tutto a costo zero.

Prima di cominciare: completa almeno i punti 1 e 2 di `DA-COMPLETARE.md`
(P.IVA, ragione sociale, ID Formspree, orari), poi rigenera con
`python3 build.py`.

---

## 1. Modulo preventivo (Formspree, gratuito)

Da fare prima della pubblicazione, altrimenti il modulo non invia nulla.

1. Vai su <https://formspree.io> e registrati con `sorgentetraslochi@gmail.com`.
2. Crea un nuovo form (New form), chiamalo "Preventivo sito".
3. Formspree mostra un endpoint tipo `https://formspree.io/f/abcdwxyz`:
   copia la parte finale (`abcdwxyz`).
4. In `sito/content.py` metti quel codice in `FORMSPREE_ID`.
5. Rigenera: `cd sito && python3 build.py`.
6. Dopo la pubblicazione manda una richiesta di prova dal sito e conferma
   l'email di verifica che Formspree invia la prima volta.

Il piano gratuito include 50 invii al mese. Se dovessero bastare appena, si
puo' valutare un'alternativa gratuita equivalente senza rifare il sito: cambia
solo l'indirizzo nell'attributo `action` del modulo.

---

## 2. Pubblicazione su Cloudflare Pages

Il sito e' gia' pronto: `sito/dist` contiene HTML statico, nessuna build da
eseguire sul server.

### Passo 1 — account

1. Vai su <https://dash.cloudflare.com/sign-up> e crea un account gratuito
   (bastano email e password, non serve carta di credito).
2. Conferma l'indirizzo email.

### Passo 2 — collega il repository

1. Nel pannello Cloudflare scegli **Workers & Pages** nel menu a sinistra.
2. **Create** > scheda **Pages** > **Connect to Git**.
3. Autorizza GitHub e seleziona il repository `megagiov/ginevra`.
4. Nella configurazione della build imposta:

   | Campo | Valore |
   | --- | --- |
   | Project name | `sorgentetraslochi` |
   | Production branch | il ramo su cui sta il sito (es. `main`) |
   | Framework preset | `None` |
   | Build command | *lasciare vuoto* |
   | Build output directory | `sito/dist` |

5. **Save and Deploy**. Dopo circa un minuto il sito e' online su
   `https://sorgentetraslochi.pages.dev`.

Il nome del progetto determina il sottodominio: se `sorgentetraslochi` fosse
gia' occupato, scegline un altro e aggiorna `BASE_URL` in `content.py`, poi
rigenera e ripubblica.

Da quel momento ogni push sul ramo di produzione ripubblica il sito da solo.

### Alternativa senza Git

Se preferisci non passare da GitHub: **Workers & Pages > Create > Pages >
Upload assets**, trascina il contenuto della cartella `sito/dist` (il
contenuto, non la cartella) e pubblica. Gli aggiornamenti successivi si fanno
ricaricando i file a mano.

### Passo 3 — verifica

Apri il sito e controlla:

- si vede su telefono senza scorrimento laterale;
- il pulsante Chiama apre il telefono, WhatsApp apre la chat;
- il modulo preventivo invia davvero (fai una prova e controlla la posta);
- `https://sorgentetraslochi.pages.dev/sitemap.xml` si apre;
- il footer mostra P.IVA e orari reali, non i segnaposto.

### Passo 4 — dominio .it (quando lo vorrete)

Il sito e' gia' predisposto e non va rifatto nulla:

1. Registra il dominio presso un registrar (costo del dominio, non di
   Cloudflare).
2. In Cloudflare: **Workers & Pages > sorgentetraslochi > Custom domains >
   Set up a domain**, inserisci il dominio e segui le istruzioni per puntare
   i DNS a Cloudflare.
3. Il certificato HTTPS viene emesso da Cloudflare, gratuito e automatico.
4. In `content.py` cambia `BASE_URL` nel nuovo dominio, rigenera e ripubblica:
   canonical, sitemap e Open Graph si aggiornano.
5. Cloudflare mantiene attivo anche `pages.dev`: imposta un redirect 301 dal
   sottodominio al dominio nuovo (Rules > Redirect Rules) per non dividere il
   posizionamento fra due indirizzi.
6. Aggiorna il link su Google Business, Facebook e Instagram.

---

## 3. Google Search Console

Serve a far indicizzare il sito e a vedere con quali ricerche vi trovano.

1. Vai su <https://search.google.com/search-console> ed entra con l'account
   Google dell'azienda (lo stesso della scheda Google Business).
2. **Aggiungi proprieta'** > tipo **Prefisso URL** > incolla
   `https://sorgentetraslochi.pages.dev` (piu' avanti aggiungerai il dominio
   .it come proprieta' separata).
3. Verifica con il metodo **Tag HTML**: Google mostra una riga tipo
   `<meta name="google-site-verification" content="...">`. Mandatemela e la
   inserisco in `build.py`, oppure incollatela voi nel blocco `DOC` subito
   dopo `<meta name="viewport" ...>` e rigenerate.
   In alternativa, se siete gia' proprietari verificati della scheda Google
   Business, provate prima la verifica automatica: spesso non serve altro.
4. A verifica avvenuta: **Sitemap** nel menu a sinistra, inserisci
   `sitemap.xml` e invia.
5. **Controllo URL** in alto: incolla l'indirizzo della home e premi
   **Richiedi indicizzazione**. Ripeti per le pagine principali (traslochi
   abitazioni, uffici, montaggio, sgomberi, zone servite).

L'indicizzazione richiede da qualche giorno a un paio di settimane. Dopo un
mese, in Search Console > Rendimento, si vedono le ricerche che portano
visite: e' li' che si capisce quali pagine rafforzare.

---

## 4. Scheda Google Business

La scheda e' gia' attiva (e' quella collegata a
<https://maps.google.com/?cid=16215080151173160187>): per un'attivita' locale
vale quanto il sito, quindi conviene curarla.

1. Vai su <https://business.google.com> ed entra con l'account proprietario
   della scheda.
2. **Modifica profilo > Informazioni sull'attivita' > Contatti > Sito web**:
   sostituisci l'indirizzo Wix con `https://sorgentetraslochi.pages.dev`
   (e in futuro con il dominio .it).
3. Nella stessa schermata controlla che nome, indirizzo e telefono siano
   **identici, carattere per carattere**, a quelli del sito:

   ```
   Sorgente Traslochi
   Via Cupa Vicinale dell'Arco 72, 80144 Napoli (NA)
   347 263 6504
   ```

   Google incrocia questi dati con quelli del sito: se coincidono, la scheda
   si posiziona meglio nelle ricerche locali.
4. Compila **Orari di apertura** con gli stessi orari messi sul sito.
5. In **Servizi** aggiungi le voci corrispondenti alle pagine: traslochi
   abitazioni, traslochi uffici, montaggio mobili, sgomberi, deposito mobili.
6. In **Aree servite** inserisci Napoli e i comuni della pagina zone servite.
7. Carica qualche **foto reale** (mezzi, squadra, lavori finiti): le schede
   con foto recenti ricevono piu' contatti.
8. Chiedete una **recensione** ai clienti soddisfatti, con il link che trovate
   in **Chiedi recensioni**. Le recensioni Google sono il fattore che sposta
   di piu' il posizionamento locale, piu' del sito stesso.

---

## 5. Dismissione del vecchio sito Wix

Da fare **solo dopo** che il nuovo sito e' online e funzionante, mai prima.

`sorgentetraslochi.wixsite.com/website`

1. **Non cancellate subito il sito Wix.** Finche' i due siti coesistono,
   Google potrebbe considerarli concorrenti sulle stesse ricerche.
2. Entrate su <https://www.wix.com> con l'account che gestisce il sito.
3. Nell'editor, sostituite il contenuto della home con poche righe e un
   collegamento al nuovo indirizzo, per esempio:

   > Il nostro sito si e' trasferito: ora siamo su
   > sorgentetraslochi.pages.dev. Per preventivi: 347 263 6504.

   Pubblicate. Cosi' chi arriva dal vecchio indirizzo o dai vecchi link vi
   trova comunque.
4. Verificate che nessun altro posto punti ancora al vecchio indirizzo:
   Facebook (Informazioni > Sito web), Instagram (bio), firma email,
   biglietti da visita, adesivi sui mezzi, eventuali annunci online.
5. Cercate su Google `site:sorgentetraslochi.wixsite.com`: vi mostra quante
   pagine Wix sono ancora indicizzate. Man mano che il nuovo sito viene
   indicizzato, quelle spariranno.
6. Dopo **due o tre mesi**, quando in Search Console il nuovo sito riceve
   visite stabili, potete chiudere il sito Wix (Impostazioni del sito >
   Elimina, oppure semplicemente togliete la pubblicazione). Se il piano Wix
   e' a pagamento, disdite il rinnovo automatico.

Nota: il piano gratuito di Wix non permette redirect 301 verso un dominio
esterno. La pagina-ponte del punto 3 e' il sostituto praticabile.

---

## Manutenzione

- **Aggiornare un testo**: modifica `sito/content.py`, esegui
  `python3 build.py`, fai commit e push. Cloudflare ripubblica da solo.
- **Costi ricorrenti**: zero. Cloudflare Pages e Formspree restano gratuiti
  nei limiti d'uso indicati; l'unico costo eventuale e' il dominio .it
  (circa 10-15 euro l'anno presso un registrar).
- **Backup**: il sito e' interamente nel repository Git, non serve altro.
