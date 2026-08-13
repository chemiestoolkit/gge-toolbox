#!/usr/bin/env python3
"""One-off: backfill the What's New history by diffing older game-data versions.

Reuses build.py's category/name/image resolution. Reads items_v<ver>.json files
from a directory (default /tmp) and writes the last several updates into
whats-new.json so the page has real history to cycle through. Run once; the
daily build.py takes over for future versions.

Usage: backfill.py [items-dir]
"""
import json
import os
import sys
from datetime import datetime, timezone

SRC_DIR = sys.argv[1] if len(sys.argv) > 1 else "/tmp"

# build.py parses sys.argv[1] as the repo root at import — hide our args first.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_argv, sys.argv = sys.argv, [sys.argv[0]]
import build  # noqa: E402  (loads current lang / overviews / dll for enrichment)
sys.argv = _argv
HERE = os.path.dirname(os.path.abspath(__file__))

# oldest → newest. First entry is only a baseline (no update emitted for it).
# Dates are the GGS changelog dates where known, best-effort otherwise.
VERSIONS = [
    ("774.01", "2026-06-11"),
    ("775.01", "2026-06-16"),
    ("776.01", "2026-06-23"),
    ("776.06", "2026-07-02"),
    ("778.01", "2026-07-09"),
    ("780.01", "2026-07-17"),
    ("781.02", "2026-07-29"),
    ("782.06", "2026-08-13"),
]

ID_TABLES = {"equipments": "equipmentID", "buildings": "wodID",
             "constructionItems": "constructionItemID", "units": "wodID",
             "gachaEvents": "gachaID", "worldmapskins": "worldmapskinID",
             "gems": "gemID", "equipment_sets": "ID"}


def load(ver):
    path = os.path.join(SRC_DIR, f"items_{ver}.json")
    return json.load(open(path, encoding="utf-8"))


def ids_of(itemsobj):
    return {t: [str(r.get(k)) for r in itemsobj.get(t, [])] for t, k in ID_TABLES.items()}


updates = []
prev_obj = load(VERSIONS[0][0])
for ver, date in VERSIONS[1:]:
    cur_obj = load(ver)
    groups = build.build_groups(ids_of(prev_obj), src=cur_obj)
    if groups:
        head, total = build.headline(groups)
        summary = ", ".join(f"{len(g['items'])} {g['category'].lower()}" for g in groups)
        updates.append({"version": ver, "date": date, "headline": head,
                        "count": total, "summary": summary, "groups": groups})
    prev_obj = cur_obj

updates.sort(key=lambda u: u["version"], reverse=True)   # newest first
updates = updates[:6]

out = os.path.join(HERE, "whats-new.json")
feed = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "version": VERSIONS[-1][0], "updates": updates}
json.dump(feed, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("backfilled", len(updates), "updates:")
for u in updates:
    print(f"  v{u['version']} ({u['date']}) — {u['headline']} · {u['count']} items · {u['summary']}")
