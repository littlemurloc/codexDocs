from pathlib import Path
from collections import Counter, defaultdict
import json, hashlib, openpyxl, re

ROOT=Path(r'D:\littl\testTempFile\ProjectMonster02\maps\map3')
OUT=Path(__file__).resolve().parent
SOURCE=Path(r'C:\Users\littl\Downloads\羁绊.xlsx')
ns={'__file__':str(Path('tmp/card-audit-20261014/inspect_cards.py').resolve())}
exec(Path('tmp/card-audit-20261014/inspect_cards.py').read_text('utf8').split('CARDDATA=')[0], ns)
walk,outline=ns['walk'],ns['outline']
LANG=ns['LANG']
objects={int(p.stem):json.loads(p.read_text('utf8')) for p in (ROOT/'editor_table/abilityall').glob('*.json')}
names={aid:LANG.get(str(d.get('name')),d.get('name')) for aid,d in objects.items()}
tables={}
members=defaultdict(list)
for faction,table in [('吴国','吴国temp'),('蜀国','蜀国temp'),('魏国','魏国temp'),('群雄','群雄temp'),('铸造','武器锻造temp')]:
    data=json.loads((ROOT/f'tables/{table}.json').read_text('utf8'))['table_data']['data']
    rows=[dict(zip(data[0],row)) for row in data[2:] if row[0] not in (None,'')]
    tables[faction]=rows
    for row in rows: members[row['技能类型']].append({'table':table,**row})
formal=json.loads((ROOT/'tables/军令卡牌技能表.json').read_text('utf8'))['table_data']['data']
formal_ids={row[1] for row in formal[2:] if row[0] not in (None,'')}
sheet=openpyxl.load_workbook(SOURCE,data_only=False)['套牌']
rows=[]
aliases={'严颜':'颜严','许褚':'许诸','刘晔':'刘烨','曹休':'八虎骑-曹修','江东之鼎':'江东之虎'}
for i,row in enumerate(sheet.iter_rows(values_only=True),1):
    if i==1 or not row[2]: continue
    faction,deck,name,quality,*_=row
    expected=[name,aliases.get(name),f'八虎骑-{name}',f'图纸-{name[:-2]}' if name.endswith('图纸') else f'套装-{name}']
    if name=='锻造锤(N-EX)': expected=['锻造锤base']
    candidates=[r['技能类型'] for r in tables[faction] if names.get(r['技能类型']) in expected]
    fallback=[aid for aid,n in names.items() if n in expected]
    ids=candidates or fallback
    rec={'row':i,'faction':faction,'deck':deck,'name':name,'quality':quality,'base':list(row[4:7]),'special':row[7],'swallow':row[8],'extra_k':row[10] if len(row)>10 else None,'ids':ids,'mapping':'table' if candidates else 'outside_table' if fallback else 'missing'}
    rows.append(rec)
all_ids=set(members)|{aid for r in rows for aid in r['ids']}
cards=[]; mods=set()
for aid in sorted(all_ids):
    obj=objects[aid]; ep=ROOT/f'ability/{aid}.json'; e=json.loads(ep.read_text('utf8')) if ep.exists() else {}
    nodes=list(walk(e)); mids={n['args_list'][1]['args_list'][0] for ptr,n,on in nodes if n.get('action_type')=='ADD_MODIFIER' and len(n.get('args_list',[]))>1 and n['args_list'][1].get('sub_type')==1}
    mids={m for m in mids if isinstance(m,int)}; mods.update(mids)
    cards.append({'id':aid,'name':names[aid],'cast':obj.get('ability_cast_type'),'desc':LANG.get(str(obj.get('description')),obj.get('description')),'kv':{k:v.get('value') for k,v in obj.get('kv',{}).items()},'table_membership':members[aid],'in_formal':aid in formal_ids,'eca_exists':ep.exists(),'eca_bytes':ep.stat().st_size if ep.exists() else 0,'events':dict(Counter(n['event_type'] for ptr,n,on in nodes if on and 'event_type' in n)),'actions':dict(Counter(str(n['action_type']) for ptr,n,on in nodes if on and 'action_type' in n)),'buffs':sorted(mids),'valid_false':[ptr for ptr,n,on in nodes if n.get('valid') is False],'sha256':hashlib.sha256(ep.read_bytes()).hexdigest() if ep.exists() else None})
    (OUT/f'ability-{aid}.txt').write_text(outline(e),encoding='utf8')
buffs=[]
for mid in sorted(mods):
    ep=ROOT/f'modifier/{mid}.json'; op=ROOT/f'editor_table/modifierall/{mid}.json'; e=json.loads(ep.read_text('utf8')) if ep.exists() else {}; obj=json.loads(op.read_text('utf8')) if op.exists() else {}
    buffs.append({'id':mid,'name':LANG.get(str(obj.get('name')),obj.get('name')),'kv':{k:v.get('value') for k,v in obj.get('kv',{}).items()},'cycle_time':obj.get('cycle_time'),'eca_exists':ep.exists(),'actions':dict(Counter(str(n['action_type']) for ptr,n,on in walk(e) if on and 'action_type' in n))})
    (OUT/f'modifier-{mid}.txt').write_text(outline(e),encoding='utf8')
result={'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'rows':rows,'cards':cards,'buffs':buffs,'formal_ids':sorted(formal_ids),'tables':tables}
(OUT/'inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print('ROWS',len(rows),'GROUPS',len({(r['faction'],r['deck']) for r in rows}),'FACTIONS',dict(Counter(r['faction'] for r in rows)))
print('MAPPING',dict(Counter(r['mapping'] for r in rows)))
print('MISSING',[(r['row'],r['faction'],r['deck'],r['name']) for r in rows if not r['ids']])
print('OUTSIDE_TABLE',[(r['row'],r['name'],r['ids']) for r in rows if r['mapping']=='outside_table'])
print('CARDS',len(cards),'ECA',sum(c['eca_exists'] for c in cards),'BUFFS',len(buffs),'FORMAL',len(formal_ids & all_ids))
for c in cards:
    print(c['id'],c['name'],'ECA',c['eca_bytes'],'BUFF',c['buffs'],'ACT',c['actions'],'DESC',re.sub('<[^>]+>','',str(c['desc'])))
