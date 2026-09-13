#!/usr/bin/env bash
# ===========================================================================
#  Percorso completo del cliente, via HTTP, come da telefono:
#  accesso con link email, prenotazione, disdetta, saldo.
# ===========================================================================
set -uo pipefail

APP="$(cd "$(dirname "$0")/.." && pwd)"
PORTA="${PORTA:-8099}"
export DB_NAME="${DB_NAME:-studio_test}"
export DB_USER="${DB_USER:-root}"
export DB_HOST="${DB_HOST:-localhost}"
export BASE_URL="http://127.0.0.1:$PORTA"
export SMTP_HOST=""

PASSATI=0; FALLITI=0
ok() { if [ "$2" = "1" ]; then echo "PASS  $1"; PASSATI=$((PASSATI+1));
       else echo "FAIL  $1"; FALLITI=$((FALLITI+1)); fi; }

contiene() { grep -qF "$2" <<<"$1" && echo 1 || echo 0; }

mysql_q() { mariadb -N -B -u "$DB_USER" -h "$DB_HOST" "$DB_NAME" -e "$1"; }

# --- preparazione ---------------------------------------------------------
php "$APP/test/prepara-schermate.php" || exit 1

php -S "127.0.0.1:$PORTA" -t "$APP" "$APP/test/server-prova.php" >/tmp/server-prova.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
for _ in $(seq 1 40); do
  curl -s -o /dev/null "http://127.0.0.1:$PORTA/accedi" && break
  sleep 0.25
done

BISCOTTI=$(mktemp)
C=(curl -s -c "$BISCOTTI" -b "$BISCOTTI" -w '\n%{http_code}|%{redirect_url}')

# --- 1. senza sessione ----------------------------------------------------
R=$("${C[@]}" -o /dev/null "http://127.0.0.1:$PORTA/")
ok "Senza sessione la home rimanda all'accesso" "$(contiene "$R" '302|http://127.0.0.1:'"$PORTA"'/accedi')"

R=$("${C[@]}" "http://127.0.0.1:$PORTA/accedi")
ok "La pagina di accesso chiede l'email" "$(contiene "$R" 'Mandami il link')"
# Cio' che conta non e' la parola "password" (la pagina dice proprio che non
# serve), ma che non esista nessun campo in cui digitarne una.
ok "E non c'e' nessun campo password" "$([ "$(grep -c 'type="password"' <<<"$R")" = "0" ] && echo 1 || echo 0)"

# --- 2. richiesta del link ------------------------------------------------
R=$("${C[@]}" -o /dev/null -d 'email=anna@test.it' "http://127.0.0.1:$PORTA/accedi")
ok "La richiesta del link risponde con un redirect" "$(contiene "$R" 'inviata=1')"

R=$("${C[@]}" -o /dev/null -d 'email=sconosciuta@test.it' "http://127.0.0.1:$PORTA/accedi")
ok "Un'email sconosciuta riceve la stessa risposta" "$(contiene "$R" 'inviata=1')"

# --- 3. entrata -----------------------------------------------------------
TOKEN=$(php "$APP/test/token-di-prova.php" anna@test.it)
R=$("${C[@]}" -o /dev/null "http://127.0.0.1:$PORTA/entra?token=$TOKEN")
ok "Il link apre la sessione" "$(contiene "$R" '303|')"
ok "Il cookie di sessione e' HttpOnly" "$(grep -q 'HttpOnly' "$BISCOTTI" && echo 1 || echo 0)"

R=$("${C[@]}" -o /dev/null "http://127.0.0.1:$PORTA/entra?token=$TOKEN")
ok "Lo stesso link non riapre una seconda sessione" "$(contiene "$R" 'errore=')"

# --- 4. prenotazione ------------------------------------------------------
PAGINA=$("${C[@]}" "http://127.0.0.1:$PORTA/")
ok "La home mostra le lezioni disponibili"  "$(contiene "$PAGINA" 'Prenota una lezione')"
ok "Con l'orario della lezione"             "$(contiene "$PAGINA" '18:00')"
ok "E i posti liberi scritti, non solo colorati" "$(contiene "$PAGINA" 'posti liberi')"
ok "Il saldo e' visibile prima di prenotare" "$(contiene "$PAGINA" 'lezioni individuali')"

GETTONE=$(grep -o 'name="gettone" value="[^"]*"' <<<"$PAGINA" | head -1 | cut -d'"' -f4)
SLOT=$(grep -o 'name="slot" value="[^"]*"' <<<"$PAGINA" | head -1 | cut -d'"' -f4)

R=$("${C[@]}" -o /dev/null -d "gettone=$GETTONE&slot=$SLOT" "http://127.0.0.1:$PORTA/prenota")
ok "La prenotazione va a buon fine" "$(contiene "$R" 'esito=')"
ok "Ed e' registrata nel database" "$([ "$(mysql_q "SELECT COUNT(*) FROM prenotazioni WHERE stato='prenotata' AND cliente_id='c1'")" = "1" ] && echo 1 || echo 0)"
ok "Il credito e' stato scalato"   "$([ "$(mysql_q "SELECT COALESCE(SUM(delta),0) FROM movimenti WHERE cliente_id='c1' AND tipo='gruppo'")" = "9" ] && echo 1 || echo 0)"

R=$("${C[@]}" -o /dev/null -d "slot=$SLOT" "http://127.0.0.1:$PORTA/prenota")
ok "Senza gettone la richiesta viene rifiutata" "$(contiene "$R" '400|')"

# --- 5. le mie lezioni e disdetta ----------------------------------------
PAGINA=$("${C[@]}" "http://127.0.0.1:$PORTA/prenotazioni")
ok "La lezione compare fra le mie"        "$(contiene "$PAGINA" 'Disdici')"
ok "Con il termine di disdetta scritto"   "$(contiene "$PAGINA" 'Disdetta gratuita entro')"

GETTONE=$(grep -o 'name="gettone" value="[^"]*"' <<<"$PAGINA" | head -1 | cut -d'"' -f4)
PREN=$(grep -o 'name="prenotazione" value="[^"]*"' <<<"$PAGINA" | head -1 | cut -d'"' -f4)

R=$("${C[@]}" -o /dev/null -d "gettone=$GETTONE&prenotazione=$PREN" "http://127.0.0.1:$PORTA/disdici")
ok "La disdetta va a buon fine" "$(contiene "$R" 'esito=')"
ok "Il credito e' tornato"      "$([ "$(mysql_q "SELECT COALESCE(SUM(delta),0) FROM movimenti WHERE cliente_id='c1' AND tipo='gruppo'")" = "10" ] && echo 1 || echo 0)"

# --- 6. saldo -------------------------------------------------------------
PAGINA=$("${C[@]}" "http://127.0.0.1:$PORTA/saldo")
ok "Il saldo elenca i movimenti"         "$(contiene "$PAGINA" 'Movimenti')"
ok "Compresa la disdetta entro i termini" "$(contiene "$PAGINA" 'Disdetta entro i termini')"
ok "E la ricarica iniziale"               "$(contiene "$PAGINA" 'Ricarica')"

# --- 7. i dati di un altro cliente non si vedono -------------------------
ALTRUI=$(mysql_q "SELECT id FROM prenotazioni WHERE cliente_id='c2' LIMIT 1")
R=$("${C[@]}" -o /dev/null -d "gettone=$GETTONE&prenotazione=$ALTRUI" "http://127.0.0.1:$PORTA/disdici")
ok "Non si disdice la prenotazione di un altro cliente" "$(contiene "$R" 'errore=')"
ok "E quella prenotazione e' ancora viva" "$([ "$(mysql_q "SELECT stato FROM prenotazioni WHERE id='$ALTRUI'")" = "prenotata" ] && echo 1 || echo 0)"

PAGINA=$("${C[@]}" "http://127.0.0.1:$PORTA/saldo")
ok "Il saldo non mostra movimenti altrui" "$([ "$(grep -c 'Bruno' <<<"$PAGINA")" = "0" ] && echo 1 || echo 0)"

# --- 8. uscita ------------------------------------------------------------
GETTONE=$(grep -o 'name="gettone" value="[^"]*"' <<<"$PAGINA" | head -1 | cut -d'"' -f4)
R=$("${C[@]}" -o /dev/null -d "gettone=$GETTONE" "http://127.0.0.1:$PORTA/esci")
R=$("${C[@]}" -o /dev/null "http://127.0.0.1:$PORTA/")
ok "Dopo l'uscita si torna alla pagina di accesso" "$(contiene "$R" '/accedi')"

rm -f "$BISCOTTI"
echo
echo "$PASSATI passati, $FALLITI falliti, $((PASSATI+FALLITI)) totali"
[ "$FALLITI" -eq 0 ]
