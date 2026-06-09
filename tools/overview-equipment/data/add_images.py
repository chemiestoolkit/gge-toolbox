#!/usr/bin/env python3
"""Attach Goodgame CDN image URLs to equipment.json using the DLL asset map.
Equipment renders are keyed by equipmentID: itemassets/Equipment/Uniques/Item_Unique_<id>/...
Usage: add_images.py <dll.js> <equipment.json>"""
import re, json, sys

ASSET_ROOT = "https://empire-html5.goodgamestudios.com/default/assets/"
dll_path, data_path = sys.argv[1], sys.argv[2]
dll = open(dll_path, encoding="utf-8", errors="ignore").read()

# Map equipmentID -> render path. Standard pieces use Item_Unique_<id>; the
# Hero-slot commander pieces use Hero_Unique_<id> (same equipmentID, different
# asset prefix) — index both so Hero-slot items get their art too.
idx = {}
for p in re.findall(r"itemassets/Equipment/Uniques/Item_Unique_\d+/Item_Unique_\d+--\d+", dll):
    eid = re.search(r"Item_Unique_(\d+)--", p).group(1)
    idx.setdefault(eid, p)
for p in re.findall(r"itemassets/Equipment/Uniques/Hero_Unique_\d+/Hero_Unique_\d+--\d+", dll):
    eid = re.search(r"Hero_Unique_(\d+)--", p).group(1)
    idx.setdefault(eid, p)

data = json.load(open(data_path))
hit = 0
for it in data["items"]:
    p = idx.get(str(it["id"])) or (it.get("reuseId") and idx.get(str(it["reuseId"])))
    if p:
        it["img"] = ASSET_ROOT + p + ".webp"
        hit += 1
    it.pop("reuseId", None)
json.dump(data, open(data_path, "w"), separators=(",", ":"))
print(f"  images: {hit}/{len(data['items'])} equipment")
