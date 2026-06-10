# Loot/mystery box extractor — same reward-name mapping as the gacha sim.
# Inputs: main = items_latest.json ; --slurpfile lang = LOWERCASED lang map (en).
# Output: { generated, boxes:[ {id,name,internal,rarity,rarityName,draws,total,entries} ] }

($lang[0]) as $L
| (INDEX(.buildings[]; (.wodID|tostring)))           as $B
| (INDEX(.units[]; (.wodID|tostring)))               as $U
| (INDEX(.equipments[]; .equipmentID))               as $E
| (INDEX(.constructionItems[]; .constructionItemID)) as $C
| (INDEX(.gems[]; (.gemID|tostring)))                as $G
| (INDEX(.rewards[]; .rewardID))                     as $R
| (.lootBoxTombolas | group_by(.tombolaID)
   | map({ key: .[0].tombolaID,
           value: { total: (map(.shares|tonumber)|add), rows: . } }) | from_entries) as $POOL
| def L($k): $L[($k|ascii_downcase)];
def human($k): ($k|ltrimstr("add")|gsub("(?<c>[A-Z])";" \(.c)")|sub("^ ";""));
def nm($r):
    if $r == null then {name:"Unknown", type:"Unknown", amount:null}
    elif ($r.decoWodID != null) then
      ($B[$r.decoWodID|tostring]) as $b
      | {name: (L("deco_\($b.type)_name") // $b.comment1 // "Decoration"), type:"Decoration", amount:1}
    elif ($r.equipmentIDs != null) then
      ($r.equipmentIDs|split(",")[0]) as $id
      | {name: (L("equipment_unique_\($id)") // ($E[$id].comment1) // "Equipment"), type:"Equipment", amount:1}
    elif ($r.relicEquipments != null) then
      ($r.relicEquipments|tostring|split(",")[0]|split("+")[0]) as $id
      | {name: (L("equipment_unique_\($id)") // ($E[$id].comment1) // "Equipment"), type:"Equipment", amount:1}
    elif ($r.units != null) then
      ($r.units|tostring|split("+")) as $p
      | ($U[$p[0]]) as $u
      | {name: (L("\($u.type)_name") // $u.name // "Troops"), type:"Units", amount: (($p[1]//$p[0])|tonumber? // null)}
    elif ($r.constructionItemIDs != null) then
      ($r.constructionItemIDs|tostring|split(",")[0]) as $id
      | {name: (L("ci_appearance_\($C[$id].name)") // ($C[$id].comment1) // "Construction Item"), type:"Construction", amount:1}
    elif ($r.gemIDs != null) then
      ($r.gemIDs|tostring|split(",")[0]) as $id
      | {name: (L("gem_unique_\($id)") // L("gem_\($id)_name") // ($G[$id].comment1) // "Gem"), type:"Gem", amount:1}
    else
      ($r|to_entries|map(select(.key|startswith("add")))|.[0]) as $a
      | if $a != null then
          ($a.key|ltrimstr("add")) as $cn
          | {name: (L("currency_name_\($cn)") // human($a.key)), type:"Resource", amount:($a.value|tonumber? // $a.value)}
        else
          # plain resource fields (food/wood/stone/coins…) on the reward row
          ($r|to_entries|map(select(.key as $k
              | ["food","wood","stone","coins","oil","glass","iron","honey","mead"]
              | index($k)))|.[0]) as $res
          | if $res != null then
              {name: (L("resource_\($res.key)") // ($res.key|ascii_upcase[0:1] + $res.key[1:])),
               type:"Resource", amount:($res.value|tonumber? // $res.value)}
            else {name:"Reward", type:"Misc", amount:null} end
        end
    end;
{
  generated: (now|todate),
  boxes: (
    .lootBoxes
    | map(
        . as $box
        | ($POOL[$box.lootBoxTombolaID]) as $p
        | select($p != null)
        | { id: ($box.lootBoxID|tonumber),
            internal: $box.name,
            rarity: ($box.rarity|tonumber),
            rarityName: (L("generals_rarity_\($box.rarity)") // ""),
            name: (L("mysterybox_boxname_\($box.name)_\($box.rarity)")
                   // "\($box.name) \($box.rarity)"),
            draws: ($box.draws|tonumber? // 1),
            total: $p.total,
            entries: ($p.rows | sort_by(-(.shares|tonumber)) | map(
                (.rewardIDs|split(",")[0]) as $rid | nm($R[$rid]) as $n
                | { rarity:(.rewardCategory|tonumber? // 0), shares:(.shares|tonumber),
                    name:$n.name, type:$n.type, amount:$n.amount } )) }
      )
    | sort_by(.internal, .rarity)
  )
}
