#!/usr/bin/env python3
"""Rebuild storm-forts.json from the game data cache.

The Storm Islands (kingdom "Eiland") gained a real content table in the game
data — `isles`. The DUNGEON-type isles are the NPC "storm forts" you attack for
aquamarine + cargo points: each carries a castle level, guard count, wall/gate/
moat/tower defence and a fixed loot table with a variance band. Because this
reads the cache directly, a game update that re-tunes the forts shows up on the
page with no code change.

Usage: build.py <cache-dir> <out.json>
"""
import json
import re
import sys
from datetime import datetime, timezone

cache, out_path = sys.argv[1], sys.argv[2]
items = json.load(open(f"{cache}/items_latest.json", encoding="utf-8"))
dll = open(f"{cache}/ggs.dll.latest.js", encoding="utf-8", errors="ignore").read()

ASSET_ROOT = "https://empire-html5.goodgamestudios.com/default/assets/"


def asset(token):
    """First CDN render path whose file token contains `token` (case-insensitive)."""
    tl = token.lower()
    for p in re.findall(r"itemassets/[A-Za-z0-9_/]+--\d+", dll):
        base = re.sub(r"--\d+$", "", p.split("/")[-1]).lower()
        if tl in base:
            return ASSET_ROOT + p + ".webp"
    return None


ICONS = {
    "aquamarine": asset("AquamarineRelic_Building_Level3"),
    "cargo": asset("Collectable_Currency_CargoPoints"),
}


def i(row, key, default=0):
    v = row.get(key, default)
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def victory_range(spec):
    """countVictories is a #-joined list of victory counts the fort spawns at."""
    nums = [int(x) for x in str(spec).split("#") if str(x).strip().isdigit()]
    return (min(nums), max(nums)) if nums else (None, None)


forts = []
for r in items.get("isles", []):
    if r.get("type") != "DUNGEON":
        continue
    vfrom, vto = victory_range(r.get("countVictories"))
    forts.append({
        "id": i(r, "IsleID"),
        "victoryFrom": vfrom,
        "victoryTo": vto,
        "level": i(r, "dungeonlevel"),
        "guards": i(r, "guards"),
        "wall": {"level": i(r, "wallLevel"), "bonus": i(r, "wallBonus")},
        "gate": {"level": i(r, "gateLevel"), "bonus": i(r, "gateBonus")},
        "moat": {"level": i(r, "moatLevel"), "bonus": i(r, "moatBonus")},
        "tower": {"level": i(r, "towerLevel")},
        "loot": {
            "wood": i(r, "lootWood"),
            "stone": i(r, "lootStone"),
            "food": i(r, "lootFood"),
            "resVariancePct": i(r, "maxDiffLootResources"),
            "aquamarine": i(r, "lootAquamarine"),
            "aquamarineVar": i(r, "maxDiffLootAquamarine"),
            "cargo": i(r, "lootCargoPoints"),
            "cargoVar": i(r, "maxDiffLootCargoPoints"),
        },
        "cooldown": {
            "global": i(r, "globalCooldown"),   # seconds
            "local": i(r, "localCooldown"),
        },
        "maxVictories": i(r, "maxCountVictories"),
    })

# Progression order: by the first victory count the fort appears at.
forts.sort(key=lambda f: (f["victoryFrom"] if f["victoryFrom"] is not None else 999))

out = {
    "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "version": (items.get("versionInfo", {}).get("version", {}) or {}).get("@value", ""),
    "icons": ICONS,
    "forts": forts,
}
json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"Wrote {out_path} — {len(forts)} storm forts.")
