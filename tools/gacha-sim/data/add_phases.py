#!/usr/bin/env python3
"""
Add both phase pools to gachas that change pool mid-event.

extract_gacha.jq keeps one reward set per level, because on most gachas a second
set is just an older version. The Jade Guardian's Chest is different: its sets
are two live pools, labelled "(Phase 1)" and "(Phase 2)" in the item table, and
the game swaps from one to the other at the event's phase switch.

Usage: add_phases.py <items.json> <en.json> <gacha-version.json>
"""
import json
import re
import sys


def number(value):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return value
    return int(f) if f.is_integer() else f


def main(items_path, lang_path, out_path):
    with open(items_path, encoding="utf-8") as fh:
        items = json.load(fh)
    with open(lang_path, encoding="utf-8") as fh:
        lang = {k.lower(): v for k, v in json.load(fh).items() if isinstance(v, str)}
    with open(out_path, encoding="utf-8") as fh:
        data = json.load(fh)

    def text(key):
        return lang.get(key.lower())

    buildings = {str(b["wodID"]): b for b in items["buildings"]}
    units = {str(u["wodID"]): u for u in items["units"]}
    equipment = {e["equipmentID"]: e for e in items["equipments"]}
    build_items = {c["constructionItemID"]: c for c in items["constructionItems"]}
    gems = {str(g["gemID"]): g for g in items["gems"]}
    rewards = {r["rewardID"]: r for r in items["rewards"]}
    tombolas = {}
    for row in items["lootBoxTombolas"]:
        tombolas.setdefault(row["tombolaID"], []).append(row)

    def equipment_name(reward, eid):
        # Older gear has no display name, and its item comment is an internal
        # label such as "Spring Baron Hero". The reward's comment is the real name.
        return text("equipment_unique_" + eid) or reward.get("comment2") or equipment.get(eid, {}).get("comment1") or "Equipment"

    def describe(reward):
        """Name one reward the same way extract_gacha.jq does."""
        if reward is None:
            return {"name": "Unknown", "type": "Unknown", "amount": None}
        if reward.get("decoWodID") is not None:
            b = buildings.get(str(reward["decoWodID"]), {})
            return {"name": text("deco_%s_name" % b.get("type")) or b.get("comment1") or "Decoration",
                    "type": "Decoration", "amount": 1}
        if reward.get("equipmentIDs") is not None:
            eid = str(reward["equipmentIDs"]).split(",")[0]
            return {"name": equipment_name(reward, eid), "type": "Equipment", "amount": 1}
        if reward.get("relicEquipments") is not None:
            eid = str(reward["relicEquipments"]).split(",")[0].split("+")[0]
            return {"name": equipment_name(reward, eid), "type": "Equipment", "amount": 1}
        if reward.get("units") is not None:
            parts = str(reward["units"]).split("+")
            u = units.get(parts[0], {})
            return {"name": text("%s_name" % u.get("type")) or u.get("name") or "Troops", "type": "Units",
                    "amount": number(parts[1] if len(parts) > 1 else parts[0])}
        if reward.get("constructionItemIDs") is not None:
            cid = str(reward["constructionItemIDs"]).split(",")[0]
            c = build_items.get(cid, {})
            return {"name": text("ci_appearance_%s" % c.get("name")) or c.get("comment1") or "Construction Item",
                    "type": "Construction", "amount": 1}
        if reward.get("gemIDs") is not None:
            gid = str(reward["gemIDs"]).split(",")[0]
            return {"name": text("gem_unique_" + gid) or text("gem_%s_name" % gid) or gems.get(gid, {}).get("comment1") or "Gem",
                    "type": "Gem", "amount": 1}
        for key, value in reward.items():
            if key.startswith("add"):
                short = key[3:]
                human = re.sub(r"([A-Z])", r" \1", short).strip()
                return {"name": text("currency_name_" + short) or human, "type": "Resource", "amount": number(value)}
        return {"name": "Reward", "type": "Misc", "amount": None}

    def level_of(row, bonus_style):
        pool = tombolas.get(row["lootBoxTombolaID"])
        if not pool:
            return None
        cost = next(({"what": k[4:], "amount": number(v)} for k, v in row.items()
                     if k.startswith("cost") and (number(v) if isinstance(number(v), (int, float)) else 0) > 0), None)
        entries = []
        for entry in sorted(pool, key=lambda e: -int(e["shares"])):
            named = describe(rewards.get(entry["rewardIDs"].split(",")[0]))
            entries.append({"rarity": int(entry["rewardCategory"]), "shares": int(entry["shares"]),
                            "name": named["name"], "type": named["type"], "amount": named["amount"]})
        level = int(row["gachaLevel"])
        first = int(row["minPulls"]) + 1
        last = int(row["maxPulls"]) + 1 if row.get("maxPulls") is not None else None
        span = "%d+" % first if last is None else str(first) if first == last else "%d-%d" % (first, last)
        name = ("Bonus %d" % (level // 2)) if bonus_style and level % 2 == 0 else "Level %d" % ((level + 1) // 2 if bonus_style else level)
        return {"level": level, "label": "%s (pull%s %s)" % (name, "" if first == last else "s", span),
                "cost": cost, "total": sum(e["shares"] for e in entries), "entries": entries}

    # extract_gacha.jq falls back to the internal label for gems whose name
    # sits under gem_unique_<id>, so "BronzeWardenJade" would reach the page.
    # A label shared by two gems can't say which one it is, so those stay as they are.
    labels = [g.get("comment1") for g in items["gems"]]
    gem_names = {g["comment1"]: text("gem_unique_" + str(g["gemID"]))
                 for g in items["gems"]
                 if g.get("comment1") and labels.count(g["comment1"]) == 1 and text("gem_unique_" + str(g["gemID"]))}
    for event in data["events"]:
        for level in event["levels"]:
            for entry in level["entries"]:
                if entry["type"] == "Gem":
                    entry["name"] = gem_names.get(entry["name"], entry["name"])

    changed = 0
    for event in data["events"]:
        rows = [r for r in items["gachaEvents"] if r["eventID"] == event["eventID"]]
        by_phase = {}
        for r in rows:
            found = re.search(r"\(Phase (\d+)\)", r.get("comment1", ""))
            if found:
                by_phase.setdefault(int(found.group(1)), []).append(r)
        if len(by_phase) < 2:
            continue
        phases = []
        for number_of_phase in sorted(by_phase):
            group = sorted(by_phase[number_of_phase], key=lambda r: int(r["gachaLevel"]))
            # Single-pull levels between the normal ones are the bonus levels.
            bonus_style = all((int(r["gachaLevel"]) % 2 == 0) == (r.get("minPulls") == r.get("maxPulls")) for r in group)
            levels = [lvl for lvl in (level_of(r, bonus_style) for r in group) if lvl]
            phases.append({"name": "Phase %d" % number_of_phase, "levels": levels})
        event["phases"] = phases
        changed += 1

    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("phase pools added to %d event(s) in %s" % (changed, out_path))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
