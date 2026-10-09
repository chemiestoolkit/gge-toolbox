#!/usr/bin/env python3
"""
Rift Point data — Maxy's Empire Toolkit.

Rebuilds the Generals Forum "Rift Raid Point Calculator" from Goodgame's own
tables, because that site was deleted and no copy of its code survives (68 URLs
of the whole domain are archived and none of them is that page).

What the game actually stores:

  raidBossStages.courtyardPointFactor  points for clearing the WHOLE courtyard
  raidBossStages.wallPointFactor       points for clearing a WHOLE wall segment
  raidBossLevels.courtyardSize         how many defenders the courtyard holds
  raidBossStages.{left,front,right}WallUnits  the garrison on each segment,
                                       as `<wodID>+<count>` joined by '#'

Points scale with troops defeated, so a hit that kills a given share of an area
earns that share of the area's factor. The in-game guide text agrees: a hit
that takes out the whole courtyard awards the full courtyard figure.

Worth recording: the toolkit's Rift Raid guide says the courtyard is worth
roughly 10x the wall, but wallPointFactor is exactly half of
courtyardPointFactor on all 57 boss-levels in the data. The table is the
authority here; the per-troop value does favour walls, since a wall segment
holds far fewer defenders than the courtyard, which may be where the 10x
impression came from.

Game data pulled direct from Goodgame by _srcdata/pull.sh.
"""
import json, os, datetime
from pathlib import Path

_SRC  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_srcdata", "cache"))
ITEMS = Path(_SRC, "items_latest.json").as_uri()
LANG  = Path(_SRC, "en.json").as_uri()
OUT   = os.path.join(os.path.dirname(__file__), "rift-points.json")

BOSS_LABEL = {"Necromancer": "Mistress of Decay",
              "FungalSwarm": "Mycelial Sovereign",
              "LegendaryDragon": "Ashen Tyrant"}


def load(uri):
    import urllib.request
    with urllib.request.urlopen(uri) as r:
        return json.loads(r.read().decode("utf-8"))


def unit_total(blob):
    """`784+1500#783+1500#787+500` -> 3500."""
    total = 0
    for part in str(blob or "").split("#"):
        if "+" in part:
            try:
                total += int(part.split("+")[1])
            except ValueError:
                pass
    return total


def main():
    d = load(ITEMS)
    root = d.get("dataItems", d)
    lang = {k.lower(): v for k, v in load(LANG).items()}

    levels = {r["raidBossLevelID"]: r for r in root["raidBossLevels"]}
    stages_by_level = {}
    for s in root["raidBossStages"]:
        stages_by_level.setdefault(s["raidBossLevelID"], []).append(s)

    bosses = []
    for b in sorted(root["raidBosses"], key=lambda r: int(r["raidBossID"])):
        bid, raw = b["raidBossID"], b["name"]
        out_levels = []
        mine = [L for L in levels.values() if L["raidBossID"] == bid]
        for L in sorted(mine, key=lambda r: int(r["level"])):
            st = sorted(stages_by_level.get(L["raidBossLevelID"], []),
                        key=lambda s: -int(s["health"]))
            if not st:
                continue
            out_levels.append({
                "level": int(L["level"]),
                "courtyardFactor": float(st[0].get("courtyardPointFactor") or 0),
                "wallFactor": float(st[0].get("wallPointFactor") or 0),
                "courtyardSize": int(L["courtyardSize"]),
                "minPoints": int(L["minPointsForBossRewards"]),
                "stages": [{
                    "health": int(s["health"]),
                    "left": unit_total(s.get("leftWallUnits")),
                    "front": unit_total(s.get("frontWallUnits")),
                    "right": unit_total(s.get("rightWallUnits")),
                } for s in st],
            })
        bosses.append({
            "id": int(bid),
            "internalName": raw,
            "name": BOSS_LABEL.get(raw, lang.get(("are_boss_" + raw + "_name").lower(), raw)),
            "levels": out_levels,
        })

    out = {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bosses": bosses,
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, separators=(",", ":"))
        f.write("\n")

    tot = sum(len(b["levels"]) for b in bosses)
    print(f"rift-points.json: {len(bosses)} bosses, {tot} levels, "
          f"{sum(len(l['stages']) for b in bosses for l in b['levels'])} stages")


if __name__ == "__main__":
    main()
