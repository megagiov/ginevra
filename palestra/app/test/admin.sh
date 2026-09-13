#!/usr/bin/env bash
# ===========================================================================
#  Schermate amministratore, percorse via HTTP.
# ===========================================================================
set -uo pipefail

APP="$(cd "$(dirname "$0")/.." && pwd)"
PORTA="${PORTA:-8097}"
export DB_NAME="${DB_NAME:-studio_test}"
export DB_USER="${DB_USER:-root}"
export DB_HOST="${DB_HOST:-localhost}"
export BASE_URL="http://127.0.0.1:$PORTA"
export SMTP_HOST=""

PASSATI=0; FALLITI=0
ok() { if [ "$2" = "1" ]; then echo "PASS  $1"; PASSATI=$((PASSATI+1));
       else echo "FAIL  $1"; FALLITI=$((FALLITI+1)); fi; }
contiene() { grep -qF "$2" <<<"$1" && echo 1 || echo 0; }
uguale()   { [ "$1" = "$2" ] && echo 1 || echo 0; }
mysql_q()  { mariadb -N -B -u "$DB_USER" -h "$DB_HOST" "$DB_NAME" -e "$1"; }
gettone()  { grep -o 'name="gettone" value="[^"]*"' <<<"$1" | head -1 | cut -d'"' -f4; }

php "$APP/test/prepara-admin.php" || exit 1

php -S "127.0.0.1:$PORTA" -t "$APP" "$APP/test/server-prova.php" >/tmp/server-admin.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
for _ in $(seq 1 40); do curl -s -o /dev/null "http://127.0.0.1:$PORTA/accedi" && break; sleep 0.25; done

U="http://127.0.0.1:$PORTA"

# --- 1. un cliente non entra nell'area riservata --------------------------
BC=$(mktemp); CL=(curl -s -c "$BC" -b "$BC" -w '\n%{http_code}')
TK=$(php "$APP/test/token-di-prova.php" anna@test.it)
"${CL[@]}" -o /dev/null "$U/entra?token=$TK" >/dev/null

R=$("${CL[@]}" -o /dev/null "$U/admin")
ok "Un cliente non accede all'area amministratore" "$(contiene "$R" '403')"
R=$("${CL[@]}" -o /dev/null "$U/admin/clienti")
ok "Nemmeno all'elenco clienti"                    "$(contiene "$R" '403')"
R=$("${CL[@]}" -o /dev/null -d 'nome=X&email=x@y.it' "$U/admin/clienti")
ok "Nemmeno creando clienti via POST"              "$(contiene "$R" '403')"

# --- 2. accesso amministratore -------------------------------------------
BA=$(mktemp); A=(curl -s -c "$BA" -b "$BA" -w '\n%{http_code}|%{redirect_url}')
TK=$(php "$APP/test/token-di-prova.php" admin@studio.test)
"${A[@]}" -o /dev/null "$U/entra?token=$TK" >/dev/null

R=$("${A[@]}" -o /dev/null "$U/")
ok "Per l'amministratore la home e' la sua agenda" "$(contiene "$R" '/admin')"

P=$("${A[@]}" "$U/admin")
ok "L'agenda mostra la barra dell'amministratore" "$(contiene "$P" 'Calendario')"
ok "Con la lezione di oggi"                       "$(contiene "$P" 'Gruppo')"
ok "E il nome di chi e' prenotato"                "$(contiene "$P" 'Anna Rossi')"
ok "Segnala le presenze da registrare"            "$(contiene "$P" 'da registrare')"

# --- 3. presenze ----------------------------------------------------------
G=$(gettone "$P")
PREN=$(mysql_q "SELECT id FROM prenotazioni WHERE cliente_id='c1' LIMIT 1")
OGGI=$(date +%F)
R=$("${A[@]}" -o /dev/null -d "gettone=$G&prenotazione=$PREN&presente=1&giorno=$OGGI" "$U/admin/presenza")
ok "L'amministratore segna la presenza" "$(uguale "$(mysql_q "SELECT stato FROM prenotazioni WHERE id='$PREN'")" 'presente')"
ok "E la presenza non muove crediti"    "$(uguale "$(mysql_q "SELECT COUNT(*) FROM movimenti WHERE cliente_id='c1'")" '3')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&prenotazione=$PREN&presente=0&giorno=$OGGI" "$U/admin/presenza")
ok "E puo' correggersi"                 "$(uguale "$(mysql_q "SELECT stato FROM prenotazioni WHERE id='$PREN'")" 'assente')"

# --- 4. pubblicazione della disponibilita' --------------------------------
P=$("${A[@]}" "$U/admin/calendario")
G=$(gettone "$P")
LUN=$(date -d 'next monday' +%F)

R=$("${A[@]}" -o /dev/null -d "gettone=$G&da=$LUN&data=$LUN&ora=07:00&tipo=gruppo&capienza=4&ripetizioni=4" "$U/admin/slot")
ok "Pubblica quattro settimane in un colpo" "$(uguale "$(mysql_q "SELECT COUNT(*) FROM slot WHERE tipo='gruppo' AND id<>'oggi1'")" '4')"
# Le ripetizioni si contano in giorni locali, non in ore: fra una e l'altra
# devono passare esattamente sette giorni anche a cavallo del cambio d'ora.
ok "A distanza di sette giorni l'una dall'altra" "$(uguale "$(mysql_q "SELECT COUNT(DISTINCT DATEDIFF(inizio, (SELECT MIN(inizio) FROM (SELECT inizio FROM slot WHERE tipo='gruppo' AND id<>'oggi1') x)) % 7) FROM slot WHERE tipo='gruppo' AND id<>'oggi1'")" '1')"
ok "Le lezioni create sono di gruppo da 4"  "$(uguale "$(mysql_q "SELECT COUNT(DISTINCT capienza) FROM slot WHERE tipo='gruppo' AND id<>'oggi1'")" '1')"

# La stessa ora, di nuovo: la sala e' occupata, va saltata.
R=$("${A[@]}" -o /dev/null -d "gettone=$G&da=$LUN&data=$LUN&ora=07:00&tipo=individuale&capienza=1&ripetizioni=1" "$U/admin/slot")
ok "Una sovrapposizione viene rifiutata e spiegata" "$(contiene "$R" 'errore=')"
ok "E non crea nulla" "$(uguale "$(mysql_q "SELECT COUNT(*) FROM slot WHERE tipo='individuale' AND id<>'fut1'")" '0')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&da=$LUN&data=$LUN&ora=09:00&tipo=gruppo&capienza=9&ripetizioni=1" "$U/admin/slot")
ok "Un gruppo da 9 posti viene rifiutato" "$(contiene "$R" 'errore=')"

# --- 5. chiusura ed eliminazione -----------------------------------------
SLOT=$(mysql_q "SELECT id FROM slot WHERE tipo='gruppo' AND id<>'oggi1' ORDER BY inizio LIMIT 1")
R=$("${A[@]}" -o /dev/null -d "gettone=$G&slot=$SLOT&da=$LUN&stato=chiuso" "$U/admin/slot/stato")
ok "Una lezione si puo' chiudere alle prenotazioni" "$(uguale "$(mysql_q "SELECT stato FROM slot WHERE id='$SLOT'")" 'chiuso')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&slot=$SLOT&da=$LUN" "$U/admin/slot/elimina")
ok "E si puo' eliminare se e' vuota" "$(uguale "$(mysql_q "SELECT COUNT(*) FROM slot WHERE id='$SLOT'")" '0')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&slot=oggi1&da=$LUN" "$U/admin/slot/elimina")
ok "Ma non se qualcuno l'ha prenotata"  "$(contiene "$R" 'errore=')"
ok "E quella lezione resta in calendario" "$(uguale "$(mysql_q "SELECT COUNT(*) FROM slot WHERE id='oggi1'")" '1')"

# --- 6. clienti -----------------------------------------------------------
P=$("${A[@]}" "$U/admin/clienti")
G=$(gettone "$P")
ok "L'elenco clienti mostra i saldi"  "$(contiene "$P" 'ind.')"
ok "E segnala chi e' in esaurimento"  "$(contiene "$P" 'in esaurimento')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&nome=Carla Verdi&email=carla@test.it&telefono=333222&note=Principiante" "$U/admin/clienti")
ok "Crea un cliente nuovo" "$(uguale "$(mysql_q "SELECT COUNT(*) FROM utenti WHERE email='carla@test.it'")" '1')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&nome=Doppione&email=carla@test.it" "$U/admin/clienti")
ok "E rifiuta un'email gia' usata" "$(contiene "$R" 'errore=')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&nome=Senza&email=non-una-email" "$U/admin/clienti")
ok "E rifiuta un'email malformata" "$(contiene "$R" 'errore=')"

# Il cliente nuovo entra da solo, senza che gli sia comunicata una password.
TKC=$(php "$APP/test/token-di-prova.php" carla@test.it)
ok "Il cliente nuovo riceve subito il suo link" "$([ -n "$TKC" ] && echo 1 || echo 0)"

# --- 7. scheda cliente: crediti e prenotazione per suo conto -------------
P=$("${A[@]}" "$U/admin/cliente?id=c1")
G=$(gettone "$P")
ok "La scheda mostra le note del cliente" "$(contiene "$P" 'Spalla destra da riabilitare')"
ok "E il suo telefono"                    "$(contiene "$P" '333111')"
ok "E lo storico dei movimenti"           "$(contiene "$P" 'Pacchetto iniziale')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&cliente=c1&quantita=10&tipo=gruppo&causale=acquisto&importo=250.00&nota=Rinnovo" "$U/admin/accredita")
ok "La ricarica aggiorna il saldo (5-1+10=14)" "$(uguale "$(mysql_q "SELECT COALESCE(SUM(delta),0) FROM movimenti WHERE cliente_id='c1' AND tipo='gruppo'")" '14')"
ok "E registra l'importo incassato" "$(uguale "$(mysql_q "SELECT COUNT(*) FROM movimenti WHERE cliente_id='c1' AND importo_eur=250.00")" '1')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&cliente=c1&quantita=-2&tipo=gruppo&causale=acquisto" "$U/admin/accredita")
ok "Un acquisto negativo viene rifiutato" "$(contiene "$R" 'errore=')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&cliente=c1&quantita=-2&tipo=gruppo&causale=rettifica&nota=Storno" "$U/admin/accredita")
ok "Una rettifica negativa invece passa (14-2=12)" "$(uguale "$(mysql_q "SELECT COALESCE(SUM(delta),0) FROM movimenti WHERE cliente_id='c1' AND tipo='gruppo'")" '12')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&cliente=c1&slot=fut1" "$U/admin/prenota")
ok "L'amministratore prenota per conto del cliente" "$(uguale "$(mysql_q "SELECT COUNT(*) FROM prenotazioni WHERE slot_id='fut1' AND cliente_id='c1'")" '1')"
ok "E il credito individuale e' stato scalato"      "$(uguale "$(mysql_q "SELECT COALESCE(SUM(delta),0) FROM movimenti WHERE cliente_id='c1' AND tipo='individuale'")" '0')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&cliente=c2&slot=fut1" "$U/admin/prenota")
ok "Ma non oltre i posti disponibili" "$(contiene "$R" 'errore=')"

# --- 8. disattivazione ----------------------------------------------------
R=$("${A[@]}" -o /dev/null -d "gettone=$G&cliente=c1&attivo=0" "$U/admin/cliente/attivazione")
ok "Disattiva un cliente" "$(uguale "$(mysql_q "SELECT attivo FROM utenti WHERE id='c1'")" '0')"
ok "E gli chiude subito le sessioni aperte" "$(uguale "$(mysql_q "SELECT COUNT(*) FROM sessioni WHERE utente_id='c1'")" '0')"

R=$("${CL[@]}" -o /dev/null "$U/prenotazioni")
ok "Il cliente disattivato torna alla pagina di accesso" "$(contiene "$R" '302')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&cliente=a1&attivo=0" "$U/admin/cliente/attivazione")
ok "L'amministratore non puo' disattivare se stesso" "$(contiene "$R" 'errore=')"

rm -f "$BA" "$BC"
echo
echo "$PASSATI passati, $FALLITI falliti, $((PASSATI+FALLITI)) totali"
[ "$FALLITI" -eq 0 ]
