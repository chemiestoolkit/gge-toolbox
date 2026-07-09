# Construction items overview extractor.
# main = items_*.json ; --slurpfile lang = lowercased lang map.
($lang[0]) as $L
| (.effects | map({key:.effectID, value:.name}) | from_entries) as $E
# legacy building_items stat fields — value sits directly on the item,
# display template is ci_effect_<field-lowercase> and carries its own +/− and % formatting
| ["unitWallCount","recruitSpeedBoost","woodStorage","stoneStorage","ReduceResearchResourceCosts",
   "Stoneproduction","Woodproduction","Foodproduction","foodStorage","unboostedFoodProduction",
   "defensiveToolsSpeedBoost","defensiveToolsCostsReduction","meadStorage","recruitCostReduction",
   "honeyStorage","hospitalCapacity","healSpeed","marketCarriages","XPBoostBuildBuildings",
   "stackSize","glassStorage","Glassproduction","ironStorage","Ironproduction","coalStorage",
   "Coalproduction","oilStorage","Oilproduction","offensiveToolsCostsReduction","feastCostsReduction",
   "Meadreduction","surviveBoost","unboostedStoneProduction","unboostedWoodProduction",
   "offensiveToolsSpeedBoost","espionageTravelBoost"] as $LEGACY
| { generated: (now|todate),
    items: (
      [ .constructionItems[]
        | . as $it
        | ((.name // "")|ascii_downcase) as $rn
        | (
            $L["ci_appearance_\($rn)"] // $L["ci_primary_\($rn)"] // $L["ci_secondary_\($rn)"] //
            $L["ci_appearance_\($rn)_premium"] // $L["ci_primary_\($rn)_premium"] // $L["ci_secondary_\($rn)_premium"] //
            $L["ci_\($rn)"]
          ) as $n
        | select($n != null)
        | { name: $n,
            raw: (.name // ""),
            level: (.level|tonumber? // 1),
            rarity: (.rarenessID|tonumber? // 0),
            kind: (if .slotTypeID == "1" then "Primary"
                   elif .slotTypeID == "2" then "Relic"
                   elif (.duration // "") != "" then "Temporary"
                   elif (.decoPoints // "") != "" then "Appearance"
                   else "Event" end),
            effects: (
              # modern effect refs: "702&12000,..."
              ((.effects // "")
               | if . == "" then [] else
                   split(",")
                   | map(
                       (split("&")) as $p
                       | ($E[$p[0]] // "") as $en
                       | ($en|ascii_downcase) as $b
                       | ($en|test("unboosted";"i")) as $flat
                       # pair values "subID+value" (e.g. craftingQueue "1+5") → lang key gets _subID suffix
                       | (($p[1] // "0") | split("+")) as $vp
                       | (if ($vp|length) > 1 then $vp[0] else null end) as $sub
                       | ($vp[-1]|tonumber? // 0) as $val
                       | (if $flat then null
                          else (((if $sub != null then $L["ci_effect_\($b)_\($sub)"] else null end)
                                // $L["ci_effect_\($b)"] // $L["equip_effect_description_\($b)"]) // null
                               | if . != null and ($en|test("decrease";"i")) then sub("\\+\\{0\\}";"-{0}") else . end)
                          end) as $tmpl
                       | { v: $val,
                           tmpl: $tmpl,
                           pct: ((($en|test("boost";"i")) or ([$tmpl // "", $L["effect_name_\($b)"] // ""] | any(contains("%"))))
                                 and ($flat|not)),
                           label: ((if $sub != null then $L["effect_name_\($b)_\($sub)"] else null end)
                                   // $L["effect_name_\($b)"] // (if $en == "" then "Effect \($p[0])" else $en end)) }
                     )
                 end)
              +
              # legacy direct stat fields
              ([ $LEGACY[]
                 | . as $f
                 | $it[$f]
                 | select(. != null and . != "")
                 | { v: (tonumber? // 0),
                     tmpl: ($L["ci_effect_\($f|ascii_downcase)"] // null),
                     pct: false,
                     label: $f } ])
            )
          } ]
      | map(select((.effects|length) > 0))
      # one card per (name, kind): keep the highest level variant
      | group_by(.name + "|" + .kind) | map(max_by(.level))
      | sort_by(.name)
    ) }
