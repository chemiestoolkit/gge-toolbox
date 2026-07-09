#!/usr/bin/env python3
"""
Rift Raid boss extractor — Maxy's Empire Toolkit.
Pulls the three Rift Raid bosses, their 20 levels and per-stage wall
composition + boss effects, and writes rift-bosses.json.

Run: python3 extract.py
"""
import json, sys, os, urllib.request

# Game data pulled direct from Goodgame Studios by tools/_srcdata/pull.sh
# (invoked from this tool's build.sh) into _srcdata/cache/ — local reads below.
_SRC      = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_srcdata", "cache"))
ITEMS_URL = "file://" + os.path.join(_SRC, "items_latest.json")
LANG_URL  = "file://" + os.path.join(_SRC, "en.json")
CDN       = "https://empire-html5.goodgamestudios.com/default/assets/itemassets/"
OUT       = os.path.join(os.path.dirname(__file__), "rift-bosses.json")

RARITY_NAMES = {"1": "Common", "2": "Rare", "3": "Epic", "4": "Legendary"}


def fetch(url, label):
    print(f"  Downloading {label}…", file=sys.stderr)
    with urllib.request.urlopen(url) as r:
        return r.read().decode("utf-8")


def boss_img(bid):
    """Per-boss portrait (DetailView_RaidBoss_<id>) resolved from the game's DLL asset index."""
    import glob, re
    dll = open(glob.glob(os.path.join(_SRC, "ggs.dll*"))[0], encoding="utf-8", errors="replace").read()
    m = re.search(r"itemassets/[A-Za-z0-9_/]*DetailView_RaidBoss_" + str(bid) + r"--\d+", dll)
    return "https://empire-html5.goodgamestudios.com/default/assets/" + m.group(0) + ".webp" if m else None


def main():
    d    = json.loads(fetch(ITEMS_URL, "items_latest.json"))
    lang = {k.lower(): v for k, v in json.loads(fetch(LANG_URL, "lang/en.json")).items()}

    effects = {str(e["effectID"]): e["name"] for e in d.get("effects", [])}
    units   = {str(u.get("wodID", "")): u for u in d.get("units", [])}

    def L(key, fallback=""):
        return lang.get(key.lower(), fallback)

    def unit_name(uid):
        u = units.get(str(uid), {})
        t = u.get("type", "")
        return L(f"{t}_name", t or f"Unit {uid}")

    def unit_role(uid):
        return units.get(str(uid), {}).get("role", "")

    def _num(v):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return 0

    def parse_units(s):
        """'506+800#505+550' -> [{id, name, role, count, meleeDef, rangeDef}]"""
        out = []
        for pair in str(s or "").split("#"):
            pair = pair.strip()
            if "+" not in pair:
                continue
            uid, cnt = pair.split("+", 1)
            uid = uid.strip()
            u = units.get(uid, {})
            out.append({
                "id": uid,
                "name": unit_name(uid),
                "role": unit_role(uid),
                "count": int(cnt) if cnt.strip().isdigit() else 0,
                "meleeDef": _num(u.get("meleeDefence")),
                "rangeDef": _num(u.get("rangeDefence")),
            })
        return out

    # Structured per-stage combat numbers for the wall-break simulator.
    # Maps the real effect names (via the effects table) to fields the sim uses.
    FX_FIELDS = {
        "raidbosswallbonus":        "wallProt",
        "raidbossgatebonus":        "gateProt",
        "defenseboostfront":        "frontStr",
        "defenseboostflank":        "flankStr",
        "defenseboostyard":         "yardStr",
        "offensiverangemalus":      "atkRangedMalus",
        "offensivemeleemalus":      "atkMeleeMalus",
    }

    def parse_combat_fx(s):
        out = {}
        for pair in str(s or "").split(","):
            pair = pair.strip()
            if "&" not in pair:
                continue
            eid, val = pair.split("&", 1)
            name = effects.get(eid.strip(), "").lower()
            field = FX_FIELDS.get(name)
            if field:
                try:
                    out[field] = out.get(field, 0) + float(val)
                except ValueError:
                    pass
        return out

    def effect_label(eid, val):
        name = effects.get(str(eid), "")
        if not name:
            return f"Effect {eid} ({val})"
        tpl = L(f"equip_effect_description_{name.lower()}")
        if tpl and "{0}" in tpl:
            out = tpl.replace("{0}", str(val))
            # Collapse double signs (template sign + negative value), e.g. "--30%"
            return out.replace("--", "-").replace("+-", "-").replace("-+", "-")
        return f"{name} {val}"

    def parse_effects(s):
        out = []
        for pair in str(s or "").split(","):
            pair = pair.strip()
            if "&" not in pair:
                continue
            eid, val = pair.split("&", 1)
            out.append(effect_label(eid.strip(), val.strip()))
        return out

    def highlight_labels(s):
        """Highlight icon ids -> friendly highlighted-effect names."""
        out = []
        for eid in str(s or "").split(","):
            eid = eid.strip()
            if not eid:
                continue
            name = effects.get(eid, "")
            friendly = L(f"dialog_are_highlightedeffect_name_{name.lower()}") if name else ""
            out.append(friendly or name or f"Effect {eid}")
        return out

    # Index stages by levelID
    stages_by_level = {}
    for s in d.get("raidBossStages", []):
        stages_by_level.setdefault(str(s["raidBossLevelID"]), []).append(s)

    # Index levels by bossID
    levels_by_boss = {}
    for l in d.get("raidBossLevels", []):
        levels_by_boss.setdefault(str(l["raidBossID"]), []).append(l)

    bosses_out = []
    for b in d.get("raidBosses", []):
        bid    = str(b["raidBossID"])
        raw    = b.get("name", "")
        name   = L(f"are_boss_name_{raw.lower()}", raw)
        desc   = L(f"dialog_are_boss_narrativ_short_desc_{raw.lower()}", "")
        rarity = RARITY_NAMES.get(str(b.get("rarity", "")), "")

        levels_out = []
        for l in sorted(levels_by_boss.get(bid, []), key=lambda x: int(x.get("level", 0))):
            lid = str(l["raidBossLevelID"])

            # Reserve pool = boss "health" (sum of reserve unit counts)
            reserve = parse_units(l.get("courtyardReserveUnits", ""))
            reserve_total = sum(u["count"] for u in reserve)

            stages_out = []
            wall_pf = court_pf = 0
            for s in sorted(stages_by_level.get(lid, []), key=lambda x: -int(x.get("health", 0))):
                left  = parse_units(s.get("leftWallUnits", ""))
                front = parse_units(s.get("frontWallUnits", ""))
                right = parse_units(s.get("rightWallUnits", ""))
                wall_total = sum(u["count"] for seg in (left, front, right) for u in seg)
                # Point factors are constant within a level; capture them.
                wall_pf  = int(s.get("wallPointFactor", 0) or 0) or wall_pf
                court_pf = int(s.get("courtyardPointFactor", 0) or 0) or court_pf
                combat = parse_combat_fx(s.get("defenderBattleEffects", ""))
                combat.update(parse_combat_fx(s.get("attackerBattleEffects", "")))
                stages_out.append({
                    "health": int(s.get("health", 0)),
                    "left": left,
                    "front": front,
                    "right": right,
                    "wallTotal": wall_total,
                    "defenderEffects": parse_effects(s.get("defenderBattleEffects", "")),
                    "attackerEffects": parse_effects(s.get("attackerBattleEffects", "")),
                    "highlights": highlight_labels(s.get("HighlightEffectIcon", "")),
                    "combat": combat,
                })

            levels_out.append({
                "level": int(l.get("level", 0)),
                "wallRegenSec": int(l.get("wallRegenerationTime", 0) or 0),
                "courtyardSize": int(l.get("courtyardSize", 0) or 0),
                "courtyardMeleePct": int(l.get("courtyardMeleePercent", 0) or 0),
                "reserveTotal": reserve_total,
                "minPointsForRewards": int(l.get("minPointsForBossRewards", 0) or 0),
                "wallPointFactor": wall_pf,
                "courtyardPointFactor": court_pf,
                "stages": stages_out,
            })

        bosses_out.append({
            "id": bid,
            "name": name,
            "internalName": raw,
            "rarity": rarity,
            "description": desc,
            "img": boss_img(bid),
            "levels": levels_out,
        })

    out = {
        "generated": __import__("datetime").date.today().isoformat(),
        "bosses": bosses_out,
    }
    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print(f"Wrote rift-bosses.json — {len(bosses_out)} bosses.", file=sys.stderr)


if __name__ == "__main__":
    main()
