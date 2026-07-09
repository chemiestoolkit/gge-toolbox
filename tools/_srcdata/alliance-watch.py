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


def post_discord(embeds):
    """Post embeds in chunks of 10. Returns True if everything posted, False if we
    gave up on a transient/dead-webhook error (caller then keeps the watermark
    unsaved so we retry next run instead of failing the job)."""
    for i in range(0, len(embeds), 10):
        payload = {"username": "Anti Black Souls", "embeds": embeds[i:i + 10]}
        data = json.dumps(payload).encode("utf-8")
        for attempt in range(4):
            # Discord sits behind Cloudflare, which 403s the default Python-urllib
            # User-Agent (error 1010) — set an explicit UA or the POST is blocked.
            req = urllib.request.Request(HOOK, data=data,
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


def main():
    if not HOOK:
        # Misconfig, but don't fail the job (and email) every hour over it.
        print("DISCORD_ALLIANCE_HOOK not set — nothing to do.", file=sys.stderr)
        return 0

    try:
        data = api_get(f"updates/alliances/{ALLIANCE_ID}/players")
    except TransientError as e:
        print(f"Skipping this cycle — {e}", file=sys.stderr)
        return 0                            # transient upstream: no crash, no email

    updates = data.get("updates", []) or []
    # Oldest → newest so Discord shows them in chronological order.
    updates.sort(key=lambda u: parse_ts(u.get("created_at")))

    state = load_state()
    since = parse_ts(state.get("watermark"))
    first_run = "watermark" not in state
    fresh = [u for u in updates if parse_ts(u.get("created_at")) > since]

    if first_run:
        if updates:
            state["watermark"] = updates[-1]["created_at"]
        save_state(state)
        print(f"First run — baseline set at {state.get('watermark')}, posted nothing.")
        return 0

    if not fresh:
        if updates:
            state["watermark"] = updates[-1]["created_at"]
        save_state(state)
        print("No new joins/leaves.")
        return 0

    # Only advance the watermark once Discord has actually accepted the posts.
    if post_discord([to_embed(u) for u in fresh]):
        state["watermark"] = updates[-1]["created_at"]
        save_state(state)
        print(f"Posted {len(fresh)} movement(s) to Discord.")
    else:
        print("Discord post failed — keeping watermark, will retry next run.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
