#!/usr/bin/env python3
# Spenders Corner data builder — decodes Goodgame's offer-targeting tables
# (paymentrewards / primeDays / shoppingCarts) from the public client data in
# tools/_srcdata/cache/ into data/offers.json.
# Reward slot tokens decoded via the client's CollectableItem*VO SERVER_KEY map
# + the currencies table JSONKey column. Run tools/_srcdata/pull.sh first.
import json, collections, os
HERE=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.join(HERE,'..','..')
items=json.load(open(os.path.join(ROOT,'tools/_srcdata/cache/items_latest.json')))
lang=json.load(open(os.path.join(ROOT,'tools/_srcdata/cache/en.json')))

units={}
for tbl in ['units','tools']:
    for u in items.get(tbl,[]):
        wid=str(u.get('wodID',''))
        nm=lang.get((u.get('type') or '')+'_name') or u.get('comment1') or u.get('type')
        if wid: units[wid]=nm
cis={str(c.get('constructionItemID', c.get('wodID',''))): (lang.get((c.get('type') or '')+'_name') or c.get('comment1') or c.get('type')) for c in items.get('constructionItems',[])}
blds={str(b.get('wodID','')): (lang.get((b.get('type') or '')+'_name') or b.get('comment1') or b.get('type')) for b in items.get('buildings',[])}
curname={c['JSONKey']:c['Name'] for c in items['currencies'] if c.get('JSONKey')}

LEGEND={'U':'unit','W':'Wood','S':'Stone','F':'Food','C':'Coal','O':'Oil','G':'Glass','I':'Iron','A':'Aquamarine',
'MEAD':'Mead','HONEY':'Honey','BEEF':'Beef','HF':'Hidden food','HM':'Hidden mead','HB':'Hidden beef','C1':'Coins','C2':'Rubies',
'VT':'VIP time (s)','VP':'VIP points','XP':'XP','AP':'Achievement points','RE':'Random hero','GE':'Random equipment (rareness)',
'UE':'Unique equipment','EUE':'Unique enchanted equipment','GID':'Gem','GLID':'Random gem','CI':'Construction item','CIBP':'CI blueprint',
'D':'Building/Deco','LB':'Loot box','RB':'Material bag','RI':'Relic','GT':'Gift package','EF':'Extinguish fire','AG':'Alliance gift',
'PD':'Payment doubler','PLD':'Plague doctor','PTS':'Permanent tool slot','PUS':'Permanent unit slot','AIP':'Alien protection','DPT':'Dungeon protection',
'B':'Booster','PG':'Glory booster','XPB':'XP booster','KTB':'Khan tablet booster','KMB':'Khan medal booster','RPB':'Rage booster',
'REPB':'Reputation booster','GPB':'Gallantry booster','STB':'Samurai booster','LTB':'LTPE booster','ACB':'Alliance coin booster',
'MS':'Minute skips','RP':'Resource point','OL':'(display flag)','OG':'(display flag)','OM':'(display flag)'}

def decode_rewards(s):
    try: data=json.loads(s.replace('*','"'))
    except Exception: return None
    out=[]
    for slot in data.get('slots',[]):
        if not isinstance(slot,list) or len(slot)<1: continue
        tok=slot[0]; val=slot[1] if len(slot)>1 else None
        if tok in ('OL','OG','OM'): continue
        e={'t':tok}
        if tok=='U' and isinstance(val,list):
            e['name']=units.get(str(val[0]),'unit '+str(val[0])); e['qty']=val[1] if len(val)>1 else 1
        elif tok=='CI' and isinstance(val,list):
            e['name']=cis.get(str(val[0]),'CI '+str(val[0])); e['qty']=val[1] if len(val)>1 else 1
        elif tok=='D':
            wid=str(val[0] if isinstance(val,list) else val); e['name']=blds.get(wid,'building '+wid); e['qty']=val[1] if isinstance(val,list) and len(val)>1 else 1
        elif tok in LEGEND and not isinstance(val,list):
            e['name']=LEGEND.get(tok,tok); e['qty']=val
        elif tok in curname and not isinstance(val,list):
            e['name']=curname[tok]; e['qty']=val
        else:
            e['name']=LEGEND.get(tok) or curname.get(tok) or tok; e['val']=val
        out.append(e)
    return out

def seg(r):
    s={}
    for k_src,k_dst in [('minLevel','lvlMin'),('maxLevel','lvlMax'),('playerIsPayuser','payuser'),
        ('c2LifetimeSpentMin','spentMin'),('c2LifetimeSpentMax','spentMax'),
        ('C290daysMin','spent90Min'),('C290daysMax','spent90Max'),
        ('daysSinceLastPaymentMin','lapsedMin'),('daysSinceLastPaymentMax','lapsedMax'),
        ('rewardCap','cap'),('duration','dur'),('displayType','dt')]:
        v=r.get(k_src)
        if v not in (None,''): s[k_dst]=v
    return s

offers=[{'id':r['paymentrewardID'],'c2':int(r['c2ForReward']),'shownValue':int(r['shownCurrencyValue']),
         'bonus':int(r['shownOfferBonus']),**seg(r),'rewards':decode_rewards(r['rewards'])} for r in items['paymentrewards']]
prime=[{'id':r['primeDayID'],**seg(r),'offerIds':[i for i in str(r.get('paymentRewardIDs','')).split(',') if i]} for r in items['primeDays']]
carts=[{'id':r['cartOptionID'],'type':r.get('typeID'),'group':r.get('groupID'),'bonus':int(r.get('shownOfferBonus',0) or 0),
        **seg(r),'rewardId':r.get('rewardID')} for r in items['shoppingCarts']]

src=open(os.path.join(ROOT,'tools/_srcdata/cache/SOURCES.txt')).readline().strip('# \n')
out={'generated':src,'tokenLegend':LEGEND,'offers':offers,'primeDays':prime,'shoppingCarts':carts}
os.makedirs(os.path.join(HERE,'data'),exist_ok=True)
json.dump(out,open(os.path.join(HERE,'data','offers.json'),'w'),separators=(',',':'))
print('offers.json:',len(offers),'offers,',len(prime),'primeDays,',len(carts),'carts')

# ---- packages.json : the in-game token shops (item-value finder) -----------
# Each shoppable package, decoded to what you get + what you pay (which currency).
CUR = {  # cost field -> friendly currency name
 'costKhanTablet':'Khan Tablets','costKhanMedal':'Khan Medals','costSamuraiToken':'Samurai Tokens',
 'costSamuraiMedal':'Samurai Medals','costGoldToken':'Gold Tokens','costSilverToken':'Silver Tokens',
 'costSceatToken':'Sceats','costPearlRelic':'Pearl Relics','costSkullRelic':'Skull Relics',
 'costGreenSkullRelic':'Green Skull Relics','costRiftCoin':'Rift Coins','costLegendaryRiftCoin':'Legendary Rift Coins',
 'costRiftShard':'Rift Shards','costOfferingShard':'Offering Shards','costWishingWellCoin':'Wishing Well Coins',
 'costSilverRune':'Silver Runes','costGoldRune':'Gold Runes','costFusionCurrency':'Fusion Currency','costDecoDust':'Deco Dust',
 'costAnniversaryToken':'Anniversary Tokens','costXmasLTPEToken':'Xmas Event Tokens','costSpringLTPEToken':'Spring Event Tokens',
 'costLotusFlowerLTPEToken':'Lotus Event Tokens','costNewKingLTPEToken':'New King Event Tokens',
 'costOctoberfestLTPEToken':'Oktoberfest Event Tokens','costHalloweenLTPEToken':'Halloween Event Tokens',
 'costIceLTPEToken':'Ice Event Tokens','costStPatrickLTPEToken':'St Patrick Event Tokens','costMayaLTPEToken':'Maya Event Tokens',
 'costPiratesLTPEToken':'Pirates Event Tokens','costDragonriderLTPEToken':'Dragonrider Event Tokens',
 'cost1MinSkip':'Minute Skips',
}
PPRICE = {'packagePriceC2':'Rubies','packagePriceC1':'Coins','packagePriceAquamarine':'Aquamarine'}

def cost_of(r):
    for k in r:
        if k.startswith('cost') and str(r.get(k)) not in ('','0','None'):
            return (CUR.get(k, k[4:]), int(float(r[k])))
    for k in PPRICE:
        if str(r.get(k,'')) not in ('','0'): return (PPRICE[k], int(float(r[k])))
    return (None, None)

import re as _re
def iv(x, d=1):
    m=_re.match(r'-?\d+', str(x)); return int(m.group()) if m else d

unit_is_tool = {str(u.get('wodID','')) for u in items.get('tools',[])}
def pkg_rewards(r):
    out=[]
    pt=r.get('packageType')
    if r.get('unitID') and r.get('unitAmount'):
        wid=str(r['unitID'])
        bucket = 'Tools' if (pt=='tool' or wid in unit_is_tool) else 'Troops'
        out.append({'b':bucket,'name':units.get(wid,'unit '+wid),'qty':iv(r['unitAmount'])})
    if r.get('equipmentIDs'):
        n=len(str(r['equipmentIDs']).split(',')); out.append({'b':'Equipment','name':(r.get('comment1') or 'Equipment'),'qty':iv(r.get('equipmentAmount',n),n)})
    if r.get('relicEquipments'):
        out.append({'b':'Equipment','name':(r.get('comment1') or 'Relic equipment'),'qty':len(str(r['relicEquipments']).split(','))})
    if r.get('constructionItemID') and r.get('constructionItemAmount'):
        cid=str(r['constructionItemID']); out.append({'b':'Construction items','name':cis.get(cid,r.get('comment1') or ('CI '+cid)),'qty':iv(r['constructionItemAmount'])})
    if r.get('buildingID') and r.get('buildingAmount'):
        bid=str(r['buildingID']); bucket='Decorations' if pt=='deco' else 'Buildings'
        out.append({'b':bucket,'name':blds.get(bid,r.get('comment1') or ('building '+bid)),'qty':iv(r['buildingAmount'])})
    if r.get('gemIDs') or r.get('specialGemOfLevelID'):
        out.append({'b':'Gems','name':(r.get('comment1') or 'Gem'),'qty':iv(r.get('gemAmount',1))})
    if r.get('lootBox'): out.append({'b':'Loot boxes','name':(r.get('comment1') or 'Loot box'),'qty':iv(r.get('lootBox',1))})
    if r.get('rewardBags'): out.append({'b':'Reward bags','name':(r.get('comment1') or 'Reward bag'),'qty':iv(r.get('rewardBags',1))})
    addmap=[('addSceatToken','Sceats','Sceats'),('addLegendaryMaterial','Upgrade tokens','Upgrade tokens'),
            ('addLegendaryToken','Construction tokens','Construction tokens'),
            ('addSaleDaysLuckyWheelTicket','Event / gacha currency','Sale lucky-wheel tickets'),
            ('addLuckyWheelTicket','Event / gacha currency','Lucky-wheel tickets'),
            ('addPegasusTicket','Travel tickets','Pegasus tickets'),('vipPoints','VIP','VIP points'),
            ('vipTime','VIP','VIP time'),('amountXP','XP','XP'),('addImperialPatronageCharter','Misc','Imperial Patronage Charter'),
            ('addDecoDust','Misc','Deco Dust'),('addFusionCurrency','Misc','Fusion currency'),('addResourceVillageToken','Misc','Resource Village token')]
    for f,bucket,nm in addmap:
        if str(r.get(f,'')) not in ('','0'): out.append({'b':bucket,'name':nm,'qty':iv(r[f])})
    for f in r:
        if f.endswith('Token') and f.startswith('add') and f not in ('addLegendaryToken',):
            v=r.get(f)
            if str(v) not in ('','0') and 'LTPE' not in f and f not in ('addSceatToken',):
                out.append({'b':'Event / gacha currency','name':f[3:].replace('Token',' token'),'qty':iv(v)})
        if f.startswith('addShard'):
            if str(r.get(f)) not in ('','0'): out.append({'b':'Hero shards','name':f[8:]+' shard','qty':iv(r[f])})
        if f.startswith('add') and 'HourSkip' in f or f.endswith('MinSkip') and f.startswith('add'):
            if str(r.get(f)) not in ('','0'): out.append({'b':'Time skips','name':f[3:],'qty':iv(r[f])})
    res=0
    for f in ('amountWood','amountStone','amountFood','amountCoal','amountOil','amountGlass','amountIron','amountHoney','amountMead','amountBeef','hiddenFood','hiddenMead','hiddenBeef','amountC1'):
        if str(r.get(f,'')) not in ('','0'): res+=iv(r[f])
    if res: out.append({'b':'Resources','name':'Resources','qty':res})
    return out

def clean(r):
    c2=(r.get('comment2') or '');
    return not ('CUT' in c2 or 'delete' in c2.lower() or str(r.get('hideInShop',''))=='1')

PKG=[]
for r in items['packages']:
    if not clean(r): continue
    cur,cost=cost_of(r)
    if not cur or not cost: continue
    rw=pkg_rewards(r)
    if not rw: continue
    rec={'id':r['packageID'],'shop':(r.get('comment2') or '').strip()[:48],'cur':cur,'cost':cost,'rw':rw}
    for k_src,k_dst in [('minLevel','lvlMin'),('maxLevel','lvlMax'),('minLegendLevel','llMin'),('maxLegendLevel','llMax')]:
        v=r.get(k_src)
        if v not in (None,''): rec[k_dst]=int(float(v))
    PKG.append(rec)

buckets=sorted({w['b'] for p in PKG for w in p['rw']})
pkgout={'generated':src,'buckets':buckets,'packages':PKG}
json.dump(pkgout,open(os.path.join(HERE,'data','packages.json'),'w'),separators=(',',':'))
print('packages.json:',len(PKG),'shoppable packages, buckets:',buckets)
