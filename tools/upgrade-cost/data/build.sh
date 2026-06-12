#!/usr/bin/env bash
# Rebuild upgrade-cost.json from game data pulled direct from Goodgame Studios. Needs curl + python3.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
bash "$here/../../_srcdata/pull.sh"
python3 "$here/extract.py"
