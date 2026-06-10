#!/usr/bin/env bash
# Rebuild loot-boxes.json from the community game-data cache. Needs curl + jq + python3.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
base="https://raw.githubusercontent.com/GeneralsCamp/ggempire-data-cache/main/public/data"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
curl -sL "$base/lang/en.json" | jq -c 'with_entries(.key|=ascii_downcase)' > "$tmp/en.json"
curl -sL "$base/empire/items_latest.json" -o "$tmp/items.json"
curl -sL "$base/empire/dll/ggs.dll.latest.js" -o "$tmp/ggs.dll.js"
jq --slurpfile lang "$tmp/en.json" -f "$here/extract.jq" "$tmp/items.json" > "$here/loot-boxes.json"
python3 "$here/add_images.py" "$tmp/ggs.dll.js" "$here/loot-boxes.json"
echo "Wrote loot-boxes.json — $(jq '.boxes|length' "$here/loot-boxes.json") boxes."
