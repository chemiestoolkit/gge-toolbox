#!/usr/bin/env python3
"""Flag newly-landed game content so the site's written pages can catch up.

The daily refresh keeps *data* current on its own, but derived pages (guides,
overview copy) still need a human/AI pass. This compares the freshly-pulled
cache against a small stored fingerprint and posts a Discord note listing what
changed — so an update never sits unnoticed.

Tracked signals are the ones we know are pending for the 29 Jul 2026 Rift
rework, plus generic counters that catch anything else GGS ships.

Usage: content-watch.py <cache-dir> <state.json>   (needs $CONTENT_WATCH_HOOK)
Exit code is always 0 — a watcher must never fail the refresh job.
"""
import json
import os
import sys
import urllib.error
import urllib.request

CACHE, STATE = sys.argv[1], sys.argv[2]
HOOK = os.environ.get("CONTENT_WATCH_HOOK", "").strip()


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


items = load(f"{CACHE}/items_latest.json")
lang = load(f"{CACHE}/en.json")
if not items or not lang:
    print("watch: cache unreadable — skipping")
    sys.exit(0)

lc = {k.lower(): v for k, v in lang.items()}
sources = ""
try:
    sources = open(f"{CACHE}/SOURCES.txt", encoding="utf-8").read()
except OSError:
    pass
version = next((ln.split("=", 1)[1].strip() for ln in sources.splitlines()
                if ln.startswith("empire_items_version=")), "?")


def rows(table):
    v = items.get(table)
    return len(v) if isinstance(v, list) else 0


def arme_quests():
    return sum(1 for q in items.get("allianceQuests", [])
               if "ARME" in json.dumps(q))


def rift_shop_packages():
    keys = ("costRiftCoin", "costLegendaryRiftCoin", "costRiftShard", "costImperialDucat")
    return sum(1 for p in items.get("packages", []) if any(k in p for k in keys))


def unnamed_rift_gear():
    """Rift set pieces shipped without an in-game name — i.e. unreleased."""
    return sum(1 for e in items.get("equipments", [])
               if "ARE set" in str(e.get("comment1", ""))
               and not lc.get(f"equipment_unique_{e.get('equipmentID')}"))


# label -> (value, "note shown when it changes")
now = {
    "items version": (version, "new game build"),
    "alliance buffs": (rows("allianceBuffs"), "**Alliance Combat Boosters** — the booster table filled in"),
    "ARME quests": (arme_quests(), "Tournament quest pool changed (1,500+ expected)"),
    "rift shop packages": (rift_shop_packages(), "event shop stock changed"),
    "raid bosses": (rows("raidBosses"), "boss roster changed"),
    "unnamed rift gear": (unnamed_rift_gear(), "rift gear names shipped — check 'name pending' rows"),
    "equipment": (rows("equipments"), "new equipment (watch for cross-event boss loot)"),
    "loot boxes": (rows("lootBoxes"), "loot box list changed"),
}

prev = load(STATE, {}) or {}
changes = []
for label, (val, note) in now.items():
    old = prev.get(label)
    if old is not None and old != val:
        changes.append(f"• **{label}**: `{old}` → `{val}` — {note}")

# Persist regardless, so a change is reported once rather than every run.
with open(STATE, "w", encoding="utf-8") as fh:
    json.dump({k: v[0] for k, v in now.items()}, fh, indent=1, sort_keys=True)
    fh.write("\n")

if not prev:
    print("watch: baseline written, nothing to compare yet")
    sys.exit(0)
if not changes:
    print("watch: no tracked content changes")
    sys.exit(0)

body = "\n".join(changes)
print("watch: changes detected\n" + body)

if not HOOK:
    print("watch: no CONTENT_WATCH_HOOK set — not posting")
    sys.exit(0)

payload = {
    "username": "Toolkit Content Watch",
    "embeds": [{
        "title": "🆕 New game content detected",
        "description": body + "\n\nThe data files already updated themselves — "
                              "the guides/overviews may need a written pass.",
        "color": 0xD9B25A,
        "footer": {"text": f"Maxy's Empire Toolkit · items v{version}"},
    }],
}
req = urllib.request.Request(
    HOOK,
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        print(f"watch: posted ({r.status})")
except urllib.error.HTTPError as e:
    print(f"watch: post failed HTTP {e.code}")
except Exception as e:  # never break the refresh job
    print(f"watch: post failed ({e})")
