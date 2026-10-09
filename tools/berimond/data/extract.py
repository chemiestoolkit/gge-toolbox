#!/usr/bin/env python3
"""
Berimond overview data — Maxy's Empire Toolkit.

Every Berimond watchtower and camp on the map, with what it pays and what sits
in it. Shaped from Goodgame's own tables:

  specialcamps  one row per map object. The placed ones (those with CampPosX /
                CampPosY) are the Berimond targets. `lootc2` is the ruby payout
                and `lootc1` the coins, using GGS's internal currency naming.
                The rubies are what the game prints under each tower on the map
                (capitals excepted), and `dungeonlevel` is the camp's level.
                `attacksUntilDestroyed` is carried through as-is: it runs into
                the tens of thousands on some camps, so it is not a simple
                attack count and is not presented as one.
  dungeons      the garrisons. A camp's `countVictories` is a '#'-separated list
                of references; each one points at a dungeons row with kID 10 and
                the lord for that side of the map, whose unitsL/M/R/K hold
                '<wodID>+<amount>' stacks. Summing those gives the defenders,
                and a camp listing several references has a range.

Sides: lanes 1-4 belong to lord -105, the rest to -106, which is how the same
camp layout serves both factions.

Game data pulled direct from Goodgame by _srcdata/pull.sh.
"""
import json, os, re, datetime
from pathlib import Path

_SRC  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_srcdata", "cache"))
ITEMS = Path(_SRC, "items_latest.json").as_uri()
OUT   = os.path.join(os.path.dirname(__file__), "berimond.json")
CDN   = "https://empire-html5.goodgamestudios.com/default/assets/"

DUNGEON_KID = "10"
LORD_LOW_LANES = "-105"      # lanes 1-4
LORD_HIGH_LANES = "-106"


def load(uri):
    import urllib.request
    with urllib.request.urlopen(uri) as r:
        return json.loads(r.read().decode("utf-8"))


def num(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def stack_total(blob):
    """'604+3#606+3#652+45' -> 51."""
    total = 0
    for part in str(blob or "").split("#"):
        if "+" in part:
            total += num(part.split("+")[1])
    return total


def dll_asset(dll, name):
    m = re.search(r"itemassets/[A-Za-z0-9_/]*" + re.escape(name) + r"--\d+", dll)
    return CDN + m.group(0) + ".webp" if m else None


def main():
    d = load(ITEMS)
    root = d.get("dataItems", d)
    camps_raw = root["specialcamps"]
    dungeons = root.get("dungeons", [])

    # index the garrisons once: (lordID, countVictories) -> total defenders
    garrison = {}
    for row in dungeons:
        if str(row.get("kID")) != DUNGEON_KID:
            continue
        key = (str(row.get("lordID")), str(row.get("countVictories")))
        garrison[key] = sum(stack_total(row.get(side))
                            for side in ("unitsL", "unitsM", "unitsR", "unitsK"))

    camps = []
    for c in camps_raw:
        if c.get("CampPosX") is None or c.get("CampPosY") is None:
            continue
        lane = num(c.get("laneID"))
        lord = LORD_LOW_LANES if lane <= 4 else LORD_HIGH_LANES
        totals = [garrison[(lord, ref)] for ref in str(c.get("countVictories") or "").split("#")
                  if ref and (lord, ref) in garrison]
        camps.append({
            "id": num(c.get("specialcampID")),
            "type": c.get("type"),
            "x": num(c.get("CampPosX")),
            "y": num(c.get("CampPosY")),
            "lane": lane,
            "level": num(c.get("dungeonlevel")),
            "rubies": num(c.get("lootc2")),
            "coins": num(c.get("lootc1")),
            "attacks": num(c.get("attacksUntilDestroyed")),
            "defenceMin": min(totals) if totals else None,
            "defenceMax": max(totals) if totals else None,
            "villages": num(c.get("villageCount")),
            "wood": num(c.get("lootWood")),
            "stone": num(c.get("lootStone")),
            "food": num(c.get("lootFood")),
        })
    camps.sort(key=lambda c: (c["lane"], -c["rubies"], c["id"]))

    # The game draws ONE tower sprite and ONE capital sprite on the Berimond
    # map, tinted by faction — it does not vary the art by camp level. An
    # earlier pass mapped each level onto a different FactionWatchtower tier,
    # which invented a visual hierarchy that is not in the game. One sprite per
    # kind, used for every camp of that kind.
    art = {"tower": None, "capital": None}
    dll_path = None
    for f in os.listdir(_SRC):
        if f.startswith("ggs.dll"):
            dll_path = os.path.join(_SRC, f)
            break
    if dll_path:
        dll = open(dll_path, encoding="utf-8", errors="replace").read()
        art["tower"] = dll_asset(dll, "FactionWatchtower_Building_Level5")
        art["capital"] = dll_asset(dll, "FactionUnitCamp_Building_Level5")

    out = {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "camps": camps,
        "art": art,
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, separators=(",", ":"))
        f.write("\n")

    rub = [c["rubies"] for c in camps if c["rubies"]]
    print(f"berimond.json: {len(camps)} placed camps "
          f"({sum(1 for c in camps if c['type'] == 'CAPITAL')} capitals), "
          f"rubies {min(rub):,}-{max(rub):,}, "
          f"{sum(1 for c in camps if c['defenceMin'] is not None)} with garrisons, "
          f"art tower={'ok' if art['tower'] else 'MISSING'} capital={'ok' if art['capital'] else 'MISSING'}")


if __name__ == "__main__":
    main()
