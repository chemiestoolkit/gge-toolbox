#!/usr/bin/env python3
"""Watch an alliance on gge-tracker and ping a Discord webhook on activity.

Six feeds, each independent:
  • member arrivals / departures  (📥 / 📤)
  • castle movements — placements, removals, relocations  (🏰 / 💥 / ↗️)
  • player renames  (✏️)
  • shields — new / last 24h / dropped  (🛡️ / ⏳ / 🔓)
  • honour — any rise or fall  (📈 / 📉)
  • might — swings of 4M+  (⬆️ / ⬇️)

Runs from GitHub Actions on a schedule. State (per-feed high-water marks + the
last-seen shield map) lives in a small JSON file that the workflow restores/saves
via actions/cache — so we never commit anything to main and the history stays
clean. On a feed's first run (no state) we record a baseline and post nothing, so
we don't dump the whole back-catalogue. Each feed advances only after Discord has
accepted the post, and a transient upstream error skips just that feed for the
cycle.

Env:
  DISCORD_ALLIANCE_HOOK    Primary Discord webhook URL (required; Actions secret).
  DISCORD_ALLIANCE_HOOK_2  Optional second webhook — the same arrivals/departures
                           feed is mirrored here (e.g. a second Anti Black Souls
                           channel). Best-effort: a dead mirror never blocks the
                           primary or causes duplicate posts. Also an Actions secret.
                           (Either var may hold a comma-separated list of URLs.)
  WATCH_STATE              path to the state file (default: cache/alliance-watch-state.json)
No third-party deps — stdlib urllib only, so there's nothing to pip install.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

# --- what we watch -----------------------------------------------------------
API = "https://api.gge-tracker.com/api/v1/"
SERVER = "AU1"
ALLIANCE_ID = "3069045"          # Black Souls (the big one, merged w/ Renegades)
ALLIANCE_NAME = "Black Souls"

STATE_PATH = os.environ.get("WATCH_STATE",
    os.path.join(os.path.dirname(__file__), "cache", "alliance-watch-state.json"))


def collect_hooks():
    """All configured webhook URLs, primary first. The primary is required and
    gates the watermark; any extras are best-effort mirrors. Each env var may
    also carry a comma-separated list, so you can add more without code changes."""
    hooks = []
    for var in ("DISCORD_ALLIANCE_HOOK", "DISCORD_ALLIANCE_HOOK_2"):
        for url in os.environ.get(var, "").replace("\n", ",").split(","):
            url = url.strip()
            if url and url not in hooks:
                hooks.append(url)
    return hooks

GREEN  = 0x4ade80   # join
RED    = 0xf87171   # leave
BLUE   = 0x60a5fa   # castle movement
PURPLE = 0xc084fc   # rename
GOLD   = 0xfbbf24   # shield up
ORANGE = 0xf59e0b   # shield ending within 24h

# gge-tracker passes the game's own areaType straight through, so these ids are
# the client's AREA_TYPE_* enum (ggs.dll) and the names are the English lang
# bundle's. Verified 2026-08-16 against a live sighting: Noob on Crack dropped a
# Royal tower and the feed reported 23 = AREA_TYPE_KINGS_TOWER.
# Capital / Metropolis / Royal tower used to be rotated among 3, 22 and 23, and
# 26 was labelled Kingdom castle when that's 12 — 26 is a Monument.
CASTLE_TYPES = {
    1:  "Main castle",       # AREA_TYPE_CASTLE
    3:  "Capital",           # AREA_TYPE_CAPITAL
    4:  "Outpost",           # AREA_TYPE_OUTPOST
    12: "Kingdom castle",    # AREA_TYPE_KINGDOM_CASTLE
    22: "Metropolis",        # AREA_TYPE_METROPOL
    23: "Royal tower",       # AREA_TYPE_KINGS_TOWER
    26: "Monument",          # AREA_TYPE_MONUMENT
    28: "Laboratory",        # AREA_TYPE_LABORATORY
}


def castle_name(t):
    return CASTLE_TYPES.get(t, f"castle (type {t})")

# Cloudflare/origin transient statuses — retry these, never hard-fail on them.
TRANSIENT_CODES = {429, 500, 502, 503, 504, 520, 521, 522, 523, 524}


class TransientError(Exception):
    """Upstream is temporarily unreachable — skip this cycle, catch up next run."""


def api_get(path, retries=4):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(API + path, headers={
                "gge-server": SERVER,
                "User-Agent": "gge-toolbox-alliance-watch/1.0",
            })
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in TRANSIENT_CODES:
                raise                       # genuine 4xx (e.g. 404) — surface it
        except (urllib.error.URLError, TimeoutError) as e:
            last = e                        # DNS/connection/timeout — always transient
        wait = 2 ** attempt
        print(f"api_get {path}: attempt {attempt + 1}/{retries} failed ({last}) — retry in {wait}s",
              file=sys.stderr)
        time.sleep(wait)
    raise TransientError(f"gge-tracker unreachable after {retries} tries: {last}")


def load_state():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def fmt_might(v):
    try:
        n = float(v)
    except (TypeError, ValueError):
        return "?"
    if n >= 1e9:
        return f"{n / 1e9:.2f}B"
    if n >= 1e6:
        return f"{n / 1e6:.1f}M"
    if n >= 1e3:
        return f"{n / 1e3:.0f}K"
    return str(int(n))


def to_embed(u):
    """One Discord embed per movement. Green = joined us, red = left us."""
    left = str(u.get("old_alliance_id")) == ALLIANCE_ID
    name = u.get("player_name") or ("#" + str(u.get("player_id")))
    might = fmt_might(u.get("might_current"))
    lvl = u.get("level")
    leg = u.get("legendary_level")
    lvl_str = f"{lvl}" + (f" / L{leg}" if leg else "")
    if left:
        dest = u.get("new_alliance_name") or "no alliance"
        title = f"📤 {name} left {ALLIANCE_NAME}"
        desc = f"→ joined **{dest}**"
        color = RED
    else:
        src = u.get("old_alliance_name") or "no alliance"
        title = f"📥 {name} joined {ALLIANCE_NAME}"
        desc = f"← from **{src}**"
        color = GREEN
    return {
        "title": title,
        "description": desc,
        "color": color,
        "fields": [
            {"name": "Might", "value": might, "inline": True},
            {"name": "Level", "value": lvl_str, "inline": True},
        ],
        "timestamp": u.get("created_at"),
        "footer": {"text": "gge-tracker • " + SERVER},
    }


def post_discord(embeds, hook):
    """Post embeds to one webhook in chunks of 10. Returns True if everything
    posted, False if we gave up on a transient/dead-webhook error (the caller
    decides what that means for the watermark)."""
    for i in range(0, len(embeds), 10):
        payload = {"username": "Anti Black Souls", "embeds": embeds[i:i + 10]}
        data = json.dumps(payload).encode("utf-8")
        for attempt in range(4):
            # Discord sits behind Cloudflare, which 403s the default Python-urllib
            # User-Agent (error 1010) — set an explicit UA or the POST is blocked.
            req = urllib.request.Request(hook, data=data,
                headers={"Content-Type": "application/json",
                         "User-Agent": "gge-toolbox-alliance-watch/1.0 (+https://github.com/chemiestoolkit/gge-toolbox)"},
                method="POST")
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    r.read()
                break                                   # chunk posted
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = float(e.headers.get("Retry-After", 2) or 2)
                elif e.code in TRANSIENT_CODES:
                    wait = 2 ** attempt
                else:                                   # 400/401/404 — bad payload or dead webhook
                    body = e.read().decode("utf-8", "replace")[:300]
                    print(f"Discord POST hard error {e.code}: {body}", file=sys.stderr)
                    return False
                print(f"Discord POST {e.code} — retry in {wait:.0f}s", file=sys.stderr)
                time.sleep(min(wait, 30))
            except (urllib.error.URLError, TimeoutError) as e:
                print(f"Discord POST network error ({e}) — retry", file=sys.stderr)
                time.sleep(2 ** attempt)
        else:
            print("Discord POST: gave up after retries.", file=sys.stderr)
            return False
        time.sleep(0.4)  # be gentle with the webhook rate limit
    return True


def parse_ts(s):
    if not s:
        return datetime.min.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# --- movement / rename embeds -----------------------------------------------
def to_movement_embed(r):
    name = r.get("player_name") or ("#" + str(r.get("player_id")))
    ct = castle_name(r.get("castle_type"))
    mt = str(r.get("movement_type", "")).lower()
    ox, oy = r.get("position_x_old"), r.get("position_y_old")
    nx, ny = r.get("position_x_new"), r.get("position_y_new")
    old = f"{ox}:{oy}" if ox is not None else "?"
    new = f"{nx}:{ny}" if nx is not None else "?"
    a = "an" if ct[:1].lower() in "aeiou" else "a"      # "an Outpost", not "a Outpost"
    if mt in ("relocate", "relocation", "move"):
        title, desc, color = f"↗️ {name} relocated {a} {ct}", f"{old} → **{new}**", BLUE
    elif mt in ("remove", "delete"):
        title, desc, color = f"💥 {name} removed {a} {ct}", f"was at {old}", RED
    elif mt in ("add", "create", "place"):
        title, desc, color = f"🏰 {name} placed {a} {ct}", f"at **{new}**", GREEN
    else:
        title, desc, color = f"🏰 {name} — {ct} ({mt})", f"{old} → {new}", BLUE
    return {"title": title, "description": desc, "color": color,
            "fields": [{"name": "Might", "value": fmt_might(r.get("player_might")), "inline": True}]}


def to_rename_embed(r):
    old = r.get("old_player_name") or "?"
    new = r.get("new_player_name") or r.get("player_name") or "?"
    return {"title": f"✏️ Rename in {ALLIANCE_NAME}",
            "description": f"**{old}** → **{new}**", "color": PURPLE,
            "fields": [{"name": "Might", "value": fmt_might(r.get("player_might")), "inline": True}]}


def _rel(until):
    try:
        return f"<t:{int(parse_ts(until).timestamp())}:R>"        # Discord relative time
    except Exception:
        return str(until)


def shield_up_embed(p, until):
    name = p.get("player_name") or ("#" + str(p.get("player_id")))
    return {"title": f"🛡️ {name} went shielded",
            "description": f"Attackable again {_rel(until)}", "color": GOLD,
            "fields": [{"name": "Might", "value": fmt_might(p.get("might_current")), "inline": True}]}


def shield_expiring_embed(p, until):
    name = p.get("player_name") or ("#" + str(p.get("player_id")))
    return {"title": f"⏳ {name}'s shield ends within 24h",
            "description": f"Attackable {_rel(until)} — line up the hit.", "color": ORANGE,
            "fields": [{"name": "Might", "value": fmt_might(p.get("might_current")), "inline": True}]}


def shield_dropped_embed(name, might=None):
    fields = [{"name": "Might", "value": fmt_might(might), "inline": True}] if might else []
    return {"title": f"🔓 {name}'s shield dropped",
            "description": "Now attackable.", "color": GREEN, "fields": fields}


# --- feeds: each returns (embeds, commit_fn). commit_fn advances that feed's
#     slice of state, and is only called once Discord has accepted the post. A
#     feed that hits a transient upstream error just raises and is skipped this
#     cycle. First run for a feed records a baseline and posts nothing. ---------
def _watermarked(state, key, rows, ts_of, embed_of):
    rows.sort(key=lambda r: parse_ts(ts_of(r)))
    prev = state.get(key)
    newest = ts_of(rows[-1]) if rows else prev
    # A watermark must only ever move forward. These feeds are filtered by the
    # player's *current* alliance, so when someone leaves, their rows leave the
    # feed with them — and the newest row we can still see drops back to an
    # older one. Letting that rewind the watermark means everything above it
    # re-posts the moment they rejoin and their history reappears.
    if prev and newest and parse_ts(newest) < parse_ts(prev):
        newest = prev

    def commit(st):
        if newest:
            st[key] = newest

    if key not in state:                        # first run — baseline only
        return [], commit
    since = parse_ts(state.get(key))
    fresh = [r for r in rows if parse_ts(ts_of(r)) > since]
    return [embed_of(r) for r in fresh], commit


def feed_members(state):
    data = api_get(f"updates/alliances/{ALLIANCE_ID}/players")
    return _watermarked(state, "watermark", data.get("updates", []) or [],
                        lambda u: u.get("created_at"), to_embed)


def feed_movements(state):
    since = parse_ts(state.get("mv_watermark"))
    rows = []
    for page in range(1, 6):                    # a few pages of headroom per hour
        data = api_get(f"server/movements?allianceId={ALLIANCE_ID}&page={page}")
        chunk = data.get("movements", []) or []
        if not chunk:
            break
        rows += chunk
        if len(chunk) < 10 or min(parse_ts(r.get("created_at")) for r in chunk) <= since:
            break
    return _watermarked(state, "mv_watermark", rows,
                        lambda r: r.get("created_at"), to_movement_embed)


RENAME_SEEN_CAP = 400            # ~2 years of this feed; state stays a few KB


def _rename_key(r):
    """Stable identity for one rename row — the feed gives us no id of its own."""
    return "|".join(str(r.get(k) or "")
                    for k in ("date", "old_player_name", "new_player_name"))


def feed_renames(state):
    """Renames of our members — but only ones that happen *while* they're ours.

    The upstream feed's `alliance_name` is the player's alliance right now, not
    the one they were in when they renamed. So the day someone joins us, their
    entire rename history retroactively lands in our slice of the feed at once —
    which is why a serial rejoiner (Krakatoa, whose chain runs BiggieOFC →
    ZARVYX → ANDRE THE GIANT → Krakatoa) used to re-announce every old name.

    A timestamp watermark can't fix that on its own, because those rows are
    genuinely new *to us* each time. So we remember rows by identity instead,
    and we mark the whole global feed seen rather than just our slice: a rename
    that happened while the player was somewhere else is already on the list by
    the time they walk in the door, and stays quiet. Only a rename we've never
    seen before, on someone already flying our tag, pings.
    """
    data = api_get("server/renames?page=1")      # global feed — sparse; one page
    rows = data.get("renames", []) or []
    seen = set(state.get("rn_seen") or [])
    first = "rn_seen" not in state               # first run — baseline only

    ours = [r for r in rows if str(r.get("alliance_name")) == ALLIANCE_NAME]
    ours.sort(key=lambda r: parse_ts(r.get("date")))
    fresh = [] if first else [r for r in ours if _rename_key(r) not in seen]

    # Newest first, so the cap prunes from the far end of history. The feed
    # turns over a handful of rows a month, so a cap this far above one page
    # can never evict something still visible upstream.
    keys = [_rename_key(r) for r in sorted(rows, key=lambda r: parse_ts(r.get("date")),
                                           reverse=True)]
    kept = keys + [k for k in (state.get("rn_seen") or []) if k not in set(keys)]

    def commit(st):
        st["rn_seen"] = kept[:RENAME_SEEN_CAP]
        st.pop("rn_watermark", None)             # superseded by rn_seen

    return [to_rename_embed(r) for r in fresh], commit


# Shields, honour and might all diff the same roster — fetch it once per run.
_ROSTER = {}


def get_roster():
    if "v" in _ROSTER:
        if _ROSTER["v"] is None:
            raise TransientError("roster unavailable this cycle")
        return _ROSTER["v"]
    try:
        data = api_get(f"alliances/id/{ALLIANCE_ID}")
    except TransientError:
        _ROSTER["v"] = None                 # remember the miss so sibling feeds skip too
        raise
    _ROSTER["v"] = data.get("players", data.get("members", [])) or []
    return _ROSTER["v"]


def feed_shields(state):
    # No shield event feed — poll the roster and diff peace_disabled_at ourselves.
    # We only ever fire on three transitions, each at most once per shield:
    #   • new shield       (member becomes protected)
    #   • last 24h         (protection now ends within a day — line up the hit)
    #   • shield dropped   (protection gone — attackable, reported next poll = ASAP)
    # Extends / top-ups while >24h out are deliberately silent (that was the spam).
    roster = get_roster()
    now = datetime.now(timezone.utc)
    by_id = {str(p.get("player_id")): p for p in roster}

    def hours_left(v):
        try:
            return (parse_ts(v) - now).total_seconds() / 3600.0
        except Exception:
            return -1

    current = {str(p.get("player_id")): p.get("peace_disabled_at")
               for p in roster if hours_left(p.get("peace_disabled_at")) > 0}

    raw_prev = state.get("shields")
    first = raw_prev is None
    # Normalise (older builds stored a bare timestamp string per player).
    prev = {}
    for pid, v in (raw_prev or {}).items():
        prev[pid] = v if isinstance(v, dict) else {"until": v, "warned24": False, "name": None}

    embeds, new_shields = [], {}
    for pid, until in current.items():
        p = by_id[pid]
        hl = hours_left(until)
        pe = prev.get(pid)
        if pe is None:                                  # ── new shield ──
            if not first:
                embeds.append(shield_up_embed(p, until))
            warned = hl <= 24                           # already <24h? count it warned
        else:
            warned = pe.get("warned24", False)
            if until != pe.get("until") and hl > 24:    # extended well out → re-arm
                warned = False
            if hl <= 24 and not warned and not first:   # ── entered last 24h ──
                embeds.append(shield_expiring_embed(p, until))
                warned = True
        new_shields[pid] = {"until": until, "warned24": warned,
                            "name": p.get("player_name") or ("#" + pid)}

    if not first:                                       # ── shield dropped ──
        for pid, pe in prev.items():
            if pid not in current:
                nm = (by_id.get(pid, {}).get("player_name")) or pe.get("name") or ("#" + pid)
                embeds.append(shield_dropped_embed(nm, by_id.get(pid, {}).get("might_current")))

    def commit(st):
        st["shields"] = new_shields

    return embeds, commit


# --- honour & might: roster stat diffs, poll-to-poll ------------------------
MIGHT_THRESHOLD = 4_000_000            # only flag might swings this big or bigger


def _to_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def honour_embed(p, old, new):
    name = p.get("player_name") or ("#" + str(p.get("player_id")))
    d = new - old
    arrow, color = ("📈", GREEN) if d > 0 else ("📉", RED)
    return {"title": f"{arrow} {name}'s honour {'rose' if d > 0 else 'fell'} {abs(d):,}",
            "description": f"{old:,} → **{new:,}**", "color": color}


def might_embed(p, old, new):
    name = p.get("player_name") or ("#" + str(p.get("player_id")))
    d = new - old
    arrow, color = ("⬆️", GREEN) if d > 0 else ("⬇️", RED)
    verb = "gained" if d > 0 else "lost"
    return {"title": f"{arrow} {name} {verb} {fmt_might(abs(d))} might",
            "description": f"{fmt_might(old)} → **{fmt_might(new)}**", "color": color}


def _roster_stat_feed(state, key, field, embed_of, changed):
    """Shared skeleton: baseline the field per player on first run, then diff
    each poll. `changed(old, new)` decides whether a delta is worth an alert."""
    roster = get_roster()
    by_id = {str(p.get("player_id")): p for p in roster}
    current = {pid: _to_int(p.get(field)) for pid, p in by_id.items()
               if _to_int(p.get(field)) is not None}
    prev = state.get(key)

    def commit(st):
        st[key] = current

    if prev is None:                    # first run — baseline only
        return [], commit
    embeds = []
    for pid, new in current.items():
        old = prev.get(pid)
        if old is not None and changed(old, new):
            embeds.append(embed_of(by_id[pid], old, new))
    return embeds, commit


def feed_honour(state):
    # Honour barely moves on a quiet server, so any change is worth surfacing.
    return _roster_stat_feed(state, "honour", "honor", honour_embed,
                             lambda old, new: old != new)


def feed_might(state):
    # Big might swings = a mass recruit (up) or a heavy loss / getting hit (down).
    return _roster_stat_feed(state, "might", "might_current", might_embed,
                             lambda old, new: abs(new - old) >= MIGHT_THRESHOLD)


FEEDS = [("members", feed_members), ("castle movements", feed_movements),
         ("renames", feed_renames), ("shields", feed_shields),
         ("honour", feed_honour), ("might", feed_might)]


def main():
    hooks = collect_hooks()
    if not hooks:
        # Misconfig, but don't fail the job (and email) every hour over it.
        print("No DISCORD_ALLIANCE_HOOK configured — nothing to do.", file=sys.stderr)
        return 0

    state = load_state()
    embeds, commits = [], []
    for label, feed in FEEDS:
        try:
            e, commit = feed(state)
        except TransientError as ex:
            print(f"{label}: transient upstream ({ex}) — skip this cycle", file=sys.stderr)
            continue                            # don't advance this feed; retry next run
        except urllib.error.HTTPError as ex:
            print(f"{label}: HTTP {ex.code} — skip this feed", file=sys.stderr)
            continue
        embeds += e
        commits.append(commit)

    if not embeds:
        # Nothing to post; still save baselines / no-op watermarks that polled OK.
        for c in commits:
            c(state)
        save_state(state)
        print("No new events.")
        return 0

    # Oldest → newest across all feeds so Discord reads chronologically.
    # The primary hook gates the state save; extras are best-effort mirrors.
    primary_ok = post_discord(embeds, hooks[0])
    for mirror in hooks[1:]:
        if not post_discord(embeds, mirror):
            print("Mirror webhook post failed (best-effort) — continuing.", file=sys.stderr)

    if primary_ok:
        for c in commits:
            c(state)
        save_state(state)
        print(f"Posted {len(embeds)} event(s) to {len(hooks)} webhook(s).")
    else:
        print("Primary Discord post failed — keeping state, will retry next run.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
