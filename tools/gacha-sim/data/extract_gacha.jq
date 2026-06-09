# Build lookup indexes for each reward-reference type
(INDEX(.buildings[]; (.wodID|tostring)))          as $B
| (INDEX(.units[]; (.wodID|tostring)))            as $U
| (INDEX(.equipments[]; .equipmentID))            as $E
| (INDEX(.constructionItems[]; .constructionItemID)) as $C
| (INDEX(.gems[]; (.gemID|tostring)))             as $G
| (INDEX(.currencies[]; (.currencyID|tostring)))  as $CUR
| (INDEX(.rewards[]; .rewardID))                  as $R

# humanize an "add<Thing>" shorthand key -> "Thing" with spaces
| def human($k): ($k | ltrimstr("add") | gsub("(?<c>[A-Z])"; " \(.c)") | sub("^ ";"") );

# resolve a reward object into {name, type, amount}
def resolve($r):
    if $r == null then {name:"Unknown", type:"Unknown", amount:null}
    elif ($r.decoWodID != null) then
      {name: ($B[$r.decoWodID|tostring].comment1 // ("Decoration #"+($r.decoWodID|tostring))), type:"Decoration", amount:1}
    elif ($r.equipmentIDs != null) then
      ($r.equipmentIDs|split(",")[0]) as $id
      | {name: ($E[$id].comment1 // ("Equipment #"+$id)), type:"Equipment", amount:1}
    elif ($r.relicEquipments != null) then
      ($r.relicEquipments|tostring|split(",")[0]|split("+")[0]) as $id
      | {name: ($E[$id].comment1 // ("Relic Equipment #"+$id)), type:"Equipment", amount:1}
    elif ($r.constructionItemIDs != null) then
      ($r.constructionItemIDs|tostring|split(",")[0]) as $id
      | {name: ($C[$id].comment1 // ("Construction Item #"+$id)), type:"Construction", amount:1}
    elif ($r.gemIDs != null) then
      ($r.gemIDs|tostring|split(",")[0]) as $id
      | {name: ($G[$id].comment1 // ("Gem #"+$id)), type:"Gem", amount:1}
    elif ($r.units != null) then
      ($r.units|tostring|split("+")) as $p
      | {name: (($U[$p[0]].name // $U[$p[0]].type) // "Troops"), type:"Units", amount: (($p[1]//$p[0])|tonumber? // null)}
    elif ($r.lootBox != null) then
      {name:"Loot Box", type:"LootBox", amount:1}
    else
      ( $r | to_entries | map(select(.key|startswith("add"))) | .[0] ) as $a
      | if $a != null then
          {name: human($a.key), type:"Resource", amount: ($a.value|tonumber? // $a.value)}
        else
          {name: ($r.comment2 // $r.comment1 // "Reward"), type:"Misc", amount:null}
        end
    end;

{
  generated: (now | todate),
  source: "GeneralsCamp/ggempire-data-cache (items_latest.json)",
  pools: (
    .lootBoxTombolas
    | group_by(.tombolaID)
    | map({
        key: .[0].tombolaID,
        value: {
          total: (map(.shares|tonumber) | add),
          entries: (
            sort_by(- (.shares|tonumber))
            | map(
                (.rewardIDs|split(",")[0]) as $rid
                | resolve($R[$rid]) as $res
                | {
                    rarity: (.rewardCategory|tonumber),
                    shares: (.shares|tonumber),
                    name: $res.name,
                    type: $res.type,
                    amount: $res.amount
                  }
              )
          )
        }
      })
    | from_entries
  ),
  lootBoxes: (
    .lootBoxes | map({
      id:.lootBoxID, name:.name, rarity:(.rarity|tonumber? // 1),
      tombolaID:.lootBoxTombolaID, draws:(.draws|tonumber? // 1)
    })
  ),
  gachaEvents: (
    .gachaEvents | map({
      id:.gachaID, name:(.comment1 // ("Gacha "+.gachaID)),
      tombolaID:.lootBoxTombolaID, cost:(.costSoldierBiscuit|tonumber? // null),
      minPulls:(.minPulls|tonumber? // 0), maxPulls:(.maxPulls|tonumber? // null),
      multiPullMax:(.multiPullMax|tonumber? // 1), spins:(.tombolaSpinsAmount|tonumber? // 1)
    })
  )
}
