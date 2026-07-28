#!/usr/bin/env bash
# Rebuild the real-money offer catalogue from game data pulled direct from
# Goodgame Studios. Writes BOTH tools/spenders/data/sales.json (Spenders Corner)
# and tools/item-value/data/packages.json (Item Value Finder).
#
# Note: the AUD pack prices in data/au-prices.json are hand-captured from the
# in-game AU1 shop and are NOT refreshed here — they need a human with the shop
# open. The page shows how old that capture is.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
bash "$here/../_srcdata/pull.sh"
python3 "$here/build.py"
