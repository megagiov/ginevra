#!/usr/bin/env bash
# Compila e installa Padel su iPhone (e Apple Watch) collegati, firmando
# con il Personal Team gratuito. Da rilanciare ogni 7 giorni, quando il
# profilo gratuito scade. I dati NON si perdono: si reinstalla sopra.
#
# Uso:
#   scripts/reinstalla.sh          compila e installa
#   scripts/reinstalla.sh --team   mostra i Team ID disponibili sul Mac
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--team" ]]; then
  echo "Certificati di sviluppo sul Mac (il Team ID e' il valore OU=):"
  security find-certificate -a -c "Apple Development" -p 2>/dev/null \
    | awk '/BEGIN/{c=""} {c=c $0 "\n"} /END/{print c | "openssl x509 -noout -subject"; close("openssl x509 -noout -subject")}' \
    | sed -E 's/.*OU ?= ?([A-Z0-9]{10}).*/\1/' | sort -u
  echo "Se non compare nulla: apri Xcode > Settings > Accounts, aggiungi il tuo Apple ID e compila una volta da Xcode."
  exit 0
fi

if [[ ! -f Config/Signing.local.xcconfig ]]; then
  echo "Manca Config/Signing.local.xcconfig."
  echo "Copialo da Config/Signing.local.xcconfig.example e inserisci Team ID e prefisso bundle."
  exit 1
fi

command -v xcodegen >/dev/null || brew install xcodegen
xcodegen generate --quiet

echo "▸ Compilo per dispositivo (firma automatica con il Personal Team)"
xcodebuild build \
  -project Padel.xcodeproj -scheme Padel -configuration Debug \
  -destination 'generic/platform=iOS' \
  -derivedDataPath build \
  -allowProvisioningUpdates -allowProvisioningDeviceRegistration \
  -quiet

APP="build/Build/Products/Debug-iphoneos/Padel.app"
WATCH_APP="$APP/Watch/PadelWatch.app"

# Elenca i dispositivi collegati (cavo o stessa rete) con devicectl.
JSON="$(mktemp)"
xcrun devicectl list devices --json-output "$JSON" >/dev/null
read_device() {
  /usr/bin/python3 - "$JSON" "$1" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
wanted = sys.argv[2]
for d in data.get("result", {}).get("devices", []):
    hw = d.get("hardwareProperties", {})
    conn = d.get("connectionProperties", {})
    if hw.get("platform") == wanted and conn.get("pairingState") == "paired":
        print(d["identifier"]); break
PY
}
IPHONE="${IPHONE_ID:-$(read_device iOS)}"
WATCH="${WATCH_ID:-$(read_device watchOS)}"
rm -f "$JSON"

if [[ -z "$IPHONE" ]]; then
  echo "Nessun iPhone trovato. Collegalo col cavo, sbloccalo e rispondi 'Autorizza' se richiesto."
  exit 1
fi

echo "▸ Installo sull'iPhone ($IPHONE)"
xcrun devicectl device install app --device "$IPHONE" "$APP"

if [[ -n "$WATCH" ]]; then
  echo "▸ Installo sull'Apple Watch ($WATCH)"
  xcrun devicectl device install app --device "$WATCH" "$WATCH_APP" \
    || echo "  Installazione diretta non riuscita: apri l'app Watch sull'iPhone > Padel > Installa."
else
  echo "▸ Watch non visibile a devicectl: l'app arriva dall'iPhone (app Watch > Padel > Installa)."
fi

echo "✓ Fatto. Il profilo gratuito scade tra 7 giorni: rilancia questo script prima di allora."
