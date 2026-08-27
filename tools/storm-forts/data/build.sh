#!/usr/bin/env bash
# Rebuild storm-forts.json from game data pulled direct from Goodgame Studios.
# Reads the cache live, so re-tuned forts from a game update appear with no code
# change. Needs curl + python3.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
bash "$here/../../_srcdata/pull.sh"
python3 "$here/build.py" "$here/../../_srcdata/cache" "$here/storm-forts.json"
