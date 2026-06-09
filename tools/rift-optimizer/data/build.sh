#!/usr/bin/env bash
# Rebuild rift.json from the community game-data cache. Needs curl + python3.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
curl -sL "https://raw.githubusercontent.com/GeneralsCamp/ggempire-data-cache/main/public/data/empire/dll/ggs.dll.latest.js" -o "$tmp/ggs.dll.js"
python3 "$here/extract.py" "$tmp/ggs.dll.js"
echo "Done."
