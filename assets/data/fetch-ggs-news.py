#!/usr/bin/env python3
"""
Refresh the homepage feeds from Goodgame Studios' own channels.

  - GGE news      -> site-feed.json ."news"    (WordPress REST API; "Latest from GGS")
  - Event calendar-> site-feed.json ."events"  (scraped from the News Hub page)

Both are FAIL-SAFE: if a fetch/parse looks wrong, the existing block is kept
untouched (never overwrite good data with junk) and a warning is printed. The
per-block "*Updated" stamps only advance on success, so stale data is visible in
the file itself. The script exits 0 either way so a transient hiccup never blocks
the daily game-data commit.

The manually curated fields (changelog, maxyNotes) are always preserved.
Run by the refresh-data GitHub Action (and `bash tools/refresh-all.sh` locally).
"""
import json, os, re, sys, html, urllib.request
from datetime import datetime, timezone, date

HUB   = "https://communityhub.goodgamestudios.com/wp-json/wp/v2/posts"
CAL   = "https://communityhub.goodgamestudios.com/newshube4k/"
HERE  = os.path.dirname(os.path.abspath(__file__))
SITE  = os.path.join(HERE, "site-feed.json")

GGE_NEWS   = {2718, 2710, 2938, 2945}   # Empire, General, FeaturedEmpire, UpdateNotes
HARD_OTHER = {2720, 2721}               # BigFarm, BitLife
NEWS_MAX   = 8

MON_ABBR = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MON_NAME = ["", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"]

# Known events -> (emoji, icon file in assets/img/event-icons/). Order = display order.
EVENT_META = [
    ("Nomad Invasion",         "🌊", "nomadinvasion.webp"),
    ("Samurai Invasion",       "⚔️", "samuraiinvasion.webp"),
    ("Bloodcrow Invasion",     "🩸", "bloodcrow.webp"),
    ("War of the Realms",      "⚔️", "waroftherealms.webp"),
    ("Berimond Kingdom",       "🏰", "berimond.webp"),
    ("Rift Raid",              "🌀", "riftraid.webp"),
    ("Bladecoast",             "🗡️", "bladecoast.webp"),
    ("Grand Tournament",       "🏆", "grandtournament.webp"),
    ("Beyond the Horizon",     "🌅", "beyondthehorizon.webp"),
    ("Outer Realms",           "🌌", "outerrealms.webp"),
    ("Imperial Patronage",     "👑", "patronage.webp"),
    ("Grand Nobility Contest", "🎖️", "ltpe.webp"),
]
# Page aliases -> canonical name (some events appear under a short label).
ALIASES = {"Berimond": "Berimond Kingdom", "Grand Nobility": "Grand Nobility Contest"}


def clean(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def nice_date(iso):
    try:
        return datetime.fromisoformat(iso.replace("Z", "")).strftime("%-d %b %Y")
    except Exception:
        return (iso or "")[:10]


def fetch_news():
    url = f"{HUB}?per_page=30&_fields=date,title,categories,link"
    req = urllib.request.Request(url, headers={"User-Agent": "gge-toolbox-newsfetch/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        posts = json.load(r)
    news = []
    for p in posts:
        cats = set(p.get("categories", []))
        if (cats & GGE_NEWS) and not (cats & HARD_OTHER):
            news.append({"date": nice_date(p.get("date", "")),
                         "title": clean(p["title"]["rendered"]),
                         "url": p.get("link", "")})
    return news[:NEWS_MAX]


def fetch_calendar(cur, year):
    """Scrape the News Hub events schedule. Returns an events dict or None.

    The calendar is free text inside the page (no table/feed), so we assign each
    date range to the nearest preceding event name, keep only ranges that START
    in the current month, and require >= 8 known events before trusting the parse.
    """
    req = urllib.request.Request(CAL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8", "replace")
    txt = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw)))

    names = []
    for canon, _, _ in EVENT_META:
        for m in re.finditer(re.escape(canon), txt):
            names.append((m.start(), canon))
    for alias, canon in ALIASES.items():
        for m in re.finditer(re.escape(alias), txt):
            names.append((m.start(), canon))
    names.sort()
    if not names:
        return None

    buckets = {}
    for m in re.finditer(r"(\d{1,2})[/.](\d{1,2})(?:\s*[-–]\s*(\d{1,2})[/.](\d{1,2}))?", txt):
        prev = [n for p, n in names if p < m.start()]
        if not prev:
            continue
        d1, m1 = int(m.group(1)), int(m.group(2))
        if m1 != cur:                       # only ranges that start this month
            continue
        d2 = int(m.group(3)) if m.group(3) else None
        m2 = int(m.group(4)) if m.group(4) else None
        buckets.setdefault(prev[-1], set()).add((d1, m1, d2, m2))

    items = []
    for canon, emoji, icon in EVENT_META:
        rs = sorted(buckets.get(canon, []))
        if not rs:
            continue
        same, cross = [], []
        for d1, m1, d2, m2 in rs:
            if d2 is None or m2 in (None, cur):
                same.append(f"{d1:02d}" if d2 is None else f"{d1:02d}–{d2:02d}")
            else:
                cross.append(f"{d1:02d} {MON_ABBR[cur]}–{d2:02d} {MON_ABBR[m2]}")
        parts = ([" · ".join(same) + " " + MON_ABBR[cur]] if same else []) + cross
        items.append({"name": canon, "emoji": emoji, "icon": icon,
                      "dates": " · ".join(parts)})

    if len(items) < 8:                      # safety: refuse a thin/broken parse
        return None
    return {"month": f"{MON_NAME[cur]} {year}",
            "iconBase": "assets/img/event-icons/", "items": items}


def main():
    with open(SITE) as f:
        site = json.load(f)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today = date.today()

    try:
        news = fetch_news()
        if news:
            site["news"], site["newsUpdated"] = news, stamp
            print(f"news: {len(news)} items")
        else:
            print("WARN news: 0 GGE items parsed — keeping existing block")
    except Exception as e:
        print(f"WARN news fetch failed ({e}) — keeping existing block")

    try:
        cal = fetch_calendar(today.month, today.year)
        if cal:
            site["events"], site["eventsUpdated"] = cal, stamp
            print(f"calendar: {len(cal['items'])} events for {cal['month']}")
        else:
            print("WARN calendar: parse below safety threshold — keeping existing block")
    except Exception as e:
        print(f"WARN calendar fetch failed ({e}) — keeping existing block")

    site.setdefault("newsUrl", "https://communityhub.goodgamestudios.com/newshube4k/")
    with open(SITE, "w") as f:
        json.dump(site, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
