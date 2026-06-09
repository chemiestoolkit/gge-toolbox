# Decorations overview extractor.
# main = items_*.json ; --slurpfile lang = lowercased lang map.
($lang[0]) as $L
| { generated: (now|todate),
    items: (
      [ .buildings[]
        | select(.buildingGroundType=="DECO")
        | ($L["deco_\(.type|ascii_downcase)_name"]) as $n
        | select($n != null)
        | { name:$n,
            type:.type,
            might:(.mightValue|tonumber? // 0),
            po:(.decoPoints|tonumber? // 0),
            w:(.width|tonumber? // 1),
            h:(.height|tonumber? // 1) } ]
      | group_by(.name) | map(max_by(.might))      # one row per deco, strongest variant
      | map(.tiles = (.w * .h)
            | .mpt = (if .tiles>0 then ((.might/.tiles)|floor) else 0 end)
            | .size = "\(.w)x\(.h)")
      | sort_by(-.might)
    ) }
