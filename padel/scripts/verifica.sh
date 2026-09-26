#!/usr/bin/env bash
# Genera il progetto, esegue i test del motore e compila i due target sui
# simulatori. Non serve alcuna firma. Uso: scripts/verifica.sh
set -euo pipefail
cd "$(dirname "$0")/.."

IPHONE_SIM="${IPHONE_SIM:-iPhone 17}"
WATCH_SIM="${WATCH_SIM:-Apple Watch Ultra 3 (49mm)}"

if ! command -v xcodegen >/dev/null; then
  echo "▸ Installo XcodeGen con Homebrew"
  brew install xcodegen
fi

echo "▸ Genero Padel.xcodeproj"
xcodegen generate --quiet

echo "▸ Test del motore di punteggio (PadelKit)"
swift test --package-path PadelKit

# Usa il simulatore indicato (per UDID, il nome con le parentesi confonde
# xcodebuild), con il sistema piu' recente; altrimenti uno generico.
destination() {
  local platform="$1" name="$2" udid
  udid="$(xcrun simctl list devices available -j | /usr/bin/python3 -c '
import json, sys
name = sys.argv[1]
found = [(rt, d["udid"]) for rt, ds in json.load(sys.stdin)["devices"].items() for d in ds if d["name"] == name]
print(sorted(found)[-1][1] if found else "")' "$name")"
  if [[ -n "$udid" ]]; then
    echo "platform=$platform Simulator,id=$udid"
  else
    echo "generic/platform=$platform Simulator"
  fi
}

COMMON=(-project Padel.xcodeproj -configuration Debug CODE_SIGNING_ALLOWED=NO
        SWIFT_TREAT_WARNINGS_AS_ERRORS=YES -quiet)

for hk in YES NO; do
  echo "▸ Build iPhone + Watch incorporato (HealthKit=$hk) su: $(destination iOS "$IPHONE_SIM")"
  xcodebuild build -scheme Padel -destination "$(destination iOS "$IPHONE_SIM")" "${COMMON[@]}" PADEL_HEALTHKIT=$hk
  echo "▸ Build Watch (HealthKit=$hk) su: $(destination watchOS "$WATCH_SIM")"
  xcodebuild build -scheme PadelWatch -destination "$(destination watchOS "$WATCH_SIM")" "${COMMON[@]}" PADEL_HEALTHKIT=$hk
done

echo "▸ Test PadelKit anche sul simulatore iPhone"
(cd PadelKit && xcodebuild test -scheme PadelKit -destination "$(destination iOS "$IPHONE_SIM")" -quiet)

echo "✓ Tutto verde"
