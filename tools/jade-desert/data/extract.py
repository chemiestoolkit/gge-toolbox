#!/usr/bin/env python3
"""
Jade Desert data for Maxy's Empire Toolkit.

Everything on the BTH: Jade pages comes from Goodgame's own item table and
language file. The Jade mode is scoring 3 ("AllianceJade") of event 113.

Two things here are deliberately not taken at face value:

  Rewards   Sets 6 (alliance) and 7 (solo) are the Jade reward tables and are
            what the page shows for normal runs. The event settings still point
            normal runs at sets 1 and 3, so `pending` stays true until they move.

  Relic     Items 790.01 added levels 31-60 and Jade Stone prices to five relic
            build items. 790.02 took them back out. relic-preview.json keeps
            that one snapshot, and `live` flips by itself if they return.
"""
import datetime
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "_srcdata", "cache"))
OUT = os.path.join(HERE, "jade-desert.json")
PREVIEW = os.path.join(HERE, "relic-preview.json")
JADE = "3"


def read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


items = read(os.path.join(SRC, "items_latest.json"))
LANG = {k.lower(): v for k, v in read(os.path.join(SRC, "en.json")).items() if isinstance(v, str)}
REWARDS = {r["rewardID"]: r for r in items["rewards"]}
CIS = {c["constructionItemID"]: c for c in items["constructionItems"]}
UNITS = {str(u["wodID"]): u for u in items["units"]}
BUILDINGS = {str(b["wodID"]): b for b in items["buildings"]}
EQUIP = {e["equipmentID"]: e for e in items["equipments"]}
GEMS = {str(g["gemID"]): g for g in items["gems"]}


def num(v, default=0):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return int(f) if f.is_integer() else f


def t(key, fallback=None):
    return LANG.get(key.lower(), fallback)


# The game's currency keys are not always the reward column's name.
CURRENCY_KEY = {"JadeStone": "jadestones"}
MATERIAL = {"CommonTimber": "Timber", "CommonStraw": "Straw", "RareNails": "Nails",
            "RareGlue": "Glue", "EpicCobblestone": "Cobblestone", "LegendaryFabric": "Fabric"}


def currency(name):
    if name in MATERIAL:
        return MATERIAL[name]
    return t("currency_name_" + CURRENCY_KEY.get(name, name)) or re.sub(r"(?<!^)([A-Z])", r" \1", name)


def ci_name(ci):
    raw = ci.get("name", "")
    # The Jade Granary's item row still carries a placeholder name.
    if raw == "namependingTCIMaterials":
        raw = "jadeGranary"
    return t("ci_appearance_" + raw) or raw


def reward_parts(reward):
    """Every separate thing a reward row grants, named the way the game names it."""
    if not reward:
        return []
    out = []
    for key, value in reward.items():
        if key.startswith("add"):
            out.append({"n": currency(key[3:]), "a": num(value), "k": "Resource"})
    if reward.get("currency2"):
        out.append({"n": "Rubies", "a": num(reward["currency2"]), "k": "Resource"})
    if reward.get("currency1"):
        out.append({"n": "Coins", "a": num(reward["currency1"]), "k": "Resource"})
    if reward.get("decoWodID"):
        b = BUILDINGS.get(str(reward["decoWodID"]), {})
        out.append({"n": t("deco_%s_name" % b.get("type", ""), b.get("comment1", "Decoration")), "a": 1, "k": "Decoration"})
    for field in ("equipmentIDs", "relicEquipments"):
        for raw in str(reward.get(field, "")).replace("#", ",").split(","):
            eid = raw.split("+")[0]
            if eid:
                # Older gear has no display-name key. Its item comment is an
                # internal label, so the reward's own comment reads better.
                name = t("equipment_unique_" + eid) or reward.get("comment2") or EQUIP.get(eid, {}).get("comment1", "Equipment")
                out.append({"n": name, "a": 1, "k": "Equipment"})
    if reward.get("units"):
        for part in str(reward["units"]).split("#"):
            uid, _, amount = part.partition("+")
            u = UNITS.get(uid, {})
            out.append({"n": t("%s_name" % u.get("type", ""), u.get("name", "Troops")), "a": num(amount, 1), "k": "Troops"})
    if reward.get("constructionItemIDs"):
        for cid in re.split("[#,]", str(reward["constructionItemIDs"])):
            ci = CIS.get(cid)
            if ci:
                out.append({"n": ci_name(ci), "a": 1, "k": "Build item", "id": cid})
    if reward.get("gemIDs"):
        for gid in str(reward["gemIDs"]).split(","):
            out.append({"n": t("gem_unique_" + gid) or t("gem_%s_name" % gid, GEMS.get(gid, {}).get("comment1", "Gem")), "a": 1, "k": "Gem"})
    return out


def tombola(tid):
    rows = [r for r in items["lootBoxTombolas"] if r["tombolaID"] == str(tid)]
    total = sum(num(r["shares"]) for r in rows)
    entries = []
    for r in rows:
        parts = []
        for rid in r["rewardIDs"].split(","):
            parts += reward_parts(REWARDS.get(rid))
        entries.append({"r": num(r.get("rewardCategory")), "p": round(num(r["shares"]) * 100 / total, 4),
                        "n": " + ".join(p["n"] for p in parts) or "Reward",
                        "a": parts[0]["a"] if len(parts) == 1 else None,
                        "k": parts[0]["k"] if parts else "Misc"})
    entries.sort(key=lambda e: -e["p"])
    return entries


def citadel():
    out = []
    for c in sorted(items["allianceCitadels"], key=lambda r: num(r["level"])):
        protection = c.get("protectionModeDuration")
        out.append({"level": num(c["level"]), "radius": num(c["radius"]),
                    "cost": num(c["costAncientJadeStatuette"]),
                    "exposed": num(c.get("exposedStatuettesPercentage")),
                    "wallUnits": num(c.get("unitWallCount")), "guards": num(c.get("guards")),
                    "protectionH": num(protection) / 3600 if protection else None})
    return out


def fortresses():
    camps = [c for c in items["resourceCamps"] if c.get("allianceBattleGroundScoringID") == JADE]
    kinds = {}
    for c in camps:
        kinds.setdefault(c["resourceCampTypeID"], []).append(c)
    names = {x["currencyID"]: x["Name"] for x in items["currencies"]}
    types = [{"name": re.sub(r" Level \d+$", "", rows[0]["name"]),
              "drops": currency(names[rows[0]["lootPoolCurrencyID"]])}
             for _, rows in sorted(kinds.items())]
    first = sorted(next(iter(kinds.values())), key=lambda r: num(r["level"]))
    tiers = [{"tier": i + 1, "level": num(c["level"]), "def": num(c["defStrength"]), "pool": num(c["lootPoolCapacity"]),
              "wall": num(c["wallBonus"]), "gate": num(c["gateBonus"]), "guards": num(c["guards"]),
              "wallUnits": num(c["unitWallCount"])} for i, c in enumerate(first)]
    return {"types": types, "tiers": tiers, "cooldownH": num(first[0]["cooldownSeconds"]) / 3600,
            "travel": num(first[0]["travelCostMultiplier"]), "extraLoot": tombola(first[0]["lootBoxTombolaID"])}


def oases():
    return [{"level": num(c["level"]), "stock": num(c["resourceLimit"]), "maxArmy": num(c["maxArmySize"]),
             "cooldownH": num(c["cooldownSeconds"]) / 3600}
            for c in sorted(items["tradingCamps"], key=lambda r: num(r["level"]))
            if c.get("allianceBattleGroundScoringID") == JADE]


def trades():
    out = []
    for row in items["trades"]:
        if row["tradeGroupID"] != "1":
            continue
        reward = REWARDS[row["mainRewardID"]]
        cost = {currency(k[4:]): num(v) for k, v in row.items() if k.startswith("cost")}
        units = sum(num(p.split("+")[1]) for p in reward["units"].split("#"))
        out.append({"gives": reward["comment2"], "units": units, "cost": cost,
                    "stock": num(row["resourceConsumed"]), "capacity": num(row["lootCapacityCost"])})
    return out


def crafting():
    out = []
    for r in items["craftingRecipes"]:
        if r.get("allianceBattleGroundScoringIDs") != JADE:
            continue
        reward = REWARDS[r["rewardIDs"].split(",")[0]]
        made = next(k[3:] for k in reward if k.startswith("add"))
        out.append({"id": num(r["craftingRecipeId"]), "type": r["type"],
                    "building": "Toolsmith" if r["queueTypeId"] == "2" else "Refinery",
                    "makes": currency(made), "amount": num(reward["add" + made]),
                    "hours": num(r["craftingDuration"]) / 3600, "rubies": num(r.get("costC2")),
                    "skip": num(r.get("skipCostC2")),
                    "cost": {currency(k[4:]): num(v) for k, v in r.items() if k.startswith("cost") and k != "costC2"}})
    return sorted(out, key=lambda x: x["id"])


def bonuses():
    effects = {e["effectID"]: e["name"] for e in items["effects"]}
    series = {}
    for b in items["alliancebuffs"]:
        if JADE in str(b.get("allianceBattleGroundScoringIDs", "")).split(",") and num(b["level"]) > 0:
            series.setdefault(b["allianceBuffSeriesID"], []).append(b)
    out = []
    for sid, rows in sorted(series.items(), key=lambda kv: num(kv[0])):
        rows.sort(key=lambda r: num(r["level"]))
        temporary = bool(rows[0].get("isTemporary"))
        name = effects[rows[0]["effects"].split("&")[0]].lower()
        title = t("dialog_alliance_%sboost_%s" % ("temporary" if temporary else "permanent", name), name)
        levels = [{"level": num(r["level"]), "value": num(re.split("[&+]", r["effects"].split(",")[0])[-1]),
                   "cost": num(r.get("costC2")),
                   "hours": num(r["duration"]) / 3600 if r.get("duration") else None} for r in rows]
        out.append({"id": num(sid), "name": title, "temporary": temporary,
                    "unit": "" if "hideout" in name else "%", "levels": levels,
                    "total": sum(l["cost"] for l in levels)})
    return out


EFFECT_LABEL = {"296": "mead/h", "298": "honey/h"}
REDUCTION = {"Meadreduction": "mead use", "Beefreduction": "beef use"}


def build_item(ci):
    bits = []
    for part in str(ci.get("effects") or "").split(","):
        eid, _, value = part.partition("&")
        if eid in EFFECT_LABEL:
            bits.append("+%s %s" % (format(num(value), ","), EFFECT_LABEL[eid]))
    for field, label in REDUCTION.items():
        if ci.get(field):
            bits.append("-%s%% %s" % (ci[field], label))
    tier = re.search(r"\bT(\d)\b", ci.get("comment2", ""))
    return {"name": ci_name(ci), "tier": int(tier.group(1)) if tier else None, "effect": ", ".join(bits),
            "days": round(num(ci.get("duration")) / 86400) if ci.get("duration") else None}


def rewards():
    jade = {"alliance": "6", "solo": "7"}
    settings = {}
    for s in items["allianceBattleGroundSettings"]:
        if s.get("scoringID") == JADE:
            kind = "beta" if s.get("isBetaRun") else "normal"
            settings[kind] = {"alliance": s["allianceRewardSetID"], "solo": s["playerRewardSetID"]}
    assign = {"normal": jade, "beta": settings["beta"]}
    wanted = set(jade.values()) | set(settings["beta"].values())
    sets = {}
    for row in items["allianceBattleGroundRankRewards"]:
        if row["eventID"] == "113" and row["rewardSetID"] in wanted:
            sets.setdefault(row["rewardSetID"], []).append(row)
    out = {}
    for sid, rows in sets.items():
        rows.sort(key=lambda r: num(r["rank"]))
        brackets, low = [], 1
        for row in rows:
            high = num(row["rank"])
            reward = REWARDS[row["rewardID"]]
            parts = [p for p in reward_parts(reward) if p["k"] != "Build item"]
            ids = re.split("[#,]", str(reward.get("constructionItemIDs", ""))) if reward.get("constructionItemIDs") else []
            brackets.append({"from": low, "to": high, "items": [{"n": p["n"], "a": p["a"]} for p in parts],
                             "build": [build_item(CIS[i]) for i in ids if i in CIS]})
            low = high + 1
        out[sid] = {"brackets": brackets}
    return {"assign": assign, "pending": settings["normal"] != jade, "sets": out}


def gacha():
    rows = [r for r in items["gachaEvents"] if r["eventID"] == "139"]
    phases = {}
    for r in rows:
        level = num(r["gachaLevel"])
        bonus = level % 2 == 0
        phases.setdefault(r["rewardSetID"], []).append({
            "index": level, "label": ("Bonus %d" % (level // 2)) if bonus else ("Level %d" % ((level + 1) // 2)),
            "bonus": bonus, "from": num(r["minPulls"]) + 1,
            "to": num(r["maxPulls"]) + 1 if r.get("maxPulls") is not None else None,
            "cost": num(r["costJadeGachaToken"]), "entries": tombola(r["lootBoxTombolaID"])})
    for levels in phases.values():
        levels.sort(key=lambda x: x["index"])
    return {"name": t("event_title_139", "Jade Guardian's Chest"),
            "phase1": phases.get("1", []), "phase2": phases.get("2", [])}


def relic():
    flank = [c for c in items["constructionItems"] if c.get("name") == "attackUnitAmountFlank"]
    snapshot = read(PREVIEW)
    snapshot["live"] = len(flank) > 30
    return snapshot


setting = next(s for s in items["allianceBattleGroundSettings"] if s.get("scoringID") == JADE and not s.get("isBetaRun"))
triggers = {r["phaseTriggerID"]: r for r in items["allianceBattleGroundPhaseTriggers"]}
early = triggers["2"]
max_alliances = num(setting.get("maxParticipatingAlliances"), 5000)

data = {
    "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "itemsVersion": ((items.get("versionInfo") or {}).get("version") or {}).get("@value"),
    "event": {"peaceH": num(setting["peaceDuration"]) / 3600, "maxMembers": num(setting.get("maxAllianceSize")),
              "maxAlliances": max_alliances, "phase2Hours": num(triggers["1"]["timerOffset"]) / 3600,
              "earlyLevel": num(early["citadelLevel"]), "earlyShare": num(early["allianceShare"]),
              "earlyMin": num(early["minAlliances"])},
    "citadel": citadel(),
    "fortresses": fortresses(),
    "oases": oases(),
    "trades": trades(),
    "crafting": crafting(),
    "bonuses": bonuses(),
    "rewards": rewards(),
    "gacha": gacha(),
    "relic": relic(),
}

with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
print("jade-desert.json: items %s, %d bonuses, %d recipes, %d reward sets" % (
    data["itemsVersion"], len(data["bonuses"]), len(data["crafting"]), len(data["rewards"]["sets"])))
