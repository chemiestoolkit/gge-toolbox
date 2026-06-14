#!/usr/bin/env python3
# Item Value Finder data builder — decodes the in-game shop packages from the
# public client data in tools/_srcdata/cache/ into tools/item-value/data/packages.json.
# Names/stats come from the overview datasets by wodID, with lang + a camelCase
# prettifier as fallbacks. Run tools/_srcdata/pull.sh first.
# (Spenders Corner's AUD pack data is hand-maintained in tools/spenders/data/au-prices.json.)
import json, collections, os
HERE=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.join(HERE,'..','..')
items=json.load(open(os.path.join(ROOT,'tools/_srcdata/cache/items_latest.json')))
lang=json.load(open(os.path.join(ROOT,'tools/_srcdata/cache/en.json')))

import re as _re
def pretty(s):
    """Turn a dev label into something readable: split camelCase, strip 'shop'/digits, tidy caps."""
    if not s: return s
    s=str(s).strip()
    s=_re.sub(r'^(shop|Shop)\s+', '', s)
    s=_re.sub(r'\s*\d+\s*$', '', s).strip()
    if _re.fullmatch(r'[A-Za-z]+', s) and _re.search(r'[a-z][A-Z]', s):  # camelCase
        s=_re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', s)
    if s.isupper() and len(s)>3: s=s.title()
    return s

def langname(t): return lang.get((t or '').lower()+'_name')

# Clean names + combat stats from the overview datasets (already game-correct), keyed by wodID.
def _load(p):
    import os as _os
    fp=_os.path.join(ROOT,p)
    return json.load(open(fp)) if _os.path.exists(fp) else {}
_tt=_load('tools/overview-troops-tools/data/troops-tools.json')
OV_TROOP={str(x['id']):x for x in _tt.get('troops',[])}
OV_TOOL ={str(x['id']):x for x in _tt.get('tools',[])}
OV_EQUIP={str(x['id']):x for x in _load('tools/overview-equipment/data/equipment.json').get('items',[])}
_rawunit={str(u.get('wodID','')):u for u in items.get('units',[])}

def unit_info(wid):
    """Return (name, kind 'Troops'|'Tools', role, statText). Prefer the overview data."""
    wid=str(wid)
    o=OV_TOOL.get(wid)
    if o: return (o['name'], 'Tools', o.get('role',''), '')
    o=OV_TROOP.get(wid)
    if o:
        atk=int(o.get('atk',0) or 0); dfn=int(o.get('def',0) or 0); role=(o.get('role') or '')
        stat = (str(atk)+' '+role.lower()+' atk') if atk>=dfn and atk>0 else ((str(dfn)+' def') if dfn>0 else '')
        return (o['name'], 'Troops', role, stat)
    u=_rawunit.get(wid)
    if u:
        nm=langname(u.get('type')) or pretty(u.get('comment1')) or ('unit '+wid)
        ma=int(u.get('meleeAttack',0) or 0); md=int(u.get('meleeDefence',0) or 0); rd=int(u.get('rangeDefence',0) or 0)
        role=(u.get('role') or '')
        stat=(str(ma)+' melee atk') if ma>max(md,rd) and ma>0 else ((str(max(md,rd))+' def') if max(md,rd)>0 else '')
        return (nm, 'Troops', role, stat)
    return ('unit '+wid, 'Troops', '', '')

# units dict keeps the old shape (wodID->name) for the ruby-offer decoder
units={wid:unit_info(wid)[0] for wid in _rawunit}
for wid,o in OV_TROOP.items(): units[wid]=o['name']
for wid,o in OV_TOOL.items(): units[wid]=o['name']
cis={str(c.get('constructionItemID','')): (langname(c.get('type')) or pretty(c.get('comment1')) or pretty(c.get('name')) or ('CI '+str(c.get('constructionItemID','')))) for c in items.get('constructionItems',[])}
blds={str(b.get('wodID','')): (langname(b.get('type')) or pretty(b.get('comment1')) or pretty(b.get('type')) or ('building '+str(b.get('wodID','')))) for b in items.get('buildings',[])}
def curdisp(name):
    """Proper in-game currency name from lang (currency_name_*), trying casing variants."""
    if not name: return name
    for cand in (name, name[0].lower()+name[1:], name[0].upper()+name[1:]):
        v=lang.get('currency_name_'+cand)
        if v: return v
    return pretty(name)
curname={c['JSONKey']:curdisp(c['Name']) for c in items['currencies'] if c.get('JSONKey')}
EQ_NAME={k:v.get('name') for k,v in OV_EQUIP.items()}

src=open(os.path.join(ROOT,'tools/_srcdata/cache/SOURCES.txt')).readline().strip('# \n')

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

def pkg_rewards(r):
    out=[]
    pt=r.get('packageType')
    if r.get('unitID') and r.get('unitAmount'):
        nm,bucket,role,stat=unit_info(r['unitID'])
        e={'b':bucket,'name':nm,'qty':iv(r['unitAmount'])}
        if stat: e['stat']=stat
        if role: e['role']=role
        out.append(e)
    if r.get('equipmentIDs'):
        ids=[i for i in str(r['equipmentIDs']).split(',') if i]
        nm=EQ_NAME.get(ids[0]) if ids else None
        if not nm or len(ids)>1:
            c1=pretty(r.get('comment1'))
            nm=(c1 if c1 and not JUNK.search(c1) else None) or (str(len(ids))+'-piece equipment set' if len(ids)>1 else 'Equipment')
        out.append({'b':'Equipment','name':nm,'qty':iv(r.get('equipmentAmount',len(ids)),len(ids))})
    if r.get('relicEquipments'):
        out.append({'b':'Equipment','name':pretty(r.get('comment1')) or 'Relic equipment','qty':len(str(r['relicEquipments']).split(','))})
    if r.get('constructionItemID') and r.get('constructionItemAmount'):
        cid=str(r['constructionItemID']); out.append({'b':'Construction items','name':cis.get(cid) or pretty(r.get('comment1')) or ('CI '+cid),'qty':iv(r['constructionItemAmount'])})
    if r.get('buildingID') and r.get('buildingAmount'):
        bid=str(r['buildingID']); bucket='Decorations' if pt=='deco' else 'Buildings'
        out.append({'b':bucket,'name':pretty(r.get('comment1')) or blds.get(bid) or ('building '+bid),'qty':iv(r['buildingAmount'])})
    if r.get('gemIDs') or r.get('specialGemOfLevelID'):
        lvl=r.get('specialGemOfLevelID'); gnm=('Level '+str(lvl)+' gem') if lvl else (pretty(r.get('comment1')) or 'Gem')
        out.append({'b':'Gems','name':gnm,'qty':iv(r.get('gemAmount',1))})
    if r.get('lootBox'): out.append({'b':'Loot boxes','name':(r.get('comment1') or 'Loot box'),'qty':iv(r.get('lootBox',1))})
    if r.get('rewardBags'): out.append({'b':'Reward bags','name':(r.get('comment1') or 'Reward bag'),'qty':iv(r.get('rewardBags',1))})
    addmap=[('addSceatToken','Sceats','Sceats'),('addLegendaryMaterial','Upgrade tokens','Upgrade tokens'),
            ('addLegendaryToken','Construction tokens','Construction tokens'),
            ('addSaleDaysLuckyWheelTicket','Event / gacha currency','Affluence tickets'),
            ('addLuckyWheelTicket','Event / gacha currency','Lucky wheel tickets'),
            ('addPegasusTicket','Travel tickets','Pegasus tickets'),('vipPoints','VIP','VIP points'),
            ('vipTime','VIP','VIP time'),('amountXP','XP','XP'),('addImperialPatronageCharter','Misc','Imperial Patronage Charter'),
            ('addDecoDust','Misc','Deco Dust'),('addFusionCurrency','Misc','Fusion currency'),('addResourceVillageToken','Misc','Resource Village token')]
    for f,bucket,nm in addmap:
        if str(r.get(f,'')) not in ('','0'): out.append({'b':bucket,'name':nm,'qty':iv(r[f])})
    for f in r:
        if f.endswith('Token') and f.startswith('add') and f not in ('addLegendaryToken',):
            v=r.get(f)
            if str(v) not in ('','0') and 'LTPE' not in f and f not in ('addSceatToken',):
                out.append({'b':'Event / gacha currency','name':curdisp(f[3:]),'qty':iv(v)})
        if f.startswith('addShard'):
            if str(r.get(f)) not in ('','0'): out.append({'b':'Hero shards','name':pretty(f[8:])+' shard','qty':iv(r[f])})
        if f.startswith('add') and ('HourSkip' in f or 'MinSkip' in f):
            if str(r.get(f)) not in ('','0'):
                sm=_re.match(r'add(\d+)(Hour|Min)Skip', f)
                snm=(sm.group(1)+('h' if sm.group(2)=='Hour' else 'm')+' skip') if sm else pretty(f[3:])
                out.append({'b':'Time skips','name':snm,'qty':iv(r[f])})
    res=0
    for f in ('amountWood','amountStone','amountFood','amountCoal','amountOil','amountGlass','amountIron','amountHoney','amountMead','amountBeef','hiddenFood','hiddenMead','hiddenBeef','amountC1'):
        if str(r.get(f,'')) not in ('','0'): res+=iv(r[f])
    if res: out.append({'b':'Resources','name':'Resources','qty':res})
    return out

JUNK=_re.compile(r'CUT|delete|rankreward|compensation|collector event|prime ?day|login|daily ?reward|beginner|workaround|x-play|\bbss\b|suboffer|testserver|\bdummy\b|placeholder|do not use', _re.I)
def clean(r):
    c2=(r.get('comment2') or '')+' '+(r.get('comment1') or '')
    if str(r.get('hideInShop',''))=='1': return False
    return not JUNK.search(c2)

PKG=[]
for r in items['packages']:
    if not clean(r): continue
    cur,cost=cost_of(r)
    if not cur or not cost: continue
    rw=pkg_rewards(r)
    if not rw: continue
    rec={'id':r['packageID'],'shop':pretty((r.get('comment2') or '').strip())[:42],'cur':cur,'cost':cost,'rw':rw}
    for k_src,k_dst in [('minLevel','lvlMin'),('maxLevel','lvlMax'),('minLegendLevel','llMin'),('maxLegendLevel','llMax')]:
        v=r.get(k_src)
        if v not in (None,''): rec[k_dst]=int(float(v))
    PKG.append(rec)

buckets=sorted({w['b'] for p in PKG for w in p['rw']})
pkgout={'generated':src,'buckets':buckets,'packages':PKG}
OUTDIR=os.path.join(ROOT,'tools/item-value/data')
os.makedirs(OUTDIR,exist_ok=True)
json.dump(pkgout,open(os.path.join(OUTDIR,'packages.json'),'w'),separators=(',',':'))

# ---- sales.json : the real-money offer catalogue (Spenders sale search) -----
# paymentrewards = every Super Sale / Benefit / Event / Prime money bundle.
# Decode the *slots* reward string into bucketed contents; price tier = c2ForReward.
# token -> (bucket, display name) for the non-unit/non-id slot tokens
TOK={'C2':('Rubies','Rubies'),'C1':('Resources','Coins'),'F':('Resources','Food'),'W':('Resources','Wood'),
 'S':('Resources','Stone'),'C':('Resources','Coal'),'O':('Resources','Oil'),'G':('Resources','Glass'),
 'I':('Resources','Iron'),'A':('Resources','Aquamarine'),'HF':('Resources','Food'),'HM':('Resources','Mead'),
 'HB':('Resources','Beef'),'MEAD':('Resources','Mead'),'HONEY':('Resources','Honey'),'BEEF':('Resources','Beef'),
 'RB':('Resources','Material bag'),'RP':('Resources','Resource points'),
 'VT':('VIP','VIP time'),'VP':('VIP','VIP points'),'XP':('XP','XP'),
 'RE':('Equipment','Random hero'),'GE':('Equipment','Random equipment'),'UE':('Equipment','Unique equipment'),
 'EUE':('Equipment','Unique enchanted equipment'),'GID':('Gems','Gem'),'GLID':('Gems','Random gem'),
 'CIBP':('Construction items','CI blueprint'),'LB':('Loot boxes','Loot box'),'RI':('Misc','Relic'),
 'GT':('Misc','Gift package'),'EF':('Misc','Extinguish fire'),'AG':('Misc','Alliance gift'),
 'PD':('Boosters','Payment doubler'),'PLD':('Misc','Plague doctor'),'PTS':('Misc','Permanent tool slot'),
 'PUS':('Misc','Permanent unit slot'),'AIP':('Boosters','Alien protection'),'DPT':('Boosters','Dungeon protection'),
 'B':('Boosters','Booster'),'PG':('Boosters','Glory booster'),'XPB':('Boosters','XP booster'),
 'KTB':('Boosters','Khan tablet booster'),'KMB':('Boosters','Khan medal booster'),'RPB':('Boosters','Rage booster'),
 'REPB':('Boosters','Reputation booster'),'GPB':('Boosters','Gallantry booster'),'STB':('Boosters','Samurai booster'),
 'LTB':('Boosters','LTPE booster'),'ACB':('Boosters','Alliance coin booster'),'MS':('Time skips','Minute skips')}

def decode_offer(s):
    try: data=json.loads(s.replace('*','"'))
    except Exception: return None
    out=[]
    for slot in data.get('slots',[]):
        if not isinstance(slot,list) or len(slot)<1: continue
        tok=slot[0]; val=slot[1] if len(slot)>1 else None
        if tok in ('OL','OG','OM'): continue
        if tok=='U' and isinstance(val,list):
            nm,bk,role,stat=unit_info(val[0]); e={'b':bk,'name':nm,'qty':iv(val[1] if len(val)>1 else 1)}
            if stat: e['stat']=stat
        elif tok=='CI' and isinstance(val,list):
            e={'b':'Construction items','name':cis.get(str(val[0]),'CI '+str(val[0])),'qty':iv(val[1] if len(val)>1 else 1)}
        elif tok=='D':
            wid=str(val[0] if isinstance(val,list) else val); e={'b':'Decorations','name':blds.get(wid,'building '+wid),'qty':iv(val[1] if isinstance(val,list) and len(val)>1 else 1)}
        elif tok in TOK:
            bk,nm=TOK[tok]; e={'b':bk,'name':nm,'qty':iv(val) if not isinstance(val,list) else 1}
        elif tok in curname:
            e={'b':'Currencies','name':curname[tok],'qty':iv(val) if not isinstance(val,list) else 1}
        else:
            continue
        out.append(e)
    return out

seen={}; SALES=[]
for r in items['paymentrewards']:
    its=decode_offer(r.get('rewards','') or '')
    if not its: continue
    c2=int(r['c2ForReward'])
    sig=(c2, tuple(sorted((i['name'], i['qty']) for i in its)))
    if sig in seen: continue
    seen[sig]=1
    SALES.append({'id':int(r['paymentrewardID']),'c2':c2,'bonus':int(r.get('shownOfferBonus',0) or 0),'items':its})
sale_buckets=sorted({i['b'] for s in SALES for i in s['items']})
salesout={'generated':src,'buckets':sale_buckets,'auLadder':[[p['rubies'],p['aud']] for p in json.load(open(os.path.join(ROOT,'tools/spenders/data/au-prices.json')))['rubyPacks']],'sales':SALES}
json.dump(salesout,open(os.path.join(HERE,'data','sales.json'),'w'),separators=(',',':'))
print('sales.json:',len(SALES),'distinct money offers (from',len(items['paymentrewards']),'), buckets:',sale_buckets)
print('packages.json:',len(PKG),'shoppable packages, buckets:',buckets)
