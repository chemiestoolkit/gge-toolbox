#!/usr/bin/env python3
"""
Troops & Tools extractor — Maxy's Empire Toolkit.
Units with combat stats + siege/defence tools, names from lang, images from the
DLL asset map (itemassets/Units/<building>/<building>_Unit_<type>/).
Run: python3 extract.py [ggs.dll.js path]
"""
import json, sys, os, re, urllib.request

ITEMS_URL = "https://raw.githubusercontent.com/GeneralsCamp/ggempire-data-cache/main/public/data/empire/items_latest.json"
LANG_URL  = "https://raw.githubusercontent.com/GeneralsCamp/ggempire-data-cache/main/public/data/lang/en.json"
DLL_URL   = "https://raw.githubusercontent.com/GeneralsCamp/ggempire-data-cache/main/public/data/empire/dll/ggs.dll.latest.js"
CDN       = "https://empire-html5.goodgamestudios.com/default/assets/"
OUT       = os.path.join(os.path.dirname(__file__), "troops-tools.json")


def fetch(url, label):
    print(f"  Downloading {label}…", file=sys.stderr)
    with urllib.request.urlopen(url) as r:
        return r.read().decode("utf-8")


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0


def main():
    d    = json.loads(fetch(ITEMS_URL, "items_latest.json"))
    lang = {k.lower(): v for k, v in json.loads(fetch(LANG_URL, "lang/en.json")).items()
            if isinstance(v, str)}

    dll_path = sys.argv[1] if len(sys.argv) > 1 else None
    if dll_path and os.path.exists(dll_path):
        dll = open(dll_path, encoding="utf-8", errors="ignore").read()
    else:
        dll = fetch(DLL_URL, "ggs.dll.latest.js")

    # type (lowercased) -> full asset path
    img_idx = {}
    for m in re.finditer(r"itemassets/Units/[A-Za-z0-9]+/[A-Za-z0-9]+_Unit_([A-Za-z0-9]+)/[A-Za-z0-9_]+--\d+", dll):
        img_idx.setdefault(m.group(1).lower(), m.group(0))

    def name_of(u):
        return lang.get(u.get("type", "").lower() + "_name", "")

    def img_of(u):
        p = img_idx.get(u.get("type", "").lower())
        return CDN + p + ".webp" if p else ""

    troops, tools = [], []

    # Attack tools REDUCE the defender's wall/gate/moat protection;
    # defence tools INCREASE protection / unit strength. Phrasing matches in-game text.
    TOOL_EFFECTS = [
        ("wallBonus",     "atk", "-{v}% wall protection"),
        ("gateBonus",     "atk", "-{v}% gate protection"),
        ("moatBonus",     "atk", "-{v}% moat protection"),
        ("wallBonus",     "def", "+{v}% wall protection"),
        ("gateBonus",     "def", "+{v}% gate protection"),
        ("moatBonus",     "def", "+{v}% moat protection"),
        ("offMeleeBonus", "atk", "+{v}% melee attack strength"),
        ("offRangeBonus", "atk", "+{v}% ranged attack strength"),
        ("defMeleeBonus", "def", "+{v}% melee defence strength"),
        ("defRangeBonus", "def", "+{v}% ranged defence strength"),
        ("offMeleeBonus", "def", "+{v}% melee strength"),
        ("offRangeBonus", "def", "+{v}% ranged strength"),
        ("defMeleeBonus", "atk", "-{v}% defender melee strength"),
        ("defRangeBonus", "atk", "-{v}% defender ranged strength"),
        ("fameBonus",      "*",  "+{v}% glory points"),
        ("pointBonus",     "*",  "+{v}% event points"),
        ("ragePointBonus", "*",  "+{v}% rage points"),
        ("khanTabletBooster", "*", "+{v}% Khan tablets"),
        ("samuraiTokenBooster", "*", "+{v}% Samurai tokens"),
        ("pearlBooster",   "*",  "+{v}% pearls"),
    ]

    # Combo/Elite/raid-boss tools encode their punch as "effectID&value,…" pairs
    # pointing into the global `effects` table; templates keyed by effect name.
    EFFECT_LINES = {
        "additionalWaves":               "+{v} attack wave(s)",
        "attackBonus":                   "+{v}% attack unit strength",
        "AttackBoostYard":               "+{v}% courtyard attack strength",
        "bonusWallCapacity":             "+{v}% wall unit limit",
        "bonusDefencePower":             "+{v}% defence unit strength",
        "bonusYardDefensePower":         "+{v}% courtyard defence strength",
        "killDefendingMeleeTroopsYard":  "kills {v} melee defenders in the courtyard",
        "killDefendingRangedTroopsYard": "kills {v} ranged defenders in the courtyard",
        "killDefendingAnyTroopsYard":    "kills {v} defenders in the courtyard",
        "killAttackingMeleeTroopsYard":  "kills {v} melee attackers in the courtyard",
        "killAttackingRangedTroopsYard": "kills {v} ranged attackers in the courtyard",
        "killAttackingAnyTroopsYard":    "kills {v} attackers in the courtyard",
        "meleeDefenseMalus":             "-{v}% defender melee strength",
        "rangeDefenseMalus":             "-{v}% defender ranged strength",
        "infectionRateBaseMalus":        "-{v}% zombie infection rate",
        "reserveUnitKill":               "kills {v} units from the enemy reserve",
        "reserveUnitKillLegendaryDragon": "kills {v} units from the enemy reserve",
        "raidBossWallRegenerationDelayLeft":  "+{v}s left flank wall regeneration cooldown",
        "raidBossWallRegenerationDelayFront": "+{v}s front wall regeneration cooldown",
        "raidBossWallRegenerationDelayRight": "+{v}s right flank wall regeneration cooldown",
        "raidBossWallRegenerationDelayAll":   "+{v}s wall regeneration cooldown on all flanks",
        "raidBossWallRegenerationDelayLeftLegendaryDragon":  "+{v}s left flank wall regeneration cooldown",
        "raidBossWallRegenerationDelayFrontLegendaryDragon": "+{v}s front wall regeneration cooldown",
        "raidBossWallRegenerationDelayRightLegendaryDragon": "+{v}s right flank wall regeneration cooldown",
        "raidBossWallRegenerationDelayAllLegendaryDragon":   "+{v}s wall regeneration cooldown on all flanks",
    }
    effect_names = {str(e.get("effectID")): e.get("name", "") for e in d.get("effects", [])}

    def effect_ref_lines(u):
        lines = []
        for part in str(u.get("effects") or "").split(","):
            if "&" not in part:
                continue
            eid, _, raw = part.partition("&")
            v = num(raw)
            v = int(v) if v == int(v) else v
            ename = effect_names.get(eid.strip(), "")
            tpl = EFFECT_LINES.get(ename)
            if tpl:
                lines.append(tpl.format(v=v))
            elif ename:
                lines.append(f"{ename}: {v}")
        return lines

    for u in d["units"]:
        name = name_of(u)
        if not name:
            continue
        is_tool = bool(u.get("toolCategory"))
        if is_tool:
            side = "atk" if u.get("typ") == "Attack" else "def"
            lines = []
            for field, want, tpl in TOOL_EFFECTS:
                if want != "*" and want != side:
                    continue
                v = num(u.get(field))
                if v:
                    lines.append(tpl.format(v=int(v) if v == int(v) else v))
            lines += effect_ref_lines(u)
            tools.append({
                "id":    u["wodID"],
                "name":  name,
                "kind":  "Tool",
                "side":  "Attack" if side == "atk" else "Defence",
                "cat":   u.get("toolCategory", ""),
                "lvl":   int(num(u.get("level"))),
                "speed": int(num(u.get("speed"))),
                "might": int(num(u.get("mightValue"))),
                "effects": lines,
                "img":   img_of(u),
            })
        else:
            ma, ra = num(u.get("meleeAttack")), num(u.get("rangeAttack"))
            md, rd = num(u.get("meleeDefence")), num(u.get("rangeDefence"))
            if not (ma or ra or md or rd):
                continue
            troops.append({
                "id":    u["wodID"],
                "name":  name,
                "kind":  "Troop",
                "role":  (u.get("role") or "").capitalize(),
                "meleeAtk": int(ma), "rangeAtk": int(ra),
                "meleeDef": int(md), "rangeDef": int(rd),
                "atk":   int(max(ma, ra)),
                "def":   int(max(md, rd)),
                "speed": int(num(u.get("speed"))),
                "loot":  int(num(u.get("lootValue"))),
                "food":  int(num(u.get("foodSupply"))),
                "might": int(num(u.get("mightValue"))),
                "img":   img_of(u),
            })

    # De-duplicate identical name+stats rows (same unit appears per building level)
    seen, troops_out = set(), []
    for t in sorted(troops, key=lambda x: int(x["id"])):
        key = (t["name"], t["meleeAtk"], t["rangeAtk"], t["meleeDef"], t["rangeDef"])
        if key in seen:
            continue
        seen.add(key)
        troops_out.append(t)

    seen, tools_out = set(), []
    for t in sorted(tools, key=lambda x: int(x["id"])):
        key = (t["name"], t["side"], tuple(t["effects"]))
        if key in seen:
            continue
        seen.add(key)
        tools_out.append(t)

    # Unit art is a texture atlas (portrait + small weapon/icon frames). Fetch
    # each .json sidecar and crop to the LARGEST frame — the character portrait.
    attach_frames(troops_out + tools_out)

    out = {
        "generated": __import__("datetime").date.today().isoformat(),
        "troops": troops_out,
        "tools":  tools_out,
    }
    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    imgs = sum(1 for x in troops_out + tools_out if x["img"])
    framed = sum(1 for x in troops_out + tools_out if x.get("frame"))
    print(f"Wrote troops-tools.json — {len(troops_out)} troops, {len(tools_out)} tools, "
          f"{imgs}/{len(troops_out)+len(tools_out)} images, {framed} atlas-cropped.", file=sys.stderr)


def fetch_largest_frame(url_webp):
    """Return (frame [x,y,w,h], sheet [W,H]) of the biggest frame, or None."""
    try:
        with urllib.request.urlopen(url_webp[:-5] + ".json", timeout=15) as r:
            a = json.loads(r.read().decode("utf-8"))
        frames = a.get("frames", [])
        if len(frames) <= 1:
            return None
        best = max(frames, key=lambda f: f[2] * f[3])
        size = a.get("size", {})
        return ([best[0], best[1], best[2], best[3]], [size.get("w", 0), size.get("h", 0)])
    except Exception:
        return None


def attach_frames(items):
    import concurrent.futures
    urls = sorted({it["img"] for it in items if it.get("img")})
    print(f"  Fetching {len(urls)} unit atlases…", file=sys.stderr)
    frames = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        for url, res in zip(urls, ex.map(fetch_largest_frame, urls)):
            if res:
                frames[url] = res
    for it in items:
        res = frames.get(it.get("img"))
        if res:
            it["frame"], it["sheet"] = res


if __name__ == "__main__":
    main()
