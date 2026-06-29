#!/usr/bin/env python3
"""Poll gge-tracker for an alliance's joins/leaves and ping a Discord webhook.

Runs from GitHub Actions on a schedule. State (the timestamp of the newest
movement we've already posted) lives in a small JSON file that the workflow
restores/saves via actions/cache — so we never commit anything to main and the
history stays clean. On the very first run (no state) we record the current
high-water mark and post nothing, so we don't dump the whole back-catalogue.

Env:
  DISCORD_ALLIANCE_HOOK  Discord webhook URL (required; set as an Actions secret)
  WATCH_STATE            path to the state file (default: cache/alliance-watch-state.json)
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
HOOK = os.environ.get("DISCORD_ALLIANCE_HOOK", "").strip()

GREEN = 0x4ade80   # join
RED   = 0xf87171   # leave


def api_get(path):
    req = urllib.request.Request(API + path, headers={
        "gge-server": SERVER,
        "User-Agent": "gge-toolbox-alliance-watch/1.0",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


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


def post_discord(embeds):
    # Discord caps embeds at 10 per message — chunk to be safe.
    for i in range(0, len(embeds), 10):
        payload = {"username": "Anti Black Souls", "embeds": embeds[i:i + 10]}
        data = json.dumps(payload).encode("utf-8")
        # Discord sits behind Cloudflare, which 403s the default Python-urllib
        # User-Agent (error 1010) — set an explicit UA or the POST is blocked.
        req = urllib.request.Request(HOOK, data=data,
            headers={"Content-Type": "application/json",
                     "User-Agent": "gge-toolbox-alliance-watch/1.0 (+https://github.com/chemiestoolkit/gge-toolbox)"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                r.read()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            print(f"Discord POST failed {e.code}: {body}", file=sys.stderr)
            raise
        time.sleep(0.4)  # be gentle with the webhook rate limit


def parse_ts(s):
    if not s:
        return datetime.min.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def main():
    if not HOOK:
        print("DISCORD_ALLIANCE_HOOK not set — nothing to do.", file=sys.stderr)
        return 1

    data = api_get(f"updates/alliances/{ALLIANCE_ID}/players")
    updates = data.get("updates", []) or []
    # Oldest → newest so Discord shows them in chronological order.
    updates.sort(key=lambda u: parse_ts(u.get("created_at")))

    state = load_state()
    since = parse_ts(state.get("watermark"))
    first_run = "watermark" not in state

    fresh = [u for u in updates if parse_ts(u.get("created_at")) > since]

    if updates:
        state["watermark"] = updates[-1]["created_at"]

    if first_run:
        save_state(state)
        print(f"First run — baseline set at {state.get('watermark')}, posted nothing.")
        return 0

    if not fresh:
        save_state(state)
        print("No new joins/leaves.")
        return 0

    post_discord([to_embed(u) for u in fresh])
    save_state(state)
    print(f"Posted {len(fresh)} movement(s) to Discord.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
