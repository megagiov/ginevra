# Studio PT

Prenotazioni per uno studio di personal training con **una sala**: lezioni da
60 minuti, individuali o di gruppo fino a 4 posti, crediti gestiti a mano
dall'amministratore, disdetta gratuita entro 24 ore.

Nessun servizio cloud a pagamento: gira su un NAS con Docker.

## Stato

| Parte | Stato |
|---|---|
| Schema del database, regole e RLS | completo e testato (34 asserzioni + test di concorrenza) |
| Impianto Docker per il NAS | scritto, non ancora provato su hardware |
| Applicazione web (PWA) | da fare |

## Com'e' fatto

```
app (PWA)  ──HTTPS──▶  NAS ──▶ PostgreSQL
  iOS / Android            Docker
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

Serve PostgreSQL 16 (o Docker).

```bash
createdb studio_dev
psql -d studio_dev -f db/migrations/0000_auth.sql
psql -d studio_dev -f db/migrations/0001_schema.sql
psql -d studio_dev -f db/migrations/0002_regole.sql
```

### Test

```bash
psql -d studio_dev -f db/test/01_regole.sql   # 34 asserzioni sulle regole
./db/test/02_concorrenza.sh studio_dev        # 8 clienti, 4 posti, stesso istante
```

`01_regole.sql` esce con errore se anche una sola asserzione fallisce, quindi
si puo' usare in una pipeline. `02_concorrenza.sh` apre otto connessioni
reali che partono allo stesso secondo: verifica che la corsa all'ultimo posto
del gruppo non produca sovrapprenotazioni ne' crediti scalati a vuoto.

## Installazione sul NAS

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
