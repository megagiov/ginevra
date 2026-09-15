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

# Il link dell'email ora e' un primo tocco (GET, non consuma) piu' un invio
# vero (POST): serve a non farsi bruciare il codice monouso da uno scanner
# di posta che apre il link da solo. I test rifanno lo stesso doppio passo.
entra_con_token() {
  local jar="$1" token="$2"
  local pagina token_campo
  pagina=$(curl -s -c "$jar" -b "$jar" "$U/entra?token=$token")
  token_campo=$(grep -o 'name="token" value="[^"]*"' <<<"$pagina" | head -1 | cut -d'"' -f4)
  curl -s -c "$jar" -b "$jar" -o /dev/null -d "token=$token_campo" "$U/entra"
}

php "$APP/test/prepara-admin.php" || exit 1

php -S "127.0.0.1:$PORTA" -t "$APP" "$APP/test/server-prova.php" >/tmp/server-admin.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
for _ in $(seq 1 40); do curl -s -o /dev/null "http://127.0.0.1:$PORTA/accedi" && break; sleep 0.25; done

U="http://127.0.0.1:$PORTA"

# --- 1. un cliente non entra nell'area riservata --------------------------
BC=$(mktemp); CL=(curl -s -c "$BC" -b "$BC" -w '\n%{http_code}')
TK=$(php "$APP/test/token-di-prova.php" anna@test.it)
entra_con_token "$BC" "$TK"

R=$("${CL[@]}" -o /dev/null "$U/admin")
ok "Un cliente non accede all'area amministratore" "$(contiene "$R" '403')"
R=$("${CL[@]}" -o /dev/null "$U/admin/clienti")
ok "Nemmeno all'elenco clienti"                    "$(contiene "$R" '403')"
R=$("${CL[@]}" -o /dev/null -d 'nome=X&email=x@y.it' "$U/admin/clienti")
ok "Nemmeno creando clienti via POST"              "$(contiene "$R" '403')"
R=$("${CL[@]}" -o /dev/null "$U/admin/impostazioni")
ok "Nemmeno alle impostazioni"                     "$(contiene "$R" '403')"

# --- 2. accesso amministratore -------------------------------------------
BA=$(mktemp); A=(curl -s -c "$BA" -b "$BA" -w '\n%{http_code}|%{redirect_url}')
TK=$(php "$APP/test/token-di-prova.php" admin@studio.test)
entra_con_token "$BA" "$TK"

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

R=$("${A[@]}" -o /dev/null -d "gettone=$G&da=$LUN&giorni[]=1&ore[]=07:00&tipo=gruppo&capienza=4&ripetizioni=4" "$U/admin/slot")
ok "Pubblica quattro settimane in un colpo" "$(uguale "$(mysql_q "SELECT COUNT(*) FROM slot WHERE tipo='gruppo' AND id<>'oggi1'")" '4')"
# Le ripetizioni si contano in giorni locali, non in ore: fra una e l'altra
# devono passare esattamente sette giorni anche a cavallo del cambio d'ora.
ok "A distanza di sette giorni l'una dall'altra" "$(uguale "$(mysql_q "SELECT COUNT(DISTINCT DATEDIFF(inizio, (SELECT MIN(inizio) FROM (SELECT inizio FROM slot WHERE tipo='gruppo' AND id<>'oggi1') x)) % 7) FROM slot WHERE tipo='gruppo' AND id<>'oggi1'")" '1')"
ok "Le lezioni create sono di gruppo da 4"  "$(uguale "$(mysql_q "SELECT COUNT(DISTINCT capienza) FROM slot WHERE tipo='gruppo' AND id<>'oggi1'")" '1')"

# La stessa ora e lo stesso tipo: quel tipo e' occupato, va saltato.
R=$("${A[@]}" -o /dev/null -d "gettone=$G&da=$LUN&giorni[]=1&ore[]=07:00&tipo=gruppo&capienza=4&ripetizioni=1" "$U/admin/slot")
ok "Una sovrapposizione dello stesso tipo viene rifiutata e spiegata" "$(contiene "$R" 'errore=')"
ok "E non crea nulla in piu'" "$(uguale "$(mysql_q "SELECT COUNT(*) FROM slot WHERE tipo='gruppo' AND id<>'oggi1'")" '4')"

# Con un secondo maestro, un'individuale nello stesso orario di un gruppo va bene.
R=$("${A[@]}" -o /dev/null -d "gettone=$G&da=$LUN&giorni[]=1&ore[]=07:00&tipo=individuale&capienza=1&ripetizioni=1" "$U/admin/slot")
ok "Un'individuale nello stesso orario di un gruppo (due maestri) viene accettata" \
   "$(uguale "$(mysql_q "SELECT COUNT(*) FROM slot WHERE tipo='individuale' AND id<>'fut1'")" '1')"

# "Entrambi" pubblica le due lezioni in un colpo solo.
R=$("${A[@]}" -o /dev/null -d "gettone=$G&da=$LUN&giorni[]=1&ore[]=10:00&tipo=entrambi&capienza=3&ripetizioni=1" "$U/admin/slot")
ok "\"Entrambi\" pubblica anche un'individuale in piu'" "$(uguale "$(mysql_q "SELECT COUNT(*) FROM slot WHERE tipo='individuale' AND id<>'fut1'")" '2')"
ok "\"Entrambi\" pubblica anche un gruppo in piu'" "$(uguale "$(mysql_q "SELECT COUNT(*) FROM slot WHERE tipo='gruppo' AND id<>'oggi1'")" '5')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&da=$LUN&giorni[]=1&ore[]=09:00&tipo=gruppo&capienza=9&ripetizioni=1" "$U/admin/slot")
ok "Un gruppo da 9 posti viene rifiutato" "$(contiene "$R" 'errore=')"

# Piu' giorni e piu' ore in un solo invio: il prodotto di ogni combinazione.
PRIMA=$(mysql_q "SELECT COUNT(*) FROM slot WHERE tipo='individuale'")
R=$("${A[@]}" -o /dev/null -d "gettone=$G&da=$LUN&giorni[]=2&giorni[]=4&ore[]=11:00&ore[]=12:00&tipo=individuale&capienza=1&ripetizioni=1" "$U/admin/slot")
DOPO=$(mysql_q "SELECT COUNT(*) FROM slot WHERE tipo='individuale'")
ok "Piu' giorni e piu' ore pubblicano tutte le combinazioni (2x2=4)" "$(uguale "$((DOPO - PRIMA))" '4')"

# "Ripeti per" ripete lo stesso schema di giorni/ore anche nelle settimane dopo.
PRIMA=$(mysql_q "SELECT COUNT(*) FROM slot WHERE tipo='individuale'")
R=$("${A[@]}" -o /dev/null -d "gettone=$G&da=$LUN&giorni[]=6&ore[]=07:00&tipo=individuale&capienza=1&ripetizioni=2" "$U/admin/slot")
DOPO=$(mysql_q "SELECT COUNT(*) FROM slot WHERE tipo='individuale'")
ok "\"Ripeti per\" ripete lo schema anche nella settimana dopo (2 sabati)" "$(uguale "$((DOPO - PRIMA))" '2')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&da=$LUN&ore[]=07:00&tipo=individuale&capienza=1&ripetizioni=1" "$U/admin/slot")
ok "Senza nessun giorno spuntato viene rifiutato" "$(contiene "$R" 'errore=')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&da=$LUN&giorni[]=3&tipo=individuale&capienza=1&ripetizioni=1" "$U/admin/slot")
ok "Senza nessun'ora spuntata viene rifiutato" "$(contiene "$R" 'errore=')"

# --- 5. chiusura ed eliminazione -----------------------------------------
SLOT=$(mysql_q "SELECT id FROM slot WHERE tipo='gruppo' AND id<>'oggi1' ORDER BY inizio LIMIT 1")
R=$("${A[@]}" -o /dev/null -d "gettone=$G&slot=$SLOT&da=$LUN&stato=chiuso" "$U/admin/slot/stato")
ok "Una lezione si puo' chiudere alle prenotazioni" "$(uguale "$(mysql_q "SELECT stato FROM slot WHERE id='$SLOT'")" 'chiuso')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&slot=$SLOT&da=$LUN" "$U/admin/slot/elimina")
ok "E si puo' eliminare se e' vuota" "$(uguale "$(mysql_q "SELECT COUNT(*) FROM slot WHERE id='$SLOT'")" '0')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&slot=oggi1&da=$LUN" "$U/admin/slot/elimina")
ok "Ma non se qualcuno l'ha prenotata"  "$(contiene "$R" 'errore=')"
ok "E quella lezione resta in calendario" "$(uguale "$(mysql_q "SELECT COUNT(*) FROM slot WHERE id='oggi1'")" '1')"

# --- 5b. cancellazione multipla ---------------------------------------------
PRIMA=$(mysql_q "SELECT COUNT(*) FROM slot WHERE tipo='individuale'")
R=$("${A[@]}" -o /dev/null -d "gettone=$G&da=$LUN&giorni[]=2&giorni[]=4&ore[]=11:00&ore[]=12:00&tipo=individuale&ripetizioni=1" "$U/admin/slot/cancella")
DOPO=$(mysql_q "SELECT COUNT(*) FROM slot WHERE tipo='individuale'")
ok "Cancella in blocco le lezioni vuote che corrispondono (2x2=4)" "$(uguale "$((PRIMA - DOPO))" '4')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&da=$LUN&giorni[]=2&ore[]=11:00&tipo=individuale&ripetizioni=1" "$U/admin/slot/cancella")
ok "Rifatta sulle stesse ore, non trova piu' nulla da cancellare" "$(contiene "$R" 'errore=')"

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
ok "Prenota per suo conto fa scegliere prima il giorno" "$(contiene "$P" 'id="giorno-prenota"')"

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

# --- 7b. piano alimentare e allenamento -----------------------------------
P=$("${CL[@]}" "$U/piano")
ok "Senza un piano scritto il cliente vede il messaggio di default" \
   "$(contiene "$P" 'non ha ancora scritto un piano')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&cliente=c1&alimentare=Colazione+proteica&allenamento=" "$U/admin/cliente/piano")
ok "L'amministratore scrive il piano alimentare" \
   "$(uguale "$(mysql_q "SELECT piano_alimentare FROM utenti WHERE id='c1'")" 'Colazione proteica')"
ok "Un campo lasciato vuoto resta NULL, non stringa vuota" \
   "$(uguale "$(mysql_q "SELECT piano_allenamento IS NULL FROM utenti WHERE id='c1'")" '1')"

P=$("${A[@]}" "$U/admin/cliente?id=c1")
ok "La scheda cliente mostra il piano appena scritto" "$(contiene "$P" 'Colazione proteica')"

P=$("${CL[@]}" "$U/piano")
ok "Il cliente vede il proprio piano alimentare" "$(contiene "$P" 'Colazione proteica')"
ok "Ma non la sezione allenamento, che e' vuota" "$(uguale "$(contiene "$P" 'Allenamento a casa')" '0')"

CL2=$(mktemp); C2=(curl -s -c "$CL2" -b "$CL2" -w '\n%{http_code}')
TK2=$(php "$APP/test/token-di-prova.php" bruno@test.it)
entra_con_token "$CL2" "$TK2"
R=$("${C2[@]}" -o /dev/null -d "gettone=$G&cliente=c1&alimentare=Rubo+il+piano&allenamento=" "$U/admin/cliente/piano")
ok "Un cliente non puo' scrivere il piano di un altro" "$(contiene "$R" '403')"
rm -f "$CL2"

# --- 8. impostazioni --------------------------------------------------------
P=$("${A[@]}" "$U/admin/impostazioni")
G=$(gettone "$P")
ok "La pagina mostra il valore attuale della finestra di disdetta" \
   "$(contiene "$P" 'value="24"')"
ok "E la barra dell'amministratore ha la voce Impostazioni" \
   "$(contiene "$P" 'Impostazioni')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&finestra_disdetta_ore=12&anticipo_minimo_ore=1&max_prenotazioni_aperte=6&giorni_visibili=21" "$U/admin/impostazioni")
ok "Salva le nuove impostazioni" \
   "$(uguale "$(mysql_q "SELECT valore FROM impostazioni WHERE chiave='finestra_disdetta_ore'")" '12')"
ok "Tutte e quattro le chiavi" \
   "$(uguale "$(mysql_q "SELECT GROUP_CONCAT(valore ORDER BY chiave) FROM impostazioni")" '1,12,21,6')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&finestra_disdetta_ore=12&anticipo_minimo_ore=1&max_prenotazioni_aperte=0&giorni_visibili=21" "$U/admin/impostazioni")
ok "Rifiuta un valore fuori dai limiti (zero prenotazioni aperte)" "$(contiene "$R" 'errore=')"
ok "E non scrive nulla di quel tentativo" \
   "$(uguale "$(mysql_q "SELECT valore FROM impostazioni WHERE chiave='max_prenotazioni_aperte'")" '6')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&finestra_disdetta_ore=abc&anticipo_minimo_ore=1&max_prenotazioni_aperte=6&giorni_visibili=21" "$U/admin/impostazioni")
ok "Rifiuta un valore non numerico" "$(contiene "$R" 'errore=')"

R=$("${CL[@]}" -o /dev/null -d "finestra_disdetta_ore=1&anticipo_minimo_ore=1&max_prenotazioni_aperte=6&giorni_visibili=21" "$U/admin/impostazioni")
ok "Un cliente non puo' cambiare le impostazioni" "$(contiene "$R" '403')"

# --- 8b. maestri ------------------------------------------------------------
R=$("${A[@]}" -o /dev/null -d "gettone=$G&nome=" "$U/admin/maestri")
ok "Rifiuta un nome vuoto" "$(contiene "$R" 'errore=')"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&nome=Marco" "$U/admin/maestri")
ok "Crea un maestro" "$(uguale "$(mysql_q "SELECT COUNT(*) FROM maestri WHERE nome='Marco'")" '1')"
MID_MARCO=$(mysql_q "SELECT id FROM maestri WHERE nome='Marco'")

P=$("${A[@]}" "$U/admin/impostazioni")
ok "L'elenco maestri mostra quello appena creato" "$(contiene "$P" 'Marco')"

# Bruno non ha ancora nessun credito individuale: gliene serve per le prove.
R=$("${A[@]}" -o /dev/null -d "gettone=$G&cliente=c2&quantita=5&tipo=individuale&causale=omaggio" "$U/admin/accredita")

# Un solo maestro candidato: l'assegnazione e' automatica, il cliente non sceglie nulla.
R=$("${A[@]}" -o /dev/null -d "gettone=$G&da=$LUN&giorni[]=1&ore[]=08:00&tipo=individuale&capienza=1&ripetizioni=1&maestri_individuale[]=$MID_MARCO" "$U/admin/slot")
SLOT_MARCO=$(mysql_q "SELECT slot_id FROM slot_maestri GROUP BY slot_id HAVING COUNT(*) = 1")
ok "Pubblica la lezione con il maestro candidato" "$([ -n "$SLOT_MARCO" ] && echo 1 || echo 0)"

BB=$(mktemp); B=(curl -s -c "$BB" -b "$BB" -w '\n%{http_code}|%{redirect_url}')
TKB=$(php "$APP/test/token-di-prova.php" bruno@test.it)
entra_con_token "$BB" "$TKB"
PB=$("${B[@]}" "$U/")
GB=$(gettone "$PB")

R=$("${B[@]}" -o /dev/null -d "gettone=$GB&slot=$SLOT_MARCO" "$U/prenota")
ok "Il cliente prenota senza dover scegliere il maestro (ce n'e' uno solo)" \
   "$(uguale "$(mysql_q "SELECT maestro_id FROM prenotazioni WHERE slot_id='$SLOT_MARCO' AND cliente_id='c2'")" "$MID_MARCO")"

# Due maestri candidati: stavolta la scelta e' del cliente.
R=$("${A[@]}" -o /dev/null -d "gettone=$G&nome=Giulia" "$U/admin/maestri")
MID_GIULIA=$(mysql_q "SELECT id FROM maestri WHERE nome='Giulia'")

R=$("${A[@]}" -o /dev/null -d "gettone=$G&da=$LUN&giorni[]=1&ore[]=09:00&tipo=individuale&capienza=1&ripetizioni=1&maestri_individuale[]=$MID_MARCO&maestri_individuale[]=$MID_GIULIA" "$U/admin/slot")
SLOT_DOPPIO=$(mysql_q "SELECT slot_id FROM slot_maestri GROUP BY slot_id HAVING COUNT(*) = 2")
ok "Pubblica la lezione con due maestri candidati" "$([ -n "$SLOT_DOPPIO" ] && echo 1 || echo 0)"

R=$("${B[@]}" -o /dev/null -d "gettone=$GB&slot=$SLOT_DOPPIO" "$U/prenota")
ok "Senza scegliere il maestro la prenotazione viene rifiutata" "$(contiene "$R" 'errore=')"

R=$("${B[@]}" -o /dev/null --data-urlencode "maestro_$SLOT_DOPPIO=$MID_GIULIA" -d "gettone=$GB&slot=$SLOT_DOPPIO" "$U/prenota")
ok "Scegliendo Giulia la prenotazione risulta a suo nome" \
   "$(uguale "$(mysql_q "SELECT maestro_id FROM prenotazioni WHERE slot_id='$SLOT_DOPPIO' AND cliente_id='c2'")" "$MID_GIULIA")"

P=$("${B[@]}" "$U/prenotazioni")
ok "Il cliente vede con chi ha la lezione, nelle sue prenotazioni" "$(contiene "$P" 'con Giulia')"

# Disattivare un maestro non tocca dove e' gia' assegnato, ma sparisce dalle nuove scelte.
R=$("${A[@]}" -o /dev/null -d "gettone=$G&maestro=$MID_GIULIA&attivo=0" "$U/admin/maestro/attivazione")
ok "Disattiva un maestro" "$(uguale "$(mysql_q "SELECT attivo FROM maestri WHERE id='$MID_GIULIA'")" '0')"
ok "La prenotazione di Bruno con Giulia resta valida" \
   "$(uguale "$(mysql_q "SELECT maestro_id FROM prenotazioni WHERE slot_id='$SLOT_DOPPIO' AND cliente_id='c2'")" "$MID_GIULIA")"

P=$("${A[@]}" "$U/admin/calendario")
ok "Un maestro disattivato non compare piu' tra le scelte per una nuova lezione" \
   "$([ "$(grep -c "value=\"$MID_GIULIA\"" <<<"$P")" = "0" ] && echo 1 || echo 0)"

R=$("${A[@]}" -o /dev/null -d "gettone=$G&da=$LUN&giorni[]=1&ore[]=08:00&tipo=individuale&ripetizioni=1" "$U/admin/slot/cancella")
ok "La cancellazione in blocco non tocca una lezione gia' prenotata" \
   "$(uguale "$(mysql_q "SELECT COUNT(*) FROM slot WHERE id='$SLOT_MARCO'")" '1')"
ok "E lo dice, invece di sparire in silenzio" "$(contiene "$R" 'errore=')"

rm -f "$BB"

# --- 9. disattivazione ----------------------------------------------------
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
