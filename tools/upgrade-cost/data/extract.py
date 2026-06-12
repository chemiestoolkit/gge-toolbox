#!/usr/bin/env python3
"""
Building upgrade cost & time extractor — Maxy's Empire Toolkit.
Emits per-building, per-level resource cost + build time so the calculator can
total any level range. Game data pulled direct from Goodgame by _srcdata/pull.sh.
"""
import json, os, urllib.request

_SRC      = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_srcdata", "cache"))
ITEMS_URL = "file://" + os.path.join(_SRC, "items_latest.json")
LANG_URL  = "file://" + os.path.join(_SRC, "en.json")
OUT       = os.path.join(os.path.dirname(__file__), "upgrade-cost.json")


def fetch(url):
    with urllib.request.urlopen(url) as r:
        return r.read().decode("utf-8")


def num(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


# cost field -> display label (order = display order)
COST_MAP = [
    ("costWood", "Wood"), ("costStone", "Stone"), ("costCoal", "Coal"),
    ("costOil", "Oil"), ("costGlass", "Glass"), ("costIron", "Iron"),
    ("costC2", "Rubies"), ("costLegendaryToken", "Construction tokens"),
    ("costLegendaryMaterial", "Upgrade tokens"), ("costGoldToken", "Gold tokens"),
    ("costSceatToken", "Sceat tokens"), ("costFloraToken", "Flora tokens"),
    ("costPlaster", "Plaster"), ("costAquamarine", "Aquamarine"),
    ("costDragonScaleTile", "Dragon-scale tiles"),
]


def main():
    d    = json.loads(fetch(ITEMS_URL))
    lang = {k.lower(): v for k, v in json.loads(fetch(LANG_URL)).items() if isinstance(v, str)}

    groups = {}
    for r in d["buildings"]:
        nm = r.get("name")
        if nm:
            groups.setdefault(nm, []).append(r)

    items = []
    for nm, rows in groups.items():
        disp = lang.get(nm.lower() + "_name", "")
        if not disp:
            continue
        rows.sort(key=lambda x: num(x.get("level")))
        levels = []
        for r in rows:
            cost = {}
            for field, label in COST_MAP:
                v = num(r.get(field))
                if v:
                    cost[label] = v
            dur = num(r.get("buildDuration")) // 1000
            if not (cost or dur):              # skip cost-less placeholder rows
                continue
            levels.append({
                "lvl": num(r.get("level")),
                "cost": cost,
                "sec": dur,
                "xp": num(r.get("xp")),
                "req": num(r.get("requiredLevel")),
            })
        if not levels:
            continue
        if levels[-1]["lvl"] > 60:             # drop deco-district junk rows
            continue
        items.append({
            "name": disp,
            "group": rows[-1].get("group", ""),
            "maxLevel": levels[-1]["lvl"],
            "levels": levels,
        })

    items.sort(key=lambda x: x["name"])
    json.dump({"items": items, "count": len(items)}, open(OUT, "w"), ensure_ascii=False)
    print(f"Wrote upgrade-cost.json — {len(items)} buildings with per-level cost/time.")


if __name__ == "__main__":
    main()
