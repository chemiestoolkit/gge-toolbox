#!/usr/bin/env bash
# Rebuild gacha-data.json from the community game-data cache.
# Run from anywhere; needs `curl` and `jq`.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
src="https://raw.githubusercontent.com/GeneralsCamp/ggempire-data-cache/main/public/data/empire/items_latest.json"

tmp="$(mktemp)"
echo "Downloading items_latest.json (~18 MB)…"
curl -sL "$src" -o "$tmp"
echo "Extracting gacha/loot-box pools…"
jq -f "$here/extract_gacha.jq" "$tmp" > "$here/gacha-data.json"
rm -f "$tmp"
echo "Done → $here/gacha-data.json"
jq -r '"pools: \(.pools|length)  events: \(.gachaEvents|length)  boxes: \(.lootBoxes|length)"' "$here/gacha-data.json"
