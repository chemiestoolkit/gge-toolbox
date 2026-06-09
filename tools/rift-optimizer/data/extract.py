#!/usr/bin/env python3
"""
Rift equipment extractor — Empire Toolbox.
Downloads the current game data and produces rift.json.
Run: python3 extract.py [ggs.dll.latest.js path]
     (DLL arg optional; downloaded if absent)
"""
import json, sys, re, urllib.request, os, tempfile

ITEMS_URL = "https://raw.githubusercontent.com/GeneralsCamp/ggempire-data-cache/main/public/data/empire/items_latest.json"
LANG_URL  = "https://raw.githubusercontent.com/GeneralsCamp/ggempire-data-cache/main/public/data/lang/en.json"
DLL_URL   = "https://raw.githubusercontent.com/GeneralsCamp/ggempire-data-cache/main/public/data/empire/dll/ggs.dll.latest.js"
# Asset matches in the DLL already start with "itemassets/", so the base must NOT
# repeat it — otherwise the URL gets a double "itemassets/itemassets/" and 404s.
CDN       = "https://empire-html5.goodgamestudios.com/default/assets/"
OUT       = os.path.join(os.path.dirname(__file__), "rift.json")

SLOT_NAMES = {"1": "Armor", "2": "Weapon", "3": "Helmet", "4": "Artifact", "6": "Hero"}
WEARER_NAMES = {"1": "Baron", "2": "General"}

def fetch(url, label):
    print(f"  Downloading {label}…", file=sys.stderr)
    with urllib.request.urlopen(url) as r:
        return r.read().decode("utf-8")

def resolve_effect(eid, val, effects_map, lang):
    name = effects_map.get(str(eid), "")
    if not name:
        return f"Effect {eid} ×{val}"
    tpl_key = f"equip_effect_description_{name.lower()}"
    tpl = lang.get(tpl_key, "")
    if tpl and "{0}" in tpl:
        return tpl.replace("{0}", str(val))
    return f"{name} {val}"

def parse_effects(effects_str, effects_map, lang):
    out = []
    for pair in str(effects_str or "").split(","):
        pair = pair.strip()
        if "&" not in pair:
            continue
        eid, val = pair.split("&", 1)
        out.append({"raw": pair, "label": resolve_effect(eid.strip(), val.strip(), effects_map, lang)})
    return out

def build_img_index(dll_text):
    """Return dict: lowercase asset key → full CDN URL."""
    idx = {}
    # Standard equipment items (slots 1-4): Item_Unique_<eid>
    for m in re.finditer(r'itemassets/Equipment/Uniques/Item_Unique_(\d+)/[^"\']+', dll_text):
        key = "item_unique_" + m.group(1)
        if key not in idx:
            idx[key] = CDN + m.group(0) + ".webp"
    # Hero items (slot 6): Hero_Unique_<eid> — these are the General/Commander pieces
    for m in re.finditer(r'itemassets/Equipment/Uniques/Hero_Unique_(\d+)/[^"\']+', dll_text):
        key = "item_unique_" + m.group(1)  # key by equipmentID so item_img() finds it
        if key not in idx:
            idx[key] = CDN + m.group(0) + ".webp"
    # Unique gems: Item_Gem_Unique_<gemID>
    for m in re.finditer(r'itemassets/Equipment/UniqueGems/Item_Gem_Unique_(\d+)/[^"\']+', dll_text):
        key = "gem_" + m.group(1)
        if key not in idx:
            idx[key] = CDN + m.group(0) + ".webp"
    return idx

def main():
    here = os.path.dirname(__file__)

    raw_items = fetch(ITEMS_URL, "items_latest.json")
    raw_lang  = fetch(LANG_URL,  "lang/en.json")

    print("  Parsing…", file=sys.stderr)
    d    = json.loads(raw_items)
    lang = {k.lower(): v for k, v in json.loads(raw_lang).items()}

    # Build effect ID→name lookup
    effects_map = {}
    for e in d.get("effects", []):
        effects_map[str(e.get("effectID", ""))] = e.get("name", "")

    # Identify rift sets: have at least one 9-piece bonus entry and
    # gems that have sellRiftShard or sellOfferingShard
    eq_sets   = d.get("equipment_sets", [])
    gems_data = d.get("gems", [])
    equips    = d.get("equipments", [])

    nine_piece_sids = {str(s["setID"]) for s in eq_sets if str(s.get("neededItems","")) == "9"}

    # True Rift sets sell for Rift Shards. Sets that sell for Offering Shards are
    # the Victorious (PvP) and Stalwart (castellan) sets — exclude those here.
    rift_gem_sids = set()
    for g in gems_data:
        sid = str(g.get("setID",""))
        if sid in nine_piece_sids and g.get("sellRiftShard"):
            rift_gem_sids.add(sid)

    print(f"  Found {len(rift_gem_sids)} rift set IDs.", file=sys.stderr)

    # Build bonus table per setID: list of {pieces, effects[]}
    bonus_map = {}
    for s in eq_sets:
        sid = str(s.get("setID",""))
        if sid not in rift_gem_sids:
            continue
        pieces = int(s.get("neededItems", 0))
        fx = parse_effects(s.get("effects",""), effects_map, lang)
        bonus_map.setdefault(sid, []).append({"pieces": pieces, "effects": fx})
    for sid in bonus_map:
        bonus_map[sid].sort(key=lambda x: x["pieces"])

    # Build equipment lookup by setID
    eq_by_set = {}
    for e in equips:
        sid = str(e.get("setID",""))
        if sid in rift_gem_sids:
            eq_by_set.setdefault(sid, []).append(e)

    gem_by_set = {}
    for g in gems_data:
        sid = str(g.get("setID",""))
        if sid in rift_gem_sids:
            gem_by_set.setdefault(sid, []).append(g)

    # Download DLL for images
    dll_path = sys.argv[1] if len(sys.argv) > 1 else None
    if dll_path and os.path.exists(dll_path):
        with open(dll_path) as f:
            dll_text = f.read()
    else:
        dll_text = fetch(DLL_URL, "ggs.dll.latest.js")
    img_idx = build_img_index(dll_text)

    def item_img(eid):
        return img_idx.get(f"item_unique_{eid}", "")

    def gem_img(gid, reuse_gid=None):
        key = f"gem_{gid}"
        if key in img_idx:
            return img_idx[key]
        if reuse_gid:
            key2 = f"gem_{reuse_gid}"
            if key2 in img_idx:
                return img_idx[key2]
        # Fallback: check if gem reuses an equipment asset
        return ""

    def lang_name(key, fallback=""):
        return lang.get(key.lower(), fallback)

    def set_name(sid):
        n = lang_name(f"equipment_set_{sid}")
        if n:
            return n
        # Fallback: look at first item comment2
        items_for_set = eq_by_set.get(sid, [])
        if items_for_set:
            return items_for_set[0].get("comment2", f"Set {sid}")
        return f"Set {sid}"

    def item_name(eid):
        return lang_name(f"equipment_unique_{eid}") or lang_name(f"equipment_unique_{eid}_name", f"Item {eid}")

    def gem_name(gid):
        return lang_name(f"gem_unique_{gid}") or lang_name(f"gem_{gid}_name") or lang_name(f"gem_{gid}", "")

    # Build output
    sets_out = []
    for sid in sorted(rift_gem_sids, key=lambda x: int(x)):
        items_in_set = eq_by_set.get(sid, [])
        gems_in_set  = gem_by_set.get(sid, [])
        if not items_in_set:
            continue

        wearer_id = str(items_in_set[0].get("wearerID", "2"))
        wearer    = WEARER_NAMES.get(wearer_id, "General")
        sname     = set_name(sid)

        items_out = []
        for e in sorted(items_in_set, key=lambda x: int(x.get("slotID",1))):
            slotid = str(e.get("slotID","1"))
            if slotid not in SLOT_NAMES:
                continue
            eid  = str(e.get("equipmentID",""))
            name = item_name(eid)
            fx   = parse_effects(e.get("effects",""), effects_map, lang)
            items_out.append({
                "id":     eid,
                "name":   name,
                "slot":   SLOT_NAMES[slotid],
                "slotID": slotid,
                "might":  int(e.get("mightValue",0) or 0),
                "effects": fx,
                "img":    item_img(eid),
            })

        gems_out = []
        for idx, g in enumerate(gems_in_set):
            gid   = str(g.get("gemID",""))
            reuse = str(g.get("reuseAssetOfGemID",""))
            name  = gem_name(gid)
            if not name:
                name = f"Gem {idx+1}"
            fx   = parse_effects(g.get("effects",""), effects_map, lang)
            gems_out.append({
                "id":      gid,
                "name":    name,
                "gemType": idx,  # 0-3 for the 4 gem socket positions
                "effects": fx,
                "img":     gem_img(gid, reuse),
            })

        sets_out.append({
            "setID":   int(sid),
            "name":    sname,
            "wearer":  wearer,
            "bonuses": bonus_map.get(sid, []),
            "items":   items_out,
            "gems":    gems_out,
        })

    out = {"generated": __import__("datetime").date.today().isoformat(), "sets": sets_out}
    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",",":"))
    print(f"Wrote rift.json — {len(sets_out)} sets.", file=sys.stderr)

if __name__ == "__main__":
    main()
