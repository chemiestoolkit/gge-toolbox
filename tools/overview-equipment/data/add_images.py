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
# asset prefix). Hero art lives under either Equipment/Uniques/ (newer sets like
# Dragon) OR Equipment/Heroes/ (older sets like Victorious) — index all so every
# Hero-slot item gets its art.
idx = {}
for p in re.findall(r"itemassets/Equipment/Uniques/Item_Unique_\d+/Item_Unique_\d+--\d+", dll):
    eid = re.search(r"Item_Unique_(\d+)--", p).group(1)
    idx.setdefault(eid, p)
for p in re.findall(r"itemassets/Equipment/(?:Uniques|Heroes)/Hero_Unique_\d+/Hero_Unique_\d+--\d+", dll):
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

# Newer assets are texture atlases (empty BMP_0 frame + named real-icon frame).
# Fetch each image's .json sidecar and bake the icon's frame rect + sheet size
# so the UI can render a cropped sprite instead of the whole sheet.
import urllib.request, concurrent.futures

def fetch_atlas(url_webp):
    try:
        with urllib.request.urlopen(url_webp[:-5] + ".json", timeout=15) as r:
            a = json.loads(r.read().decode("utf-8"))
        anims = a.get("animations", {})
        named = [k for k in anims if k != "BMP_0"]
        if not named:
            return None
        f = a["frames"][anims[named[0]]["frames"][0]]
        size = a.get("size", {})
        return ([f[0], f[1], f[2], f[3]], [size.get("w", 0), size.get("h", 0)])
    except Exception:
        return None

urls = sorted({it["img"] for it in data["items"] if it.get("img")})
print(f"  fetching {len(urls)} sprite atlases…")
frames = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
    for url, res in zip(urls, ex.map(fetch_atlas, urls)):
        if res:
            frames[url] = res
framed = 0
for it in data["items"]:
    res = frames.get(it.get("img"))
    if res:
        it["frame"], it["sheet"] = res
        framed += 1

json.dump(data, open(data_path, "w"), separators=(",", ":"))
print(f"  images: {hit}/{len(data['items'])} equipment, {framed} atlas-cropped")
