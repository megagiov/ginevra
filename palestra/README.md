# Studio PT

Prenotazioni per uno studio di personal training con **una sala**: lezioni da
60 minuti, individuali o di gruppo fino a 4 posti, crediti gestiti a mano
dall'amministratore, disdetta gratuita entro 24 ore.

Gira sull'hosting Aruba Linux gia' in uso (PHP 8.3 + MySQL), su un
sottodominio dedicato. Nessun servizio cloud a pagamento.

## Stato

| Parte | Stato |
|---|---|
| Schema MySQL e vincoli | completo — 26 asserzioni |
| Regole di prenotazione in PHP | complete — 24 asserzioni |
| Accesso con link via email | completo — 27 asserzioni |
| Schermate cliente (PWA) | complete — 28 asserzioni end-to-end |
| Schermate amministratore | complete — 41 asserzioni end-to-end |
| Installazione in sottocartella | supportata — 24 asserzioni |

**170 asserzioni verdi in totale.**

Sette schermate, una sola applicazione: il ruolo decide cosa si vede.

- **Cliente** — prenota, le mie lezioni, saldo
- **Amministratore** — oggi (agenda e presenze), calendario (pubblica la
  disponibilita'), clienti, scheda cliente (crediti, prenotazione per suo
  conto, storico)

L'accesso avviene con un link inviato per email, senza password. Il primo
tocco del link (GET) non consuma nulla: mostra una pagina con un pulsante
"Entra", e solo l'invio di quel modulo (POST) apre davvero la sessione.
Niente invio automatico via JavaScript: alcuni controlli antiphishing
aprono il link ed eseguono anche lo script della pagina, quindi un invio
automatico verrebbe consumato da loro. Serve perche' Gmail e molti
antivirus aprono da soli i link dentro un'email per controllarli prima
che il cliente li clicchi — se quell'apertura consumasse il codice
monouso, il cliente vero si troverebbe sempre un link "gia' usato".

### Due implementazioni

`db/mysql/` e' quella in uso, per l'hosting Aruba. `db/postgres/` e' la
versione PostgreSQL da cui nasce il progetto: li' le regole stanno dentro il
database e sono inaggirabili, qui stanno in PHP perche' MySQL non ha ne'
Row Level Security ne' vincoli di esclusione. Serve se un domani il progetto
si sposta su un VPS.

## Com'e' fatto

```
PWA  ──HTTPS──▶  studio.<dominio>  ──▶  MySQL
iOS / Android     PHP 8.3 su Aruba        database dedicato
```

Una sola PWA serve sia i clienti sia l'amministratore: il ruolo decide cosa
si vede. Si apre dal browser e si aggiunge alla schermata home — niente
store, niente file da installare, niente quota annuale per gli sviluppatori.

## Le regole, in breve

1. Senza credito del tipo giusto non si prenota.
2. Il credito si scala **alla prenotazione**, non alla presenza.
3. Disdetta oltre 24 ore: credito restituito. Sotto: perso.
4. Anticipo minimo per prenotare: 2 ore.
5. Massimo 4 prenotazioni future aperte per cliente.

Sono tutte in `impostazioni`, modificabili senza rilasciare una nuova
versione, e applicate dal **database**, non dall'interfaccia: non esiste una
policy di scrittura su `prenotazioni` e `movimenti`, si passa solo dalle
funzioni `prenota()`, `disdici()`, `segna_presenza()` e `accredita()`.

## Il saldo e' una somma, non un contatore

Nessuna colonna `lezioni_residue`. Ogni variazione e' una riga in
`movimenti` con la sua causale, e il saldo e' la somma dei delta. Quando una
cliente chiede *"perche' me ne risulta una in meno?"*, la risposta e' una
riga con data, causale e autore.

## Sviluppo

Serve MySQL 8 o MariaDB 10.3+ e PHP 8.1+.

```bash
mariadb -e "CREATE DATABASE studio_dev CHARACTER SET utf8mb4"
mariadb studio_dev < db/mysql/migrations/0001_schema.sql
```

### Test

```bash
mariadb -t studio_test < db/mysql/test/01_vincoli.sql   # 26 — cosa garantisce il database
php app/test/regole.php                                 # 24 — le regole di prenotazione
php app/test/accesso.php                                # 27 — accesso senza password
bash app/test/schermate.sh                              # 28 — percorso cliente via HTTP
bash app/test/admin.sh                                  # 41 — percorso amministratore
bash app/test/sottocartella.sh                          # 24 — app dentro una sottocartella
```

`schermate.sh` avvia il server integrato di PHP e percorre l'app come
farebbe un telefono: richiesta del link, entrata, prenotazione, disdetta,
saldo, uscita. Verifica anche che un cliente non veda ne' possa toccare i
dati di un altro.

`regole.php` ricrea il database indicato da `DB_NAME` (default `studio_test`)
a ogni esecuzione: non puntarlo mai a un database vero. Esce con codice 1 se
anche una sola asserzione fallisce.

### Attenzione alla versione di MySQL

Su **MySQL 5.7 i vincoli CHECK vengono accettati e poi ignorati in silenzio**:
lo schema si installa ma meta' delle garanzie non esiste. La prima asserzione
di `01_vincoli.sql` verifica proprio questo, quindi eseguila sul server di
Aruba prima di fidarti dello schema.

## Installazione su Aruba

1. Crea un sottodominio `studio.<dominio>` con la sua cartella — oppure
   usa una sottocartella del sito (`<dominio>/studio`): l'app riconosce da
   sola il prefisso.

   > Su alcuni hosting (verificato su Aruba) il server riporta un percorso
   > diverso dopo la riscrittura degli indirizzi, e il rilevamento
   > automatico fallisce: i fogli di stile non caricano e i link portano
   > fuori dalla cartella. In quel caso basta dichiararlo in `config.php`:
   >
   > ```php
   > 'base_path' => 'studio',
   > ```
2. Crea un database MySQL **separato da quello di WordPress**, con un
   utente dedicato.
3. Applica `db/mysql/migrations/0001_schema.sql` da phpMyAdmin.
4. Copia `app/config.example.php` in `app/config.php` e compilalo.
5. Carica il contenuto di `app/` via FTP nella cartella del sottodominio.
   Le cartelle `src/`, `pagine/` e `test/` hanno gia' il loro `.htaccess`
   che ne nega l'accesso dal browser; `test/` puoi anche non caricarla.
6. Apri `https://<sottodominio>/verifica.php` nel browser: elenca tutto
   cio' che deve funzionare e dice cosa manca. **Cancella quel file dal
   server appena hai finito.** Con `?posta=tuo@indirizzo.it` prova anche
   l'invio delle email.
7. Crea il primo amministratore, da phpMyAdmin:

   ```sql
   INSERT INTO utenti (id, email, nome, ruolo)
   VALUES (UUID(), 'tua@email.it', 'Nome Cognome', 'admin');
   ```

   Poi entra dall'app con quell'indirizzo: riceverai il link di accesso.

Il motivo della separazione: l'app tratta PAR-Q e storico infortuni, che
sono dati sanitari. Un WordPress compromesso non deve poterci arrivare.

## In alternativa, sul NAS (percorso PostgreSQL)

1. Copia la cartella sul NAS.
2. Crea un file `.env` accanto a `docker-compose.yml`:

   ```
   DB_PASSWORD=...
   APP_DB_PASSWORD=...
   SESSION_SECRET=...            # stringa lunga e casuale
   BASE_URL=https://studio.tuodominio.it
   SMTP_HOST=...
   SMTP_USER=...
   SMTP_PASSWORD=...
   SMTP_MITTENTE="Studio <no-reply@tuodominio.it>"
   ```

3. `docker compose up -d`

Il database non pubblica porte: e' raggiungibile solo dall'applicazione.
Il backup gira da solo, un dump al giorno, trenta giorni di storico in
`dati/backup`.

### HTTPS obbligatorio

Una PWA **non funziona senza HTTPS**: niente installazione sulla schermata
home, niente notifiche. Serve un nome pubblico con certificato valido. Due
strade:

- **Cloudflare Tunnel** — non apre porte sul router, il NAS resta invisibile
  dall'esterno, certificato automatico. E' la via consigliata.
- **Reverse proxy del NAS** (Synology, QNAP) con Let's Encrypt e DDNS, piu'
  port forwarding 443. Funziona, ma espone il NAS.

### Il limite da conoscere

Se il NAS e' spento o la connessione dello studio cade, **nessuno puo'
prenotare** finche' non torna. Con cinquanta clienti e prenotazioni che si
fanno con giorni di anticipo e' un rischio accettabile; va sapendolo.
