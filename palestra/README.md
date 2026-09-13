# Studio PT

Prenotazioni per uno studio di personal training con **una sala**: lezioni da
60 minuti, individuali o di gruppo fino a 4 posti, crediti gestiti a mano
dall'amministratore, disdetta gratuita entro 24 ore.

Gira sull'hosting Aruba Linux gia' in uso (PHP 8.3 + MySQL), su un
sottodominio dedicato. Nessun servizio cloud a pagamento.

## Stato

| Parte | Stato |
|---|---|
| Schema MySQL e vincoli | completo — 26 asserzioni verdi |
| Regole di prenotazione in PHP | complete — 24 asserzioni verdi |
| Interfaccia web (PWA) | da fare |
| Accesso via link email | tabelle pronte, logica da scrivere |

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
php app/test/regole.php                                 # 24 — le regole in PHP
```

`regole.php` ricrea il database indicato da `DB_NAME` (default `studio_test`)
a ogni esecuzione: non puntarlo mai a un database vero. Esce con codice 1 se
anche una sola asserzione fallisce.

### Attenzione alla versione di MySQL

Su **MySQL 5.7 i vincoli CHECK vengono accettati e poi ignorati in silenzio**:
lo schema si installa ma meta' delle garanzie non esiste. La prima asserzione
di `01_vincoli.sql` verifica proprio questo, quindi eseguila sul server di
Aruba prima di fidarti dello schema.

## Installazione su Aruba

1. Crea un sottodominio `studio.<dominio>` con la sua cartella.
2. Crea un database MySQL **separato da quello di WordPress**, con un
   utente dedicato.
3. Carica `app/` via FTP e applica `db/mysql/migrations/0001_schema.sql`
   da phpMyAdmin.
4. Configura le credenziali (vedi `app/config.example.php`).

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
