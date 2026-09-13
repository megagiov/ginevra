#!/usr/bin/env bash
# ============================================================================
#  Otto clienti prenotano NELLO STESSO ISTANTE un gruppo da quattro posti.
#  Devono passarne esattamente quattro. Non e' una simulazione: sono otto
#  connessioni separate al database che partono allo stesso secondo.
#
#  Uso:  ./02_concorrenza.sh <nome_database>
# ============================================================================
set -uo pipefail

DB="${1:-studio_test}"
SLOT='00000000-0000-0000-0000-0000000f0001'
POSTI=4
CLIENTI=8

q() { psql -X -q -t -A -d "$DB" "$@"; }

# --- preparazione -----------------------------------------------------------
q -c "delete from movimenti where nota = 'concorrenza';" >/dev/null
q -c "
  delete from prenotazioni where slot_id = '$SLOT';
  delete from slot where id = '$SLOT';
  insert into slot (id, inizio, fine, tipo, capienza)
  values ('$SLOT', now() + interval '9 days',
          now() + interval '9 days' + interval '60 min', 'gruppo', $POSTI);
" >/dev/null

ADMIN=$(q -c "select id from profili where ruolo = 'admin' limit 1")

for i in $(seq 1 $CLIENTI); do
  UID_C=$(printf '00000000-0000-0000-0000-0000000f00%02d' "$i")
  q -c "
    insert into auth.users (id, email) values ('$UID_C', 'gara$i@test.it')
      on conflict (id) do nothing;
    set app.utente_id = '$ADMIN';
    select accredita('$UID_C', 'gruppo', 1, null, 'concorrenza');
  " >/dev/null
done

# --- la gara ----------------------------------------------------------------
# Tutti i processi attendono lo stesso istante di partenza, cosi' la contesa
# sull'ultimo posto e' reale e non dipende dall'ordine di avvio.
VIA=$(( $(date +%s) + 3 ))
ESITI=$(mktemp -d)

for i in $(seq 1 $CLIENTI); do
  UID_C=$(printf '00000000-0000-0000-0000-0000000f00%02d' "$i")
  (
    while [ "$(date +%s)" -lt "$VIA" ]; do :; done
    if psql -X -q -t -A -d "$DB" \
         -c "set app.utente_id = '$UID_C'; select prenota('$SLOT');" >/dev/null 2>&1
    then echo ok > "$ESITI/$i"
    else echo ko > "$ESITI/$i"
    fi
  ) &
done
wait

# --- verifica ---------------------------------------------------------------
RIUSCITE=$(grep -l ok "$ESITI"/* 2>/dev/null | wc -l)
POSTI_OCCUPATI=$(q -c "select count(*) from prenotazioni
                        where slot_id = '$SLOT' and stato <> 'disdetta'")
CREDITI_SPESI=$(q -c "select count(*) from movimenti
                       where causale = 'prenotazione'
                         and prenotazione_id in (select id from prenotazioni
                                                  where slot_id = '$SLOT')")
rm -rf "$ESITI"

echo "prenotazioni riuscite : $RIUSCITE  (attese $POSTI)"
echo "posti occupati        : $POSTI_OCCUPATI  (attesi $POSTI)"
echo "crediti scalati       : $CREDITI_SPESI  (attesi $POSTI)"

if [ "$RIUSCITE" -eq "$POSTI" ] && [ "$POSTI_OCCUPATI" -eq "$POSTI" ] \
   && [ "$CREDITI_SPESI" -eq "$POSTI" ]; then
  echo "PASS  nessuna sovrapprenotazione, nessun credito scalato a vuoto"
  exit 0
else
  echo "FAIL  il vincolo di capienza non ha retto alla concorrenza"
  exit 1
fi
