#!/usr/bin/env bash
# Prove nel browser vero (Chromium via Playwright). Coprono il pannello, le
# schede, il catalogo, il battito, il backup, la condivisione, e simulano
# Safari su iPhone (niente vibrazione, menu Condividi, categoria audio).
#
#   npm i playwright                      # una volta sola, dove preferisci
#   NODE_PATH=<quella>/node_modules ./tests/run.sh
#
# CHROMIUM_PATH  percorso di un Chromium gia' installato (facoltativo)
# PALESTRA_URL   indirizzo dell'app (predefinito: server locale sulla 8777)
set -u
cd "$(dirname "$0")/.."
mkdir -p "${TMPDIR:-/tmp}/palestra-shots"
if ! curl -s -o /dev/null "${PALESTRA_URL:-http://127.0.0.1:8777/index.html}"; then
  python3 -m http.server 8777 --bind 127.0.0.1 >/dev/null 2>&1 &
  SERVER=$!
  trap 'kill $SERVER 2>/dev/null' EXIT
  sleep 1
fi
fallite=0
for t in tests/*.test.js; do
  echo "######## $t"
  node "$t" || fallite=$((fallite + 1))
done
echo
[ "$fallite" -eq 0 ] && echo "Tutte le suite passate." || echo "$fallite suite con errori."
exit "$fallite"
