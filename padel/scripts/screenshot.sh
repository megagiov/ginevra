#!/usr/bin/env bash
# Scatta screenshot di iPhone e Apple Watch sui simulatori, con dati demo.
# Uso: scripts/screenshot.sh [cartella-output]
set -euo pipefail
set -x
cd "$(dirname "$0")/.."
OUT="${1:-screenshots}"
mkdir -p "$OUT"

udid() {
  xcrun simctl list devices available -j | /usr/bin/python3 -c '
import json, sys
name = sys.argv[1]
found = [(rt, d["udid"]) for rt, ds in json.load(sys.stdin)["devices"].items() for d in ds if d["name"] == name]
print(sorted(found)[-1][1] if found else "")' "$1"
}
IPHONE="$(udid "${IPHONE_SIM:-iPhone 17}")"
WATCH="$(udid "${WATCH_SIM:-Apple Watch Ultra 3 (49mm)}")"
[[ -n "$IPHONE" && -n "$WATCH" ]] || { echo "Simulatori non trovati"; exit 1; }

[[ -d Padel.xcodeproj ]] || xcodegen generate --quiet
echo "▸ Build per i simulatori"
xcodebuild build -project Padel.xcodeproj -scheme Padel -destination "platform=iOS Simulator,id=$IPHONE" -derivedDataPath build -quiet
xcodebuild build -project Padel.xcodeproj -scheme PadelWatch -destination "platform=watchOS Simulator,id=$WATCH" -derivedDataPath build -quiet

PHONE_APP=build/Build/Products/Debug-iphonesimulator/Padel.app
WATCH_APP=build/Build/Products/Debug-watchsimulator/PadelWatch.app
PHONE_ID=$(/usr/libexec/PlistBuddy -c 'Print CFBundleIdentifier' "$PHONE_APP/Info.plist")
WATCH_ID=$(/usr/libexec/PlistBuddy -c 'Print CFBundleIdentifier' "$WATCH_APP/Info.plist")

boot() { xcrun simctl boot "$1" 2>/dev/null || true; xcrun simctl bootstatus "$1" -b >/dev/null; }

echo "▸ iPhone"
boot "$IPHONE"
xcrun simctl status_bar "$IPHONE" override --time 9:41 --batteryState charged --batteryLevel 100 --cellularBars 4 --wifiBars 3 || true
xcrun simctl install "$IPHONE" "$PHONE_APP"
for tab in 0 1; do
  xcrun simctl terminate "$IPHONE" "$PHONE_ID" 2>/dev/null || true
  xcrun simctl launch "$IPHONE" "$PHONE_ID" -demo -tab "$tab" >/dev/null
  sleep 8
  xcrun simctl io "$IPHONE" screenshot "$OUT/iphone-$tab.png"
done

echo "▸ Apple Watch"
boot "$WATCH"
xcrun simctl install "$WATCH" "$WATCH_APP"
xcrun simctl launch "$WATCH" "$WATCH_ID" >/dev/null
sleep 8
xcrun simctl io "$WATCH" screenshot "$OUT/watch-setup.png"
xcrun simctl terminate "$WATCH" "$WATCH_ID" 2>/dev/null || true
xcrun simctl launch "$WATCH" "$WATCH_ID" -demo >/dev/null
sleep 8
xcrun simctl io "$WATCH" screenshot "$OUT/watch-segnapunti.png"

ls -la "$OUT"
