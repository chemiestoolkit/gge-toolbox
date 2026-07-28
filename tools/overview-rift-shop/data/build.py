#!/usr/bin/env python3
"""Rebuild rift-shop.json from the game data cache.

The Rift Raid event shops ("ARE Blacksmith" + the "ARME Ducat Shop") are plain
`packages` rows priced in one of the rift currencies. Because this reads the
cache directly, the daily refresh picks up new stock automatically — when GGS
adds shop entries in an update, the page updates itself with no code change.

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

# ── indexes ────────────────────────────────────────────────────────────────
units = {str(u.get("wodID")): u for u in items["units"]}
equips = {str(e.get("equipmentID")): e for e in items["equipments"]}
boxes = {str(b.get("lootBoxID")): b for b in items["lootBoxes"]}

# Asset paths: units/tools live under itemassets/Units/..., collectables under
# itemassets/Collectables/... — index by the token after the last slash.
unit_assets = {}
for p in re.findall(r"itemassets/Units/[A-Za-z0-9_/]+--\d+", dll):
    base = re.sub(r"--\d+$", "", p.split("/")[-1])
    m = re.match(r"(?:Eventtool|Tool|Unit)_Unit_(.+)", base) or re.match(r"(.+)", base)
    if m:
        unit_assets.setdefault(m.group(1).lower(), p)
cur_assets = {}
for p in re.findall(r"itemassets/Collectables/[A-Za-z0-9_/]+--\d+", dll):
    base = re.sub(r"--\d+$", "", p.split("/")[-1])
    m = re.match(r"Collectable_Currency_(.+)", base)
    if m and "DropShadow" not in base:
        cur_assets.setdefault(m.group(1).lower(), p)
box_assets = {}
for p in re.findall(r"itemassets/Collectables/MysteryBoxes/[A-Za-z0-9_/]+--\d+", dll):
    base = re.sub(r"--\d+$", "", p.split("/")[-1])
    m = re.match(r"Collectable_(.+)", base)
    if m:
        box_assets.setdefault(m.group(1).lower(), p)
eq_assets = {}
for p in re.findall(r"itemassets/Equipment/Uniques/Item_Unique_\d+/Item_Unique_\d+--\d+", dll):
    eq_assets.setdefault(re.search(r"Item_Unique_(\d+)--", p).group(1), p)


def L(key, fallback=None):
    return lang.get(key.lower(), fallback)


def set_prefix(comment1):
    """Common name prefix of a set, taken from whichever members are named.

    Items ship before their lang strings, so an unreleased piece can still be
    labelled from its siblings (e.g. "Bronze Dragon Hunter Armor" + "… Helmet"
    -> "Bronze Dragon Hunter"). Returns None when nothing useful is shared.
    """
    if not comment1:
        return None
    names = [n for n in (L(f"equipment_unique_{e['equipmentID']}") for e in items["equipments"]
                         if e.get("comment1") == comment1) if n]
    if len(names) < 2:
        return None
    words = names[0].split()
    for other in names[1:]:
        ow = other.split()
        while words and (len(ow) < len(words) or ow[:len(words)] != words):
            words.pop()
        if not words:
            return None
    return " ".join(words) or None


def unit_name(wid):
    u = units.get(str(wid))
    if not u:
        return f"Unit #{wid}"
    t = u.get("type", "")
    return L(f"{t}_name", t or f"Unit #{wid}")


def unit_img(wid):
    u = units.get(str(wid))
    if not u:
        return None
    t = str(u.get("type", "")).lower()
    for key, path in unit_assets.items():
        if key == t or (len(t) >= 5 and t in key):
            return ASSET_ROOT + path + ".webp"
    return None


# Currency payload keys (add<Name>) → display name + icon.
def currency_meta(key):
    name = key[3:]  # strip "add"
    disp = L(f"currency_name_{name}") or L(f"currency_name_{name[0].lower() + name[1:]}") \
        or re.sub(r"(?<!^)(?=[A-Z])", " ", name)
    img = None
    for k, path in cur_assets.items():
        if k == name.lower():
            img = ASSET_ROOT + path + ".webp"
            break
    return disp, img


CURRENCIES = {
    "costRiftCoin": ("Rift Coin", "RiftCoin"),
    "costLegendaryRiftCoin": ("Legendary Rift Coin", "LegendaryRiftCoin"),
    "costRiftShard": ("Rift Shard", "RiftShard"),
    "costImperialDucat": ("Imperial Ducat", "ImperialDucat"),
}
# Friendlier shop names than the dev comments.
SHOP_LABELS = {
    "ARE Blacksmith - Rift Coin Package": "Rift Coin shop",
    "ARE Blacksmith - RiftShard Package": "Rift Shard shop",
    "ARE Blacksmith - Legendary Rift Coin Package": "Legendary Rift Coin shop",
    "ARE Blacksmith Booster Tools": "Booster tools",
    "ARME Ducat Shop": "Ducat shop (Tournament)",
}

entries = []
for p in items["packages"]:
    cur_key = next((c for c in CURRENCIES if c in p), None)
    if not cur_key:
        continue
    cur_name, cur_internal = CURRENCIES[cur_key]
    cur_img = None
    for k, path in cur_assets.items():
        if k == cur_internal.lower():
            cur_img = ASSET_ROOT + path + ".webp"
            break

    # ── what you actually get ────────────────────────────────────────────
    gets = []
    if p.get("unitID"):
        gets.append({
            "name": unit_name(p["unitID"]),
            "qty": int(p.get("unitAmount") or 1),
            "kind": "unit",
            "img": unit_img(p["unitID"]),
        })
    if p.get("equipmentIDs"):
        for eid in str(p["equipmentIDs"]).split(","):
            eid = eid.strip()
            e = equips.get(eid, {})
            name = L(f"equipment_unique_{eid}")
            pending = False
            if not name:
                # Unreleased piece — GGS ships the item before its lang string.
                # Borrow the set's name from a sibling that IS named, so the row
                # still reads sensibly; it self-heals on the next data refresh.
                name = f"{e.get('comment2') or 'Equipment'} (name pending)"
                pending = True
                prefix = set_prefix(e.get("comment1"))
                if prefix:
                    name = f"{prefix} {e.get('comment2') or 'piece'} (name pending)"
            gets.append({
                "name": name,
                "qty": int(p.get("equipmentAmount") or 1),
                "kind": "equipment",
                "pending": pending or None,
                "img": (ASSET_ROOT + eq_assets[eid] + ".webp") if eid in eq_assets else None,
            })
    if p.get("lootBox"):
        bid, _, cnt = str(p["lootBox"]).partition("+")
        b = boxes.get(bid, {})
        internal = str(b.get("name", ""))
        img = None
        for k, path in box_assets.items():
            if k == internal.lower():
                img = ASSET_ROOT + path + ".webp"
                break
        # Box display names live under mysterybox_boxname_<internal>[_<tier>].
        box_name = (L(f"mysterybox_boxname_{internal}_1")
                    or L(f"mysterybox_boxname_{internal}")
                    or L(f"lootbox_{internal}_name")
                    or L(f"{internal}_name")
                    or internal or f"Box #{bid}")
        gets.append({
            "name": box_name,
            "qty": int(cnt or 1),
            "kind": "lootbox",
            "img": img,
            "boxId": int(bid) if bid.isdigit() else None,
        })
    for k, v in p.items():
        if k.startswith("add") and k not in ("addRiftCoin",) or k == "addRiftCoin":
            disp, img = currency_meta(k)
            gets.append({"name": disp, "qty": int(v), "kind": "currency", "img": img})
    if p.get("hiddenMead"):
        gets.append({"name": "Mead (included)", "qty": int(p["hiddenMead"]), "kind": "currency",
                     "img": None, "note": True})

    if not gets:
        continue

    raw_shop = str(p.get("comment1", "")).strip()
    entries.append({
        "id": int(p["packageID"]),
        "shop": SHOP_LABELS.get(raw_shop, raw_shop or "Rift shop"),
        "currency": cur_name,
        "currencyImg": cur_img,
        "cost": int(p[cur_key]),
        "stock": int(p["stock"]) if str(p.get("stock", "")).isdigit() else None,
        "minLevel": int(p["minLevel"]) if str(p.get("minLevel", "")).isdigit() else None,
        "type": p.get("packageType", ""),
        "gets": gets,
    })

entries.sort(key=lambda e: (e["shop"], e["cost"]))
json.dump({
    "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "itemsVersion": items.get("versionInfo", {}).get("version") if isinstance(items.get("versionInfo"), dict) else None,
    "entries": entries,
}, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

shops = {}
for e in entries:
    shops[e["shop"]] = shops.get(e["shop"], 0) + 1
print(f"Wrote {out_path} — {len(entries)} entries: " + ", ".join(f"{k} {v}" for k, v in sorted(shops.items())))
