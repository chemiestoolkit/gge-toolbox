#!/usr/bin/env python3
"""
Berimond gallantry titles — Maxy's Empire Toolkit.

The Battle for Berimond has its own title system, separate from glory. The
client calls it BRAVERY_TITLE, the item table calls it `FACTION`, and the game
shows it to you as "Gallantry titles". This pulls the whole ladder out of
Goodgame's own tables:

  titles        -> every row with type FACTION. `previousTitleID` chains them,
                   which is the only reliable order: the Berimond rework
                   inserted ids 118-126 into the middle and the end of a ladder
                   that used to run 100-117, so sorting by id gives the wrong
                   sequence. Each row carries either a `threshold` (gallantry
                   points) or a `topX` (a position on the live board), a
                   `decay` (percent of your points lost per day), a
                   `mightValue`, and an `effects` string.
  effects       -> the effect ids inside that string, resolved to the game's
                   own wording where the language bundle has it.
  units         -> effect 46 is `enableUnits`, whose value is a unit wodID
                   rather than a percentage, so those two titles are read as
                   "this unit can be recruited".

Title names come from the language bundle as `playerTitle_<id>`, and the page's
wording (header, "gallantry points required", the daily-loss line, the 12-hour
refresh note) is taken from the game's own `dialog_factionTitles_*` strings so
the tool says what the game says.

Game data pulled direct from Goodgame by _srcdata/pull.sh.
"""
import json, os, re, datetime

_SRC  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_srcdata", "cache"))
ITEMS = os.path.join(_SRC, "items_latest.json")
LANG  = os.path.join(_SRC, "en.json")
OUT   = os.path.join(os.path.dirname(__file__), "berimond-titles.json")

TITLE_TYPE = "FACTION"
ENABLE_UNITS_EFFECT = "46"

# The language bundle labels an effect under several prefixes and they are not
# equally trustworthy: `equip_name_effect_*` and `gem_effect_name_gem*` hold
# *item* names (lootBonus resolves to "the Marauder"), so they are left out.
# Descriptions come first because they carry the {0} value placeholder.
LABEL_PATTERNS = [
    "effect_description_{n}",
    "equip_effect_description_{n}",
    "equip_effect_description_short_{n}",
    "ci_effect_{n}",
    "effect_name_{n}",
]

# The game's own wording, so the page doesn't paraphrase it.
LANG_KEYS = {
    "header":        "dialog_factionTitles_header",
    "info":          "dialog_factionTitles_info",
    "pointsNeeded":  "dialog_factionTitles_pointsNeeded",
    "dailyLoss":     "dialog_factionTitles_dailyLoss",
    "yourRank":      "dialog_factionTitles_yourRank",
    "refreshIn":     "dialog_factionTitles_refreshIn_1",
    "refreshNote":   "dialog_factionTitles_refreshIn_2",
    "mightHeader":   "dialog_gloryTitles_mightCounter_header",
    "eventName":     "event_title_3",
    "systemPlural":  "nobilityTitles_plural",
}

# The four live boards the game splits the faction highscore into. LT 30 is
# HighscoreConst.FACTION_TOURNAMENT; the LIDs and their names are the client's.
BOARDS = [
    {"lid": 1, "key": "dialog_factionhighscore_blueList"},
    {"lid": 2, "key": "dialog_factionhighscore_redList"},
    {"lid": 3, "key": "dialog_factionhighscore_blueList_legendary"},
    {"lid": 4, "key": "dialog_factionhighscore_redList_legendary"},
]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def humanise(name):
    """Last resort for an effect the language bundle ships no string for."""
    s = re.sub(r"(?<!^)(?=[A-Z])", " ", name).replace("_", " ")
    return s[0].upper() + s[1:]


def main():
    items = load(ITEMS)
    root = items.get("dataItems", items)
    lang = load(LANG)

    effects = {str(e["effectID"]): e for e in root["effects"]}
    units = {str(u["wodID"]): u for u in root["units"]}

    def unit_name(wid):
        u = units.get(str(wid))
        if not u:
            return "unit " + str(wid)
        return lang.get(u["type"] + "_name", u["type"])

    def effect_label(eid):
        """(label, derived) — derived means we built it from the internal name."""
        e = effects.get(str(eid))
        if not e:
            return "effect " + str(eid), True
        name = e["name"]
        for pattern in LABEL_PATTERNS:
            text = lang.get(pattern.format(n=name))
            if text:
                return text, False
        return humanise(name), True

    def parse_effects(blob):
        out = []
        for eid, value in re.findall(r"(\d+)&([0-9.]+)", str(blob or "")):
            label, derived = effect_label(eid)
            number = float(value)
            shown = int(number) if number == int(number) else number
            row = {"id": int(eid), "value": number, "label": label}
            if eid == ENABLE_UNITS_EFFECT:
                # The value is a unit wodID, not an amount.
                row["unit"] = unit_name(value.split(".")[0])
                row["text"] = label.replace("{0}", row["unit"])
            elif "{0}" in label:
                row["text"] = label.replace("{0}", "{:,}".format(shown))
            else:
                # The language bundle ships no sentence for this one, so the
                # value is shown on its own rather than guessed into a unit.
                row["text"] = label
                row["bare"] = shown
            if derived:
                row["derived"] = True
            out.append(row)
        return out

    rows = {str(t["titleID"]): t for t in root["titles"] if t.get("type") == TITLE_TYPE}
    if not rows:
        raise SystemExit("no " + TITLE_TYPE + " titles in the item table")

    # Walk `previousTitleID` from the one row that has none. Sorting by id would
    # put the reworked 118-126 in the wrong place entirely.
    nxt = {str(t["previousTitleID"]): tid for tid, t in rows.items() if t.get("previousTitleID")}
    roots = [tid for tid, t in rows.items() if not t.get("previousTitleID")]
    if len(roots) != 1:
        raise SystemExit("expected one ladder root, found " + str(roots))
    order, cur = [], roots[0]
    while cur is not None:
        order.append(cur)
        cur = nxt.get(cur)
    if len(order) != len(rows):
        raise SystemExit("ladder chain covers %d of %d titles" % (len(order), len(rows)))

    titles = []
    for step, tid in enumerate(order, 1):
        t = rows[tid]
        threshold = t.get("threshold")
        top_x = t.get("topX")
        titles.append({
            "step": step,
            "id": int(tid),
            "name": lang.get("playerTitle_" + tid, "Title " + tid),
            "display": t.get("displayType") or "prefix",
            "points": int(threshold) if threshold is not None else None,
            "topX": int(top_x) if top_x is not None else None,
            "decayPct": int(t.get("decay") or 0),
            "might": int(t.get("mightValue") or 0),
            "effects": parse_effects(t.get("effects")),
        })

    boards = [{"lid": b["lid"], "name": lang.get(b["key"], "List " + str(b["lid"]))} for b in BOARDS]

    out = {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "itemsVersion": items.get("version") or items.get("Version") or None,
        "listType": 30,              # HighscoreConst.FACTION_TOURNAMENT
        "boards": boards,
        "labels": {k: lang.get(v, "") for k, v in LANG_KEYS.items()},
        "titles": titles,
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, separators=(",", ":"))
        f.write("\n")

    ranked = [t for t in titles if t["topX"] is not None]
    print("berimond-titles.json: %d titles, %d by points up to %s, %d by position (top %s), top title '%s'" % (
        len(titles),
        len(titles) - len(ranked),
        "{:,}".format(max(t["points"] for t in titles if t["points"] is not None)),
        len(ranked),
        "/".join(str(t["topX"]) for t in ranked),
        titles[-1]["name"],
    ))


if __name__ == "__main__":
    main()
