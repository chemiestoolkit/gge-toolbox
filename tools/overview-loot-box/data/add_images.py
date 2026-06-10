#!/usr/bin/env python3
"""Attach box art to loot-boxes.json from the DLL asset map.
Boxes live under Collectables/ (Collectable_Currency_<name> or
MysteryBoxes/Collectable_<name>). Usage: add_images.py <dll.js> <loot-boxes.json>"""
import re, json, sys

ASSET_ROOT = "https://empire-html5.goodgamestudios.com/default/assets/"
dll_path, data_path = sys.argv[1], sys.argv[2]
dll = open(dll_path, encoding="utf-8", errors="ignore").read()

paths = set(re.findall(r"itemassets/Collectables/[A-Za-z0-9_/]+--\d+", dll))

def find(internal):
    pat = re.compile(r"Collectable_(Currency_)?" + re.escape(internal) + r"--", re.I)
    for p in paths:
        if pat.search(p):
            return p
    return None

data = json.load(open(data_path))
hit = 0
for b in data["boxes"]:
    p = find(b["internal"])
    if p:
        b["img"] = ASSET_ROOT + p + ".webp"
        hit += 1
json.dump(data, open(data_path, "w"), separators=(",", ":"))
print(f"  images: {hit}/{len(data['boxes'])} boxes")
