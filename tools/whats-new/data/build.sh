#!/usr/bin/env bash
# Rebuild the What's New feed by diffing the current game data against the last
# recorded version. Must run AFTER the overviews (it borrows their thumbnails),
# so it's placed last in refresh-all.sh. Needs python3.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
python3 "$here/build.py" "$here/../../.."
