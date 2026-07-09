#!/usr/bin/env bash
# Rebuild construction-items.json from game data pulled direct from Goodgame Studios. Needs curl + jq + python3.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
bash "$here/../../_srcdata/pull.sh"
cache="$here/../../_srcdata/cache"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
jq -c 'with_entries(.key|=ascii_downcase)' "$cache/en.json" > "$tmp/en.json"
jq --slurpfile lang "$tmp/en.json" -f "$here/extract.jq" "$cache/items_latest.json" > "$here/construction-items.json"
# post-pass: resolve each item's icon from the game's DLL asset index (ConstructionItem_<raw>)
python3 - "$here/construction-items.json" "$cache" <<'PYEOF'
import json, re, sys, glob
out, cache = sys.argv[1], sys.argv[2]
dll = open(glob.glob(cache + "/ggs.dll*")[0], encoding="utf-8", errors="replace").read()
ROOT = "https://empire-html5.goodgamestudios.com/default/assets/"
assets = {}
for p in re.findall(r"itemassets/[A-Za-z0-9_/]+--\d+", dll):
    assets[p.rsplit("/", 1)[-1].split("--")[0].lower()] = ROOT + p + ".webp"
d = json.load(open(out))
hit = 0
for it in d["items"]:
    raw = it.pop("raw", "").lower()
    img = assets.get("constructionitem_" + raw) or assets.get("constructionitem_premium" + raw)
    if img:
        it["img"] = img
        hit += 1
json.dump(d, open(out, "w"), ensure_ascii=False)
print(f"icons resolved: {hit}/{len(d['items'])}")
PYEOF
echo "Wrote construction-items.json — $(jq '.items|length' "$here/construction-items.json") construction items."
