#!/usr/bin/env bash
# Regenerate every tool's data, pulled direct from Goodgame Studios' own servers
# (tools/_srcdata/pull.sh). Run after a game maintenance to pull new equipment,
# gacha pools, rift data, etc.
# Needs: bash, curl, jq, python3.
#
# Usage: bash tools/refresh-all.sh
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"

builds=(
  "overview-equipment/data/build.sh"
  "overview-decorations/data/build.sh"
  "overview-rift/data/build.sh"
  "overview-troops-tools/data/build.sh"
  "overview-generals/data/build.sh"
  "overview-loot-box/data/build.sh"
  "overview-event-rewards/data/build.sh"
  "overview-construction-items/data/build.sh"
  "overview-buildings/data/build.sh"
  "upgrade-cost/data/build.sh"
  "set-bonus/data/build.sh"
  "hol-planner/data/build.sh"
  "rift-optimizer/data/build.sh"
  "gacha-sim/data/build.sh"
)

fail=0
for b in "${builds[@]}"; do
  path="$here/$b"
  if [[ ! -f "$path" ]]; then
    echo "‼  missing: $b" >&2; fail=1; continue
  fi
  echo "▶  $b"
  if bash "$path"; then
    echo "✓  $b"
  else
    echo "✗  $b (build failed)" >&2; fail=1
  fi
done

if [[ "$fail" -ne 0 ]]; then
  echo "Some builds failed — see log above." >&2
  exit 1
fi
echo "All data refreshed."
