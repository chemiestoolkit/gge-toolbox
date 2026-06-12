#!/usr/bin/env python3
"""
Hall of Legends planner data — Maxy's Empire Toolkit.
Shapes the `legendskills` table into two trees (Offense / Defense), each with
tiers of skill nodes; per node the cumulative skill-point cost and total bonus
value at every level. Game data pulled direct from Goodgame by _srcdata/pull.sh.
"""
import json, os, re, urllib.request

_SRC      = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_srcdata", "cache"))
ITEMS_URL = "file://" + os.path.join(_SRC, "items_latest.json")
OUT       = os.path.join(os.path.dirname(__file__), "hol.json")

# Tree id -> display. (0 = offensive skill tree, 1 = defensive.)
TREE_NAME = {"0": "Offense", "1": "Defense"}

# Nicer names for the common effect types; anything else is humanised from camelCase.
NICE = {
    "gateReduction": "Enemy gate reduction", "wallReduction": "Enemy wall reduction",
    "moatReduction": "Enemy moat reduction", "lootBonus": "Loot bonus",
    "honorBonus": "Honour bonus", "attackMeleeBonus": "Melee attack",
    "attackRangeBonus": "Ranged attack", "defenseMeleeBonus": "Melee defence",
    "defenseRangeBonus": "Ranged defence", "cooldownReduction": "Cooldown reduction",
    "travelCostReduction": "Travel-cost reduction", "spyAmountBonus": "Extra spies",
    "smashChanceBonus": "Smash chance", "additionalWave": "Extra attack wave",
    "fireBonus": "Fire strength", "XPAttackPvPBonus": "PvP attack XP",
    "additionalUnitAmountOnFront": "Extra front-line units",
    "gateBonus": "Gate protection", "wallBonus": "Wall protection", "moatBonus": "Moat protection",
    "lootReduction": "Loot loss reduction", "XPConstructionBonus": "Construction XP",
    "XPDefenseBonus": "Defence XP", "guardAmountBonus": "Extra guards",
    "additionalPeasantsAmount": "Extra peasants", "travelConquerBoost": "Conquest travel speed",
}
FLAT = re.compile(r"additional|amount|wave|spy", re.I)


def humanize(et):
    if et in NICE:
        return NICE[et]
    # split camelCase but keep acronym runs (XP, PvP) intact
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", et).strip()
    return s[0].upper() + s[1:] if s else et


def num(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def main():
    with urllib.request.urlopen(ITEMS_URL) as r:
        d = json.loads(r.read().decode("utf-8"))

    groups = {}
    for row in d["legendskills"]:
        g = row["skillGroupID"]
        node = groups.setdefault(g, {
            "tree": row["skillTreeID"], "tier": num(row["tier"]),
            "effectType": row["effectType"], "levels": [],
        })
        node["levels"].append({
            "lvl": num(row["level"]),
            "cost": num(row.get("totalCostSkillPoints")),
            "val": num(row.get("totalEffectValue")),
        })

    trees = {}
    for g, node in groups.items():
        node["levels"].sort(key=lambda x: x["lvl"])
        et = node["effectType"]
        rec = {
            "id": g,
            "name": humanize(et),
            "effectType": et,
            "pct": not bool(FLAT.search(et)),
            "maxLevel": node["levels"][-1]["lvl"],
            "maxCost": node["levels"][-1]["cost"],
            "maxVal": node["levels"][-1]["val"],
            "levels": node["levels"],
        }
        t = trees.setdefault(node["tree"], {})
        t.setdefault(node["tier"], []).append(rec)

    out = {"trees": []}
    for tid in sorted(trees, key=lambda x: num(x)):
        tiers = []
        total = 0
        for tier in sorted(trees[tid]):
            nodes = sorted(trees[tid][tier], key=lambda n: n["id"])
            total += sum(n["maxCost"] for n in nodes)
            tiers.append({"tier": tier, "nodes": nodes})
        out["trees"].append({
            "id": tid, "name": TREE_NAME.get(tid, "Tree " + tid),
            "tiers": tiers, "maxPoints": total,
        })

    json.dump(out, open(OUT, "w"), ensure_ascii=False)
    tot = sum(t["maxPoints"] for t in out["trees"])
    print(f"Wrote hol.json — {len(out['trees'])} trees, "
          f"{sum(len(ti['nodes']) for t in out['trees'] for ti in t['tiers'])} nodes, "
          f"{tot} points to max everything.")


if __name__ == "__main__":
    main()
