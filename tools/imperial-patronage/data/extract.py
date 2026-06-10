#!/usr/bin/env python3
"""Build patronage.json for the Imperial Patronage simulator from the live game
data, mirroring the GeneralsCamp tool's model but pre-resolved to a static file
(no client-side reward resolver needed — patronage rewards are only decorations
and construction items).

Usage:
  python3 extract.py <items_latest.json> <en.json> <ggs.dll.latest.js> > patronage.json
"""
import sys, json, re, datetime

items = json.load(open(sys.argv[1], encoding="utf-8"))
lang = {k.lower(): v for k, v in json.load(open(sys.argv[2], encoding="utf-8")).items()}
dll = open(sys.argv[3], encoding="utf-8", errors="ignore").read()

ASSET = "https://empire-html5.goodgamestudios.com/default/assets/"

# Index every DLL asset path by its leaf token (lowercased), preferring non-shadow.
asset_by_token = {}
for p in re.findall(r"itemassets/[A-Za-z0-9_/]+--\d+", dll):
    leaf = p.split("/")[-1]                       # <Token>--<ts>
    token = re.sub(r"--\d+$", "", leaf).lower()
    if "dropshadow" in token:
        continue
    asset_by_token.setdefault(token, ASSET + p + ".webp")

def asset(token):
    return asset_by_token.get(token.lower())

def by(table, key):
    return {str(r.get(key)): r for r in items.get(table, [])}

currencies = by("currencies", "currencyID")
rewards = by("rewards", "rewardID")
decos = {str(b["wodID"]): b for b in items.get("buildings", []) if str(b.get("name", "")).lower() == "deco"}
cis = by("constructionItems", "constructionItemID")
construction_groups = by("constructionItemGroups", "constructionItemGroupID")

def title(s):
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(s or ""))
    return re.sub(r"[_-]+", " ", s).strip().title()

def currency_label(cid):
    c = currencies.get(str(cid), {})
    name = c.get("Name") or c.get("name") or f"Currency {cid}"
    return lang.get(f"currency_name_{name}".lower()) or title(name), c.get("assetName") or name

def currency_image(asset_name):
    return asset(f"Collectable_Currency_{asset_name}")

def resolve_reward(reward_row):
    """Patronage rewards are a decoration (decoWodID) or construction item(s)."""
    if reward_row.get("decoWodID"):
        d = decos.get(str(reward_row["decoWodID"]))
        if d:
            t = d.get("type", "")
            name = lang.get(f"deco_{t}_name".lower()) or title(t)
            return {"name": name, "img": asset(f"Deco_Building_{t}"), "kind": "decoration"}
    if reward_row.get("constructionItemIDs"):
        first = re.split(r"[&,\s]+", str(reward_row["constructionItemIDs"]).strip())[0]
        ci = cis.get(first)
        if ci:
            nm = ci.get("name", "")
            name = lang.get(f"ci_appearance_{nm}".lower()) or title(nm)
            return {"name": name, "img": asset(f"ConstructionItem_{nm}"), "kind": "construction"}
    return {"name": title(" ".join(filter(None, [reward_row.get("comment2")]))) or "Reward", "img": None, "kind": "other"}

# Group items + rewards by (set, type)
items_by = {}
for it in items.get("donationItems", []):
    items_by.setdefault((str(it["donationItemSetID"]), str(it["donationTypeID"])), []).append(it)
rewards_by = {}
for rw in items.get("donationRewards", []):
    rewards_by.setdefault((str(rw["rewardSetID"]), str(rw["donationTypeID"])), []).append(rw)

# "mason" is a defunct donation track that never shipped in-game — drop it.
types = {str(t["donationTypeID"]): title(t.get("name"))
         for t in items.get("donationTypes", [])
         if str(t.get("name", "")).lower() != "mason"}

def set_label(reward_set_id):
    # Derive a "Mon 'YY" hint from the reward comments when present.
    for rw in rewards_by.get((reward_set_id, "1"), []):
        c = rewards.get(str(rw["rewardID"]), {}).get("comment1", "")
        m = re.search(r"([A-Z][a-z]{2})\s*'?(\d{2})", c)
        if m:
            return f"{m.group(1)} '{m.group(2)}"
    return f"Set {reward_set_id}"

sets_out = []
for s in items.get("donationSettings", []):
    iset, rset = str(s["donationItemSetID"]), str(s["rewardSetID"])
    types_out = {}
    for tid, tlabel in types.items():
        opts = sorted(items_by.get((iset, tid), []), key=lambda x: int(x["donationItemID"]))
        tiers_raw = sorted(rewards_by.get((rset, tid), []), key=lambda x: int(x["minPoints"]))
        if not opts or not tiers_raw:
            continue
        options = []
        for it in opts:
            label, asset_name = currency_label(it["currencyID"])
            ratio = max(1, int(it.get("ratio") or 1))
            cap = it.get("maxPointLimit")
            options.append({
                "label": label,
                "ratio": ratio,
                "maxPoints": int(cap) if cap not in (None, "") else None,
                "img": currency_image(asset_name),
            })
        tiers = []
        for i, rw in enumerate(tiers_raw, 1):
            r = resolve_reward(rewards.get(str(rw["rewardID"]), {}))
            tiers.append({"level": i, "minPoints": int(rw["minPoints"]), **r})
        types_out[tid] = {"label": tlabel, "options": options, "tiers": tiers}
    if types_out:
        sets_out.append({"id": rset, "label": set_label(rset), "types": types_out})

sets_out.sort(key=lambda x: int(x["id"]))
if sets_out:
    sets_out[-1]["latest"] = True

out = {
    "generated": datetime.date.today().isoformat(),
    "typeOrder": list(types.keys()),
    "sets": sets_out,
}
json.dump(out, sys.stdout, separators=(",", ":"))
