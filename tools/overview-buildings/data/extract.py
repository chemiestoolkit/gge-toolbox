#!/usr/bin/env python3
"""
Buildings overview extractor — Maxy's Empire Toolkit.
Groups the per-level `buildings` rows into one card per building: max level,
size, max-count, might, production/storage at max level, resolved area effects,
and the total resource cost + build time to take it from L1 to max.

Game data pulled direct from Goodgame by tools/_srcdata/pull.sh.
Run from build.sh.
"""
import glob, json, os, re, urllib.request

_SRC      = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_srcdata", "cache"))
ITEMS_URL = "file://" + os.path.join(_SRC, "items_latest.json")
LANG_URL  = "file://" + os.path.join(_SRC, "en.json")
OUT       = os.path.join(os.path.dirname(__file__), "buildings.json")
ASSET_ROOT = "https://empire-html5.goodgamestudios.com/default/assets/"


def asset_index():
    """basename(lowercased, sans timestamp) -> full GGS CDN url, from the game's own DLL."""
    dll = open(glob.glob(os.path.join(_SRC, "ggs.dll*"))[0], encoding="utf-8", errors="replace").read()
    idx = {}
    for p in re.findall(r"itemassets/[A-Za-z0-9_/]+--\d+", dll):
        idx[p.rsplit("/", 1)[-1].split("--")[0].lower()] = ASSET_ROOT + p + ".webp"
    return idx


def building_img(idx, raw, max_level):
    """Best skin: highest shipped level asset at or below max level, else any variant."""
    rl = raw.lower()
    # collect every "<raw>_building_level<n>[_variant]" style key (incl. fixed-position piers etc.)
    cands = []
    for k in idx:
        m = re.match(re.escape(rl) + r"_(?:fixedposition)?building_level(\d+)(_.*)?$", k)
        if m:
            cands.append((int(m.group(1)), m.group(2) or "", k))
    if cands:
        below = [c for c in cands if c[0] <= max_level]
        pick = max(below or cands, key=lambda c: (c[0], c[1] == ""))  # highest level, plain variant first
        return idx[pick[2]]
    return idx.get(rl)  # plain key (e.g. Castlewall)


def fetch(url):
    with urllib.request.urlopen(url) as r:
        return r.read().decode("utf-8")


def num(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def main():
    d    = json.loads(fetch(ITEMS_URL))
    lang = {k.lower(): v for k, v in json.loads(fetch(LANG_URL)).items() if isinstance(v, str)}
    eff_name = {str(e["effectID"]): e.get("name", "") for e in d.get("effects", [])}
    idx  = asset_index()

    def L(key, default=""):
        return lang.get(key.lower(), default)

    def effect_label(eid):
        nm = eff_name.get(str(eid), "")
        if not nm:
            return None
        return L("effect_name_" + nm) or re.sub(r"(?<!^)(?=[A-Z])", " ", nm).strip()

    def resolve_effects(raw):
        out = []
        for part in str(raw or "").split(","):
            if "&" not in part:
                continue
            eid, val = part.split("&", 1)
            label = effect_label(eid.strip())
            if not label:
                continue
            v = num(val)
            pct = bool(re.search(r"boost|percent|bonus", eff_name.get(str(eid).strip(), ""), re.I)) and v <= 1000
            out.append({"label": label, "v": v, "pct": pct})
        return out

    # group rows by building name
    groups = {}
    for r in d["buildings"]:
        nm = r.get("name")
        if not nm:
            continue
        groups.setdefault(nm, []).append(r)

    PROD_KEYS = ["Woodproduction", "Stoneproduction", "Foodproduction", "Beefproduction",
                 "Meadproduction", "Honeyproduction", "honeyproduction", "Coalproduction",
                 "Oilproduction", "Glassproduction", "Ironproduction"]
    PROD_LABEL = {"wood": "Wood", "stone": "Stone", "food": "Food", "beef": "Beef",
                  "mead": "Mead", "honey": "Honey", "coal": "Coal", "oil": "Oil",
                  "glass": "Glass", "iron": "Iron"}

    items = []
    for nm, rows in groups.items():
        # real player buildings localise as "<name>_name"; skip internal/deco junk
        disp = L(nm.lower() + "_name")
        if not disp:
            continue
        rows.sort(key=lambda x: num(x.get("level")))
        # buildable rows = have a cost or a real Level type
        buildable = [r for r in rows if num(r.get("costWood")) or num(r.get("costStone"))
                     or str(r.get("type", "")).startswith("Level")]
        rep = (buildable or rows)[-1]            # representative = highest real level
        if rep.get("type") == "Placeholder" and not buildable:
            continue
        max_level = num(rep.get("level"))
        if max_level > 60:                        # drop deco-district rows w/ bogus levels
            continue

        # production at max level
        prod = []
        for k in PROD_KEYS:
            v = num(rep.get(k))
            if v:
                res = k.lower().replace("production", "")
                prod.append({"res": PROD_LABEL.get(res, res.title()), "v": v})
        # storage total at max level
        storage = sum(num(rep.get(k)) for k in rep if k.endswith("Storage"))

        items.append({
            "name": disp,
            "raw": nm,
            "img": building_img(idx, nm, max_level),
            "group": rep.get("group", ""),
            "ground": rep.get("buildingGroundType", ""),
            "maxLevel": max_level,
            "size": f'{num(rep.get("width"))}×{num(rep.get("height"))}',
            "tiles": num(rep.get("width")) * num(rep.get("height")),
            "maxCount": num(rep.get("maximumCount")),
            "might": num(rep.get("mightValue")),
            "reqLevel": num(rep.get("requiredLevel")),
            "costWood": sum(num(r.get("costWood")) for r in buildable),
            "costStone": sum(num(r.get("costStone")) for r in buildable),
            "buildSec": sum(num(r.get("buildDuration")) for r in buildable) // 1000,
            "prod": prod,
            "storage": storage,
            "effects": resolve_effects(rep.get("areaSpecificEffects")),
        })

    items.sort(key=lambda x: (-x["might"], x["name"]))
    json.dump({"items": items, "count": len(items)}, open(OUT, "w"), ensure_ascii=False)
    print(f"Wrote buildings.json — {len(items)} buildings.")


if __name__ == "__main__":
    main()
