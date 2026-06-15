#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Pull canonical game data DIRECTLY from Goodgame Studios' own public servers.
# No third-party cache is involved. Every file written here is GGS's own
# published client data, downloaded verbatim:
#
#   cache/items_latest.json    <- empire-html5.goodgamestudios.com  (current item DB)
#   cache/en.json              <- langserv.public.ggs-ep.com        (English strings)
#   cache/ggs.dll.latest.js    <- empire-html5 game client          (sprite atlas map)
#   cache/SOURCES.txt          <- resolved versions + exact source URLs (provenance)
#
# The version pointers and resolution steps mirror what the game client itself
# does at load time. Run by every tool's build.sh; results are gitignored.
# ---------------------------------------------------------------------------
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cache="$here/cache"
mkdir -p "$cache"

EMPIRE="https://empire-html5.goodgamestudios.com/default"
LANGSRV="https://langserv.public.ggs-ep.com"

# mtime helper. GNU/Linux `stat -c` first (it's what CI runs on); macOS falls
# through to the BSD `stat -f` form. Order matters: on Linux `stat -f` does NOT
# fail — it means --file-system and prints non-numeric text, which would poison
# the arithmetic in fresh() under `set -u`.
mtime() { stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0; }
# treat a file as fresh if downloaded < 30 min ago (avoids re-pulling 18 MB
# once per tool when refresh-all.sh runs ten builds back-to-back). Guard the
# value to an integer so a stray non-numeric mtime can never abort the build.
fresh() { [[ -f "$1" ]] || return 1; local m; m="$(mtime "$1")"; [[ "$m" =~ ^[0-9]+$ ]] || m=0; (( $(date +%s) - m < 1800 )); }

ITEMS_VER=""; LANG_VER=""; DLL_REL=""

if fresh "$cache/items_latest.json" && fresh "$cache/en.json" && fresh "$cache/ggs.dll.latest.js"; then
  echo "  _srcdata: cache is fresh (<30 min), skipping download" >&2
  exit 0
fi

echo "  _srcdata: resolving + downloading direct from Goodgame…" >&2

# 1. Items — version pointer then the versioned item DB (downloaded verbatim)
ITEMS_VER="$(curl -fsSL "$EMPIRE/items/ItemsVersion.properties" \
  | tr -d '\r' | grep -oE 'CastleItemXMLVersion=[^ ]+' | cut -d= -f2)"
[[ -n "$ITEMS_VER" ]] || { echo "  _srcdata: could not resolve item version" >&2; exit 1; }
curl -fsSL "$EMPIRE/items/items_v${ITEMS_VER}.json" -o "$cache/items_latest.json"

# 2. Language — versionNo from metadata, then the English bundle
LANG_VER="$(curl -fsSL "$LANGSRV/12/fr/@metadata" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["@metadata"]["versionNo"])')"
[[ -n "$LANG_VER" ]] || { echo "  _srcdata: could not resolve lang version" >&2; exit 1; }
curl -fsSL "$LANGSRV/12@${LANG_VER}/en/*" -o "$cache/en.json"

# 3. DLL — the hashed sprite-atlas map referenced by the game's index.html
DLL_REL="$(curl -fsSL "$EMPIRE/index.html" \
  | grep -oiE '[^"'"'"']*ggs\.dll\.[a-f0-9]{10,}\.js' | head -1)"
[[ -n "$DLL_REL" ]] || { echo "  _srcdata: could not resolve DLL path" >&2; exit 1; }
curl -fsSL "$EMPIRE/$DLL_REL" -o "$cache/ggs.dll.latest.js"

# provenance record
{
  echo "# Pulled $(date -u +'%Y-%m-%d %H:%M:%SZ') direct from Goodgame Studios"
  echo "empire_items_version=$ITEMS_VER"
  echo "empire_items_url=$EMPIRE/items/items_v${ITEMS_VER}.json"
  echo "lang_version=$LANG_VER"
  echo "lang_url=$LANGSRV/12@${LANG_VER}/en/*"
  echo "dll_url=$EMPIRE/$DLL_REL"
} > "$cache/SOURCES.txt"

echo "  _srcdata: items v$ITEMS_VER · lang $LANG_VER · dll ${DLL_REL##*/}" >&2
