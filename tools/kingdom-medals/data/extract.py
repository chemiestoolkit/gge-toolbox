#!/usr/bin/env python3
"""
Kingdom's League medal data — Maxy's Empire Toolkit.

Shapes three game tables into one small file the calculator can read:

  seasonMedals  -> which medal each division-ranking position pays, and the
                   medal points it is worth.
  seasonRanks   -> the 21 kingdom titles (majorRank/minorRank pairs), with the
                   medal points each promotion step costs.
  seasonSettings-> season/promotion pass prices, shown for reference only.

Title names come from the language bundle as `seasonLeague_rank_<n>`, medal
names as `seasonLeague_<type>_name`.

One modelling note, because the game data is not explicit about it:
`minMedalPointsForUnlock` is 2000 on every rank from 2 upwards. Read as an
absolute threshold that would mean every title unlocks at 2000 points, which
cannot be right, so it is the cost of *that* promotion step. We therefore
publish a running total rather than hardcoding 2000, so a future change to any
single step is picked up automatically.

Game data pulled direct from Goodgame by _srcdata/pull.sh.
"""
import json, os, datetime

_SRC  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_srcdata", "cache"))
ITEMS = os.path.join(_SRC, "items_latest.json")
LANG  = os.path.join(_SRC, "en.json")
OUT   = os.path.join(os.path.dirname(__file__), "kingdom-medals.json")

# Medal type -> the file name we ship the sprite-sheet crop under.
MEDAL_IMG = {
    "goldMedal": "gold.webp", "silverMedal": "silver.webp", "bronzeMedal": "bronze.webp",
    "glasMedal": "glass.webp", "copperMedal": "copper.webp", "stoneMedal": "stone.webp",
    "woodMedal": "wood.webp",
}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    items = load(ITEMS)
    root = items.get("dataItems", items)
    lang = load(LANG)

    medals = []
    for m in sorted(root["seasonMedals"], key=lambda r: int(r["minHighscoreRank"])):
        t = m["type"]
        medals.append({
            "id": int(m["medalID"]),
            "type": t,
            "name": lang.get(f"seasonLeague_{t}_name", t),
            "minPosition": int(m["minHighscoreRank"]),
            "points": int(m["medalPoints"]),
            "img": MEDAL_IMG.get(t, ""),
        })
    # The last tier is the floor: any position at or below it pays that medal.
    if medals:
        medals[-1]["isFloor"] = True

    ranks, total = [], 0
    for r in sorted(root["seasonRanks"], key=lambda r: int(r["rankID"])):
        rid = int(r["rankID"])
        step = int(r["minMedalPointsForUnlock"])
        total += step                         # rank 1 carries 0, so this lines up
        ranks.append({
            "id": rid,
            "title": lang.get(f"seasonLeague_rank_{rid}", f"Rank {rid}"),
            "major": int(r["majorRank"]),
            "minor": int(r["minorRank"]),
            "stepPoints": step,
            "totalPoints": total,
        })

    st = (root.get("seasonSettings") or [{}])[0]
    out = {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "itemsVersion": items.get("version") or items.get("Version") or None,
        "payoutPerDay": 1,          # "Medals: Awarded once a day according to your current division ranking"
        "medals": medals,
        "ranks": ranks,
        "passPrices": {
            "promotion": int(st["seasonPassPromotionPrice"]) if st.get("seasonPassPromotionPrice") else None,
            "eventEnd": int(st["seasonPassEventEndPrice"]) if st.get("seasonPassEventEndPrice") else None,
            "fullDiscountPct": int(st["seasonPassFullDiscount"]) if st.get("seasonPassFullDiscount") else None,
            "singleDiscountPct": int(st["seasonPassSingleDiscount"]) if st.get("seasonPassSingleDiscount") else None,
        },
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, separators=(",", ":"))
        f.write("\n")
    print(f"kingdom-medals.json: {len(medals)} medals, {len(ranks)} titles, "
          f"top title '{ranks[-1]['title']}' at {ranks[-1]['totalPoints']:,} points")


if __name__ == "__main__":
    main()
