#!/usr/bin/env bash
# Rebuild gacha data for the CURRENT game version, direct from Goodgame Studios.
# Goodgame only serves the live item DB, so historical gacha-<version>.json
# snapshots already committed here are kept as-is; this adds/refreshes the
# current one and rebuilds the versions.json manifest from whatever is present.
# Needs: curl, jq, python3.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
bash "$here/../../_srcdata/pull.sh"
cache="$here/../../_srcdata/cache"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

ver="$(grep -E '^empire_items_version=' "$cache/SOURCES.txt" | cut -d= -f2)"
[[ -n "$ver" ]] || { echo "could not read item version from SOURCES.txt" >&2; exit 1; }
echo "→ version $ver"

jq -c 'with_entries(.key|=ascii_downcase)' "$cache/en.json" > "$tmp/en_lower.json"
jq --slurpfile lang "$tmp/en_lower.json" -f "$here/extract_gacha.jq" "$cache/items_latest.json" \
   > "$here/gacha-$ver.json"
python3 "$here/add_phases.py" "$cache/items_latest.json" "$cache/en.json" "$here/gacha-$ver.json"

# Manifest from every gacha-*.json on disk (version-sorted; last = latest).
versions="$(ls "$here"/gacha-*.json 2>/dev/null \
  | sed -E 's#.*/gacha-(.*)\.json#\1#' | sort -V | jq -R . | jq -cs .)"
latest="$(jq -r '.[-1]' <<<"$versions")"
jq -n --argjson list "$versions" --arg latest "$latest" \
  '{latest:$latest, versions:($list|reverse)}' > "$here/versions.json"

echo "Done. Versions: $(jq -r '.versions|join(", ")' "$here/versions.json")  (latest $latest)"
