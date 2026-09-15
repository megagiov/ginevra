#!/usr/bin/env bash
# ===========================================================================
#  L'app installata in una sottocartella (www.dominio.it/studio) deve
#  funzionare come alla radice: link, moduli, cookie e risorse statiche.
# ===========================================================================
set -uo pipefail

APP="$(cd "$(dirname "$0")/.." && pwd)"
PORTA="${PORTA:-8093}"
export RADICE_SITO="${RADICE_SITO:-/tmp/sito-prova}"
export DB_NAME="${DB_NAME:-studio_test}" DB_USER="${DB_USER:-root}" DB_HOST="${DB_HOST:-localhost}"
export BASE_URL="http://127.0.0.1:$PORTA/studio" SMTP_HOST=""

PASSATI=0; FALLITI=0
ok() { if [ "$2" = "1" ]; then echo "PASS  $1"; PASSATI=$((PASSATI+1));
       else echo "FAIL  $1"; FALLITI=$((FALLITI+1)); fi; }
contiene() { grep -qF "$2" <<<"$1" && echo 1 || echo 0; }
manca()    { grep -qF "$2" <<<"$1" && echo 0 || echo 1; }

# Il link dell'email e' un primo tocco (GET, non consuma) piu' un invio vero
# (POST): serve a non farsi bruciare il codice monouso da uno scanner di
# posta che apre il link da solo, prima che il cliente lo clicchi davvero.
entra_con_token() {
  local pagina token_campo
  pagina=$("${C[@]}" "$U/entra?token=$1")
  token_campo=$(grep -o 'name="token" value="[^"]*"' <<<"$pagina" | head -1 | cut -d'"' -f4)
  "${C[@]}" -o /dev/null -d "token=$token_campo" "$U/entra"
}

rm -rf "$RADICE_SITO"; mkdir -p "$RADICE_SITO"
cp -r "$APP" "$RADICE_SITO/studio"

php "$APP/test/prepara-schermate.php" || exit 1

php -S "127.0.0.1:$PORTA" -t "$RADICE_SITO" "$APP/test/server-sottocartella.php" \
    >/tmp/server-sotto.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null; rm -rf "$RADICE_SITO"' EXIT
for _ in $(seq 1 40); do curl -s -o /dev/null "http://127.0.0.1:$PORTA/studio/accedi" && break; sleep 0.25; done

U="http://127.0.0.1:$PORTA/studio"
B=$(mktemp); C=(curl -s -c "$B" -b "$B" -w '\n%{http_code}|%{redirect_url}')

# --- accesso --------------------------------------------------------------
R=$("${C[@]}" -o /dev/null "$U/")
ok "Senza sessione rimanda a /studio/accedi" "$(contiene "$R" "/studio/accedi")"

P=$("${C[@]}" "$U/accedi")
ok "La pagina di accesso risponde"        "$(contiene "$P" 'Mandami il link')"
ok "Il foglio di stile punta a /studio"   "$(contiene "$P" 'href="/studio/stile.css?v=')"
ok "Il manifest punta a /studio"          "$(contiene "$P" 'href="/studio/manifest.json"')"
ok "Il modulo invia a /studio/accedi"     "$(contiene "$P" 'action="/studio/accedi"')"
ok "Nessun link punta fuori dalla cartella" "$(manca "$P" 'href="/stile.css"')"

TK=$(php "$APP/test/token-di-prova.php" anna@test.it)
P=$("${C[@]}" "$U/entra?token=$TK")
ok "La pagina di conferma resta dentro /studio" "$(contiene "$P" 'action="/studio/entra"')"
R=$(entra_con_token "$TK")
ok "L'invio del modulo apre la sessione" "$(contiene "$R" "/studio/")"
ok "Il cookie vale solo sotto /studio"   "$(grep -qE '/studio' "$B" && echo 1 || echo 0)"

# --- le risorse statiche esistono davvero --------------------------------
for f in stile.css manifest.json icona-180.png sw.js; do
  COD=$(curl -s -o /dev/null -w '%{http_code}' "$U/$f")
  ok "La risorsa $f risponde"  "$([ "$COD" = "200" ] && echo 1 || echo 0)"
done

# --- navigazione e prenotazione ------------------------------------------
P=$("${C[@]}" "$U/")
ok "La home mostra le lezioni"          "$(contiene "$P" 'Prenota una lezione')"
ok "La barra punta a /studio/saldo"     "$(contiene "$P" 'href="/studio/saldo"')"

G=$(grep -o 'name="gettone" value="[^"]*"' <<<"$P" | head -1 | cut -d'"' -f4)
S=$(grep -o 'name="slot" value="[^"]*"' <<<"$P" | head -1 | cut -d'"' -f4)

R=$("${C[@]}" -o /dev/null -d "gettone=$G&slot=$S" "$U/prenota")
ok "La prenotazione funziona e rimanda dentro /studio" "$(contiene "$R" "/studio/prenotazioni")"

P=$("${C[@]}" "$U/prenotazioni")
ok "La lezione compare fra le mie" "$(contiene "$P" 'Disdici')"

P=$("${C[@]}" "$U/saldo")
ok "Il saldo elenca i movimenti" "$(contiene "$P" 'Movimenti')"

# --- amministratore --------------------------------------------------------
#
# Questo e' il caso che il bug reale ha superato: un link con una variabile
# PHP incorporata (es. href="/admin/cliente?id=<?= ... ?>") non veniva
# corretto dal prefisso automatico, e restava puntato alla radice del
# dominio invece che dentro /studio. Alla radice il difetto e' invisibile
# perche' "/admin/..." e' gia' l'indirizzo giusto: si vede solo qui, con
# l'app dentro una sottocartella — esattamente come su Aruba.
BA=$(mktemp); AC=(curl -s -c "$BA" -b "$BA" -w '\n%{http_code}|%{redirect_url}')
entra_admin() {
  local pagina token_campo
  pagina=$("${AC[@]}" "$U/entra?token=$1")
  token_campo=$(grep -o 'name="token" value="[^"]*"' <<<"$pagina" | head -1 | cut -d'"' -f4)
  "${AC[@]}" -o /dev/null -d "token=$token_campo" "$U/entra"
}

TKA=$(php "$APP/test/token-di-prova.php" admin@studio.test)
entra_admin "$TKA" >/dev/null

P=$("${AC[@]}" "$U/admin")
ok "L'agenda dell'amministratore risponde dentro /studio" "$(contiene "$P" 'Calendario')"
ok "Le frecce di navigazione restano dentro /studio" "$(contiene "$P" "href=\"/studio/admin?giorno=")"

P=$("${AC[@]}" "$U/admin/calendario")
ok "Le frecce del calendario restano dentro /studio" "$(contiene "$P" "href=\"/studio/admin/calendario?da=")"

P=$("${AC[@]}" "$U/admin/clienti")
LINK_CLIENTE=$(grep -o 'href="/studio/admin/cliente?id=[^"]*"' <<<"$P" | head -1 | sed 's/href="//; s/"$//')
ok "Il link a un cliente resta dentro /studio, non alla radice del dominio" \
   "$([ -n "$LINK_CLIENTE" ] && echo 1 || echo 0)"

P=$("${AC[@]}" -o /dev/null "http://127.0.0.1:$PORTA$LINK_CLIENTE")
ok "Seguendo quel link si apre davvero la scheda cliente" "$(contiene "$P" '200')"

# --- diagnostica ----------------------------------------------------------
P=$(curl -s "$U/verifica.php")
ok "La diagnostica indica il percorso giusto" "$(contiene "$P" '/studio/accedi')"

rm -f "$B" "$BA"
echo
echo "$PASSATI passati, $FALLITI falliti, $((PASSATI+FALLITI)) totali"
[ "$FALLITI" -eq 0 ]
