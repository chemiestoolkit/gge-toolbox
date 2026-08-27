#!/usr/bin/env python3
"""Rebuild aqua-islands.json from the game data cache.

The Storm Islands (kingdom "Eiland") content lives in three game-data tables:
  * `isles`               — the occupiable VILLAGE isles (wood / stone / aquamarine)
  * `islandrewardranks`   — the ALLIANCE cargo-point reward ladder
  * `islandPlayerRewards` — the PERSONAL cargo-point reward ladder
Both ladders ship two reward sets: set 0 (the legacy ladder) and set 2 (the
reworked one added in the recent update, split into per-member / alliance-funds
/ personal rewards). This reads the cache directly, so a re-tuned ladder or new
reward decos appear on the page with no code change.

Usage: build.py <cache-dir> <out.json>
"""
import json
import re
import sys
from datetime import datetime, timezone

cache, out_path = sys.argv[1], sys.argv[2]
items = json.load(open(f"{cache}/items_latest.json", encoding="utf-8"))
lang = {k.lower(): v for k, v in json.load(open(f"{cache}/en.json", encoding="utf-8")).items()}
dll = open(f"{cache}/ggs.dll.latest.js", encoding="utf-8", errors="ignore").read()

ASSET_ROOT = "https://empire-html5.goodgamestudios.com/default/assets/"
rewards = {str(r["rewardID"]): r for r in items.get("rewards", [])}
buildings = {str(b.get("wodID")): b for b in items.get("buildings", [])}


def i(row, key, default=0):
    try:
        return int(row.get(key, default))
    except (TypeError, ValueError):
        return default


def asset(token):
    tl = token.lower()
    for p in re.findall(r"itemassets/[A-Za-z0-9_/]+--\d+", dll):
        base = re.sub(r"--\d+$", "", p.split("/")[-1]).lower()
        if tl in base:
            return ASSET_ROOT + p + ".webp"
    return None


def deco_asset(type_token):
    tl = type_token.lower()
    for p in re.findall(r"itemassets/Building/[A-Za-z0-9_/]+--\d+", dll):
        base = re.sub(r"--\d+$", "", p.split("/")[-1])
        m = re.match(r"Deco_Building_(.+)", base)
        if m and tl in m.group(1).lower():
            return ASSET_ROOT + p + ".webp"
    return None


ICONS = {
    "aquamarine": asset("AquamarineRelic_Building_Level3"),
    "cargo": asset("Collectable_Currency_CargoPoints"),
    "coins": None,
    "rubies": None,
    "Upgrade tokens": asset("Collectable_Currency_LegendaryMaterial"),
    "Construction tokens": asset("Collectable_Currency_LegendaryToken"),
    "Sceat tokens": asset("Collectable_Currency_SceatToken"),
    "Silver tokens": asset("Collectable_Currency_SilverToken"),
}

# add<Currency> reward keys → (display label, icon key)
ADD_KEYS = {
    "addLegendaryMaterial": ("Upgrade tokens", "Upgrade tokens"),
    "addLegendaryToken": ("Construction tokens", "Construction tokens"),
    "addSceatToken": ("Sceat tokens", "Sceat tokens"),
    "addSilverToken": ("Silver tokens", "Silver tokens"),
}
_COLOR_WORDS = ("gold", "blue", "green", "red", "fore", "rider", "mask", "island")


def humanize(token):
    """Best-effort readable name for an unreleased deco type (no lang string yet)."""
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", token)          # camelCase → spaces
    for w in _COLOR_WORDS:                                      # split glued lowercase words
        s = re.sub(f"(?i)(?<=[a-z])({w})$", r" \1", s)
    return " ".join(p.capitalize() for p in s.split())


def decode_reward(rid):
    r = rewards.get(str(rid))
    if not r:
        return []
    out = []
    if r.get("currency1"):
        out.append({"label": "Coins", "amount": int(r["currency1"]), "icon": "coins"})
    if r.get("currency2"):
        out.append({"label": "Rubies", "amount": int(r["currency2"]), "icon": "rubies"})
    for key, (label, ic) in ADD_KEYS.items():
        if r.get(key):
            out.append({"label": label, "amount": int(r[key]), "icon": ic,
                        "img": ICONS.get(ic)})
    if r.get("decoWodID"):
        b = buildings.get(str(r["decoWodID"]), {})
        name = humanize(b.get("comment2") or b.get("type") or "Deco")
        out.append({"label": name + " deco", "amount": None, "kind": "deco",
                    "img": deco_asset(b.get("type", "")),
                    "note": (f"{i(b, 'decoPoints')} deco pts" if i(b, "decoPoints") else None),
                    "might": i(b, "mightValue")})
    return out


VILLAGE_KIND = {"VILLAGEWOOD": "Wood", "VILLAGESTONE": "Stone", "VILLAGEAQUAMARINE": "Aquamarine"}
villages = []
for r in items.get("isles", []):
    kind = VILLAGE_KIND.get(r.get("type"))
    if not kind:
        continue
    villages.append({
        "id": i(r, "IsleID"),
        "kind": kind,
        "wood": i(r, "fixedLootWood"),
        "stone": i(r, "fixedLootStone"),
        "aquamarine": i(r, "fixedLootAquamarine"),
        "cargo": i(r, "lootCargoPoints"),
        "cargoVar": i(r, "maxDiffLootCargoPoints"),
        "occupation": i(r, "occupationTime"),   # seconds
        "cooldown": i(r, "globalCooldown"),
        "guards": i(r, "guards"),
    })
# Aquamarine villages first, then biggest haul.
_ORDER = {"Aquamarine": 0, "Wood": 1, "Stone": 2}
villages.sort(key=lambda v: (_ORDER[v["kind"]], -(v["aquamarine"] or v["wood"] or v["stone"])))


def ladder(table, id_key):
    """Group a reward table into {set: [{req, topX, rewards:[...]}]}."""
    sets = {}
    for row in items.get(table, []):
        s = str(row.get("islandRewardSetID", "0"))
        rung = {
            "req": int(row["cargoPointRequirement"]) if row.get("cargoPointRequirement") else None,
            "topX": int(row["topXValue"]) if row.get("topXValue") else None,
            "rewards": [rw for rid in str(row["rewardIDs"]).split(",") for rw in decode_reward(rid)],
        }
        sets.setdefault(s, []).append(rung)
    for rungs in sets.values():
        rungs.sort(key=lambda x: (x["req"] is None, x["req"] or 0))
    return sets


alliance = ladder("islandrewardranks", "islandRewardRankID")
personal = ladder("islandPlayerRewards", "islandPlayerRewardID")

# set 2 = the reworked ladder (current), set 0 = legacy.
out = {
    "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "version": (items.get("versionInfo", {}).get("version", {}) or {}).get("@value", ""),
    "icons": ICONS,
    "villages": villages,
    "ladders": {
        "current": {"alliance": alliance.get("2", []), "personal": personal.get("2", [])},
        "legacy": {"alliance": alliance.get("0", []), "personal": personal.get("0", [])},
    },
}
json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"Wrote {out_path} — {len(villages)} villages, "
      f"{len(out['ladders']['current']['alliance'])} alliance + "
      f"{len(out['ladders']['current']['personal'])} personal rungs (current).")
