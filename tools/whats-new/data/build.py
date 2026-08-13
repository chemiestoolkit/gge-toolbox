#!/usr/bin/env python3
"""Build the "What's New in GGE" feed by diffing game-data versions.

Compares the current items file against a small committed snapshot of the last
version's item IDs (prev-index.json). Anything present now but not then is NEW —
grouped by kind (gear, decorations, troops, construction items, gacha, sets) and
linked out to the matching overview / the gacha sim so players can see exactly
what each thing is.

Display names come from the lang file; thumbnails are borrowed by name from the
already-built overview JSONs (so this must run AFTER the overviews in
refresh-all.sh). The result accumulates a short history in whats-new.json.

Usage: build.py <repo-root>          (defaults to ../../.. from here)
"""
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CACHE = os.path.join(ROOT, "tools", "_srcdata", "cache")

items = json.load(open(os.path.join(CACHE, "items_latest.json"), encoding="utf-8"))
lang = {k.lower(): v for k, v in json.load(open(os.path.join(CACHE, "en.json"), encoding="utf-8")).items()
        if isinstance(v, str)}
version = "?"
try:
    for ln in open(os.path.join(CACHE, "SOURCES.txt"), encoding="utf-8"):
        if ln.startswith("empire_items_version="):
            version = ln.split("=", 1)[1].strip()
except OSError:
    pass


def L(key, default=""):
    return lang.get(str(key).lower(), default)


# name -> img, harvested from an already-built overview JSON (list under `items`).
def img_index(rel):
    try:
        d = json.load(open(os.path.join(ROOT, "tools", rel), encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    rows = d.get("items") or d.get("boxes") or d.get("sets") or (d if isinstance(d, list) else [])
    return {str(r.get("name", "")).lower(): r.get("img") for r in rows if r.get("img")}


IMG = {
    "equipment": img_index("overview-equipment/data/equipment.json"),
    "deco": img_index("overview-decorations/data/decorations.json"),
    "building": img_index("overview-buildings/data/buildings.json"),
    "ci": img_index("overview-construction-items/data/construction-items.json"),
    "troops": img_index("overview-troops-tools/data/troops-tools.json"),
}


def img_for(bucket, name):
    return IMG.get(bucket, {}).get(str(name).lower())


# Fallback: resolve an equipment render straight from the client asset map when
# the item isn't carried in the overview (some sale/appearance pieces aren't).
ASSET_ROOT = "https://empire-html5.goodgamestudios.com/default/assets/"
import re as _re
try:
    _dll = open(os.path.join(CACHE, "ggs.dll.latest.js"), encoding="utf-8", errors="ignore").read()
except OSError:
    _dll = ""
_EQ_ASSET = {}
for _p in _re.findall(r"itemassets/Equipment/Uniques/Item_Unique_(\d+)/Item_Unique_\d+--\d+", _dll):
    pass
for _m in _re.finditer(r"itemassets/Equipment/Uniques/Item_Unique_(\d+)/Item_Unique_\d+--\d+", _dll):
    _EQ_ASSET.setdefault(_m.group(1), _m.group(0))


def eq_img(eid):
    p = _EQ_ASSET.get(str(eid))
    return (ASSET_ROOT + p + ".webp") if p else None


# ── category resolvers: (table, idkey, bucket, overview-url, name_fn) ─────────
def eq_name(r):
    return L(f"equipment_unique_{r.get('equipmentID')}") or r.get("comment2") or r.get("comment1")


def deco_name(r):
    t = r.get("type", "")
    return L(f"deco_{t}_name") or L(f"building_{t}_name") or r.get("comment1") or t


def bld_name(r):
    t = r.get("type", "")
    return L(f"building_{t}_name") or L(f"deco_{t}_name") or r.get("comment1") or t


def ci_name(r):
    n = r.get("name", "")
    return L(f"ci_appearance_{n}") or L(f"ci_{n}_name") or r.get("comment1") or n


def unit_name(r):
    return L(f"{r.get('type', '')}_name") or r.get("comment1") or r.get("type")


def is_deco(b):
    return str(b.get("buildingGroundType", "")).upper() == "DECO"


CATS = []


def new_ids(table, idkey, prev):
    have = set(prev.get(table, []))
    cur = [str(r.get(idkey)) for r in items.get(table, [])]
    return have, cur, [r for r in items.get(table, []) if str(r.get(idkey)) not in have]


def build_groups(prev):
    groups = []

    def group(title, icon, link, rows, bucket, name_fn, note_fn=None, img_fn=None):
        seen, out = set(), []
        for r in rows:
            nm = str(name_fn(r) or "").strip()
            if not nm or nm.lower() in seen:
                continue
            seen.add(nm.lower())
            img = img_for(bucket, nm) or (img_fn(r) if img_fn else None)
            out.append({"name": nm, "img": img,
                        "link": link + ("?q=" + _q(nm) if "overview" in link else ""),
                        "note": note_fn(r) if note_fn else None})
        if out:
            groups.append({"category": title, "icon": icon, "link": link, "items": out})

    # Equipment (overview art, else the client asset by id)
    _, _, eq = new_ids("equipments", "equipmentID", prev)
    group("Equipment & Gear", "🛡️", "../overview-equipment/", eq, "equipment", eq_name,
          img_fn=lambda r: eq_img(r.get("equipmentID")))

    # Buildings split into decorations vs functional
    _, _, bl = new_ids("buildings", "wodID", prev)
    group("Decorations", "🎴", "../overview-decorations/", [b for b in bl if is_deco(b)], "deco", deco_name)
    group("Buildings", "🏛️", "../overview-buildings/", [b for b in bl if not is_deco(b)], "building", bld_name)

    # Construction items
    _, _, ci = new_ids("constructionItems", "constructionItemID", prev)
    group("Construction Items", "🧩", "../overview-construction-items/", ci, "ci", ci_name)

    # Troops & tools
    _, _, un = new_ids("units", "wodID", prev)
    group("Troops & Tools", "⚔️", "../overview-troops-tools/", un, "troops", unit_name)

    # Gacha events → the spin sim (group by base name)
    _, _, ga = new_ids("gachaEvents", "gachaID", prev)
    ga_names = {}
    for g in ga:
        nm = (g.get("comment1") or "Gacha").split(" - ")[0].strip()
        ga_names.setdefault(nm, 0)
        ga_names[nm] += 1
    if ga_names:
        groups.append({"category": "Gacha Events", "icon": "🎰", "link": "../gacha-sim/",
                       "items": [{"name": nm, "img": None, "link": "../gacha-sim/",
                                  "note": f"{n} pull pools"} for nm, n in sorted(ga_names.items())]})

    # World-map skins (no overview to link to)
    _, _, sk = new_ids("worldmapskins", "worldmapskinID", prev)
    sk_names = [s.get("comment1") or s.get("name") for s in sk if (s.get("comment1") or s.get("name"))]
    if sk_names:
        groups.append({"category": "Map Skins", "icon": "🗺️", "link": None,
                       "items": [{"name": str(n), "img": None, "link": None, "note": None}
                                 for n in dict.fromkeys(sk_names)]})
    return groups


def _q(s):
    from urllib.parse import quote
    return quote(s)


def headline(groups):
    blob = json.dumps(groups).lower()
    total = sum(len(g["items"]) for g in groups)
    if "anniversary" in blob or "festive" in blob or "firework" in blob:
        return "🎉 Anniversary update", total
    return "✨ Game update", total


def main():
    prev_path = os.path.join(HERE, "prev-index.json")
    out_path = os.path.join(HERE, "whats-new.json")
    prev = {}
    try:
        prev = json.load(open(prev_path, encoding="utf-8")).get("ids", {})
    except (OSError, ValueError):
        prev = {}

    groups = build_groups(prev) if prev else []
    feed = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "version": version, "updates": []}
    try:
        feed["updates"] = json.load(open(out_path, encoding="utf-8")).get("updates", [])
    except (OSError, ValueError):
        pass

    if prev and groups:
        head, total = headline(groups)
        summary = ", ".join(f"{len(g['items'])} {g['category'].lower()}" for g in groups)
        entry = {"version": version, "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                 "headline": head, "count": total, "summary": summary, "groups": groups}
        feed["updates"] = [u for u in feed["updates"] if u.get("version") != version]
        feed["updates"].insert(0, entry)
        feed["updates"] = feed["updates"][:8]
        print(f"whats-new: v{version} — {total} new items across {len(groups)} groups")
    else:
        print(f"whats-new: {'baseline seeded' if not prev else 'no new items'} for v{version}")

    json.dump(feed, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    # Refresh the snapshot to the current version's IDs for next time.
    ID_TABLES = {"equipments": "equipmentID", "buildings": "wodID",
                 "constructionItems": "constructionItemID", "units": "wodID",
                 "gachaEvents": "gachaID", "worldmapskins": "worldmapskinID",
                 "gems": "gemID", "equipment_sets": "ID"}
    snap = {t: [str(r.get(k)) for r in items.get(t, [])] for t, k in ID_TABLES.items()}
    json.dump({"version": version, "ids": snap}, open(prev_path, "w"), separators=(",", ":"))


if __name__ == "__main__":
    main()
