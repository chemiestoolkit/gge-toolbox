#!/usr/bin/env python3
"""
Rift dragon egg/grenade data — Maxy's Empire Toolkit.

Everything the egg calculator needs, pulled from Goodgame's own tables:

  units            -> the Magmatic Grenade Flask and Flintlock Gun tiers and how
                      many reserve units each one destroys. The kill amount is in
                      the tool's `effects` as `493&<wodID>+<amount>`, where effect
                      493 is `reserveUnitKillLegendaryDragon`.
  raidBossStages   -> the per-battle mutation rates, from `defenderPostBattleEffects`
                      `488&<wodID>+<percent>` (effect 488 =
                      `mutateReserveUnitLegendaryDragon`). Identical on all 157
                      dragon stage rows: egg 20%, wyrmling 10%, lesser dragon 5%.
                      Also `defenderWallRegenerationEffects` `487&785+<amount>`,
                      the eggs the wall regeneration puts BACK into the reserve.
  raidBossLevels   -> the reserve each dragon level opens with, so the page can
                      prefill the egg count per level instead of making you count.

The mutation is a *post-battle* defender effect, which is why the model is
"subtract the grenade kill, then shrink what is left by 20%" and not the other
way round.

Game data pulled direct from Goodgame by _srcdata/pull.sh.
"""
import json, os, re, datetime

_SRC  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_srcdata", "cache"))
ITEMS = os.path.join(_SRC, "items_latest.json")
LANG  = os.path.join(_SRC, "en.json")
OUT   = os.path.join(os.path.dirname(__file__), "rift-eggs.json")

DRAGON_BOSS_ID = "3"
KILL_EFFECT    = "493"      # reserveUnitKillLegendaryDragon
MUTATE_EFFECT  = "488"      # mutateReserveUnitLegendaryDragon
SPAWN_EFFECT   = "487"      # spawnReserveUnitLegendaryDragon (wall regeneration)

# The dormant chain, in the order it evolves.
CHAIN = ["785", "786", "787", "788"]
TIER_LABEL = {"Weak": "Bronze", "Medium": "Silver", "Strong": "Gold", "Premium": "Gold"}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def parse_effects(blob, effect_id):
    """Pull every `<effect>&<wodID>+<value>` pair for one effect id."""
    out = {}
    for m in re.finditer(re.escape(effect_id) + r"&(\d+)\+([0-9.]+)", blob or ""):
        out[m.group(1)] = float(m.group(2))
    return out


def main():
    items = load(ITEMS)
    root = items.get("dataItems", items)
    lang = load(LANG)
    units = {str(u["wodID"]): u for u in root["units"]}

    def uname(wid):
        u = units.get(str(wid))
        return lang.get(u["type"] + "_name", u["type"]) if u else "wod" + str(wid)

    # --- the kill tools -----------------------------------------------------
    tools = {"egg": [], "wyrmling": []}
    for u in root["units"]:
        t = str(u.get("type", ""))
        if not t.startswith("ARELegendaryDragon") or "KillingTool" not in t:
            continue
        kills = parse_effects(str(u.get("effects", "")), KILL_EFFECT)
        if not kills:
            continue
        target, amount = next(iter(kills.items()))
        tools["egg" if target == "785" else "wyrmling"].append({
            "wodID": int(u["wodID"]),
            "tier": TIER_LABEL.get(str(u.get("comment2", "")), str(u.get("comment2", ""))),
            "name": lang.get(t + "_name", t),
            "target": target,
            "targetName": uname(target),
            "kills": int(amount),
        })
    for k in tools:
        tools[k].sort(key=lambda r: r["kills"])

    # --- mutation + wall-regeneration spawn, from the dragon's stages -------
    levels = {r["raidBossLevelID"]: r for r in root["raidBossLevels"]
              if r["raidBossID"] == DRAGON_BOSS_ID}
    stages = [s for s in root["raidBossStages"] if s["raidBossLevelID"] in levels]

    mut_seen, spawn_by_level = {}, {}
    for s in stages:
        for wid, pct in parse_effects(s.get("defenderPostBattleEffects", ""), MUTATE_EFFECT).items():
            mut_seen.setdefault(wid, set()).add(pct)
        sp = parse_effects(s.get("defenderWallRegenerationEffects", ""), SPAWN_EFFECT)
        if "785" in sp:
            spawn_by_level[s["raidBossLevelID"]] = int(sp["785"])

    mutation = []
    for wid in CHAIN:
        if wid in mut_seen:
            vals = sorted(mut_seen[wid])
            mutation.append({
                "wodID": int(wid), "name": uname(wid), "pct": vals[0],
                "varies": len(vals) > 1,
                "becomes": uname(CHAIN[CHAIN.index(wid) + 1]) if CHAIN.index(wid) + 1 < len(CHAIN) else None,
            })

    # --- per-level opening reserve -----------------------------------------
    out_levels = []
    for lid, L in sorted(levels.items(), key=lambda kv: int(kv[1]["level"])):
        reserve = {}
        for part in str(L.get("courtyardReserveUnits", "")).split("#"):
            if "+" in part:
                w, n = part.split("+")
                reserve[w] = int(n)
        out_levels.append({
            "level": int(L["level"]),
            "eggs": reserve.get("785", 0),
            "wyrmlings": reserve.get("786", 0),
            "lesser": reserve.get("787", 0),
            "great": reserve.get("788", 0),
            "courtyardSize": int(L["courtyardSize"]),
            "wallRegenSeconds": int(L["wallRegenerationTime"]),
            "wallRegenEggs": spawn_by_level.get(lid, 0),
            "minPointsForBossRewards": int(L["minPointsForBossRewards"]),
        })

    out = {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tools": tools,
        "mutation": mutation,
        "levels": out_levels,
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, separators=(",", ":"))
        f.write("\n")

    egg_mut = next((m["pct"] for m in mutation if m["wodID"] == 785), None)
    print(f"rift-eggs.json: {len(tools['egg'])} grenade tiers "
          f"({', '.join(str(t['kills']) for t in tools['egg'])}), "
          f"egg mutation {egg_mut}%, {len(out_levels)} dragon levels "
          f"({out_levels[0]['eggs']:,} to {out_levels[-1]['eggs']:,} eggs)")


if __name__ == "__main__":
    main()
