#!/usr/bin/env python3
"""Attach Goodgame CDN image URLs to decorations.json using the game DLL asset map.
Usage: add_images.py <dll.js> <decorations.json>"""
import re, json, sys

ASSET_ROOT = "https://empire-html5.goodgamestudios.com/default/assets/"
dll_path, data_path = sys.argv[1], sys.argv[2]
dll = open(dll_path, encoding="utf-8", errors="ignore").read()

# Index every Deco_Building render path by lowercased asset base name.
idx = {}
for p in re.findall(r"itemassets/Building/Deco/[A-Za-z0-9_]+/Deco_Building_[A-Za-z0-9_]+--\d+", dll):
    base = re.search(r"Deco_Building_([A-Za-z0-9_]+)--", p).group(1).lower()
    idx.setdefault(base, p)


def resolve(t):
    if not t:
        return None
    tl = t.lower()
    if tl in idx:
        return idx[tl]
    for k, v in idx.items():            # fuzzy: substring either way
        if tl in k or k in tl:
            return v
    return None


data = json.load(open(data_path))
hit = 0
for it in data["items"]:
    path = resolve(it.get("type"))
    if path:
        it["img"] = ASSET_ROOT + path + ".webp"
        hit += 1
    it.pop("type", None)                # not needed client-side
json.dump(data, open(data_path, "w"), separators=(",", ":"))
print(f"  images: {hit}/{len(data['items'])} decorations")
