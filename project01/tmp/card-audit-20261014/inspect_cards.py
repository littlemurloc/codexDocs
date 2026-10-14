from pathlib import Path
from collections import Counter
import json,re,hashlib

ROOT=Path(r'D:\littl\testTempFile\ProjectMonster02\maps\map3')
OUT=Path(__file__).resolve().parent
LANG=json.loads((ROOT/'zhlanguage.json').read_text('utf8'))
FUNCS={}
DOCS={}
TABLES={}
OBJECTS={}
for p in (ROOT/'tables').glob('*.json'):
    d=json.loads(p.read_text('utf8'));TABLES[d.get('tid')]=p.stem
for p in (ROOT/'global_trigger').rglob('*.json'):
    d=json.loads(p.read_text('utf8'));rel=p.relative_to(ROOT).as_posix();DOCS[rel]=d
    if d.get('func_id'):FUNCS[d['func_id']]=p.stem
for folder in ['abilityall','modifierall','editorunit','editoritem']:
    for p in (ROOT/'editor_table'/folder).glob('*.json'):
        d=json.loads(p.read_text('utf8'));OBJECTS.setdefault(d.get('key'),LANG.get(str(d.get('name')),d.get('name')))

def walk(v,ptr='',on=True):
    if isinstance(v,dict):
        # Configured child triggers commonly use enabled=false and REG_* registration.
        # Count their structural content; do not infer runtime reachability from this flag.
        dynamic=v.get('p_trigger_id') is not None or v.get('is_conf') is True
        on=on and v.get('enable',True) and (v.get('enabled',True) or dynamic)
        yield ptr,v,on
        for k,x in v.items():yield from walk(x,ptr+'/'+k,on)
    elif isinstance(v,list):
        for i,x in enumerate(v):yield from walk(x,ptr+'/'+str(i),on)

def expr(v,depth=0):
    if depth>14:return '...'
    if not isinstance(v,(dict,list)):
        if isinstance(v,str):return FUNCS.get(v,TABLES.get(v,json.dumps(v,ensure_ascii=False)))
        return str(v)
    if isinstance(v,list):return '['+', '.join(expr(x,depth+1) for x in v)+']'
    if v.get('__tuple__'):return ':'.join(map(str,v['items']))
    if 'condition_type' in v:return v['condition_type']+'('+', '.join(expr(x,depth+1) for x in v.get('args_list',[]))+')'
    typ=v.get('sub_type');args=v.get('args_list',[])
    if v.get('arg_type')==100022:return '{actions}'
    if typ in (1,11,14,'VARIABLE'):
        if len(args)==1:
            val=args[0]
            if v.get('arg_type') in [100039,100116,100115,100041] and isinstance(val,int):return f'{val}<{OBJECTS.get(val,"?")}>'
            return expr(val,depth+1)
        return ', '.join(expr(x,depth+1) for x in args)
    label=FUNCS.get(str(typ),str(typ))
    if v.get('call_rt_index',0):label+=f"[return {v['call_rt_index']}]"
    s=label+'('+', '.join(expr(x,depth+1) for x in args)+')'
    op=[expr(x,depth+1) for x,enabled in zip(v.get('op_arg',[]),v.get('op_arg_enable',[])) if enabled]
    return s+(' optional='+','.join(op) if op else '')

def outline(d):
    lines=[]
    for ptr,node,on in walk(d):
        if 'action_type' in node or 'event_type' in node:
            t=node.get('action_type',node.get('event_type'));args=node.get('args_list',[])
            op=[expr(x) for x,enabled in zip(node.get('op_arg',[]),node.get('op_arg_enable',[])) if enabled]
            lines.append(('ON ' if on else 'OFF ')+ptr+' '+str(t)+' '+', '.join(expr(x) for x in args)+(' OPTIONAL '+','.join(op) if op else ''))
        elif 'condition_type' in node:
            lines.append(('ON ' if on else 'OFF ')+ptr+' CONDITION '+expr(node))
    return '\n'.join(lines)

CARDDATA=json.loads((ROOT/'tables/军令卡牌技能表.json').read_text('utf8'))['table_data']['data']
CARDROWS=[r for r in CARDDATA[2:] if r[0] not in (None,'')]
FORMAL_IDS={r[1] for r in CARDROWS}
CARDROWS += [['independent',aid,'独立',0,'false','独立'] for aid in [134257459,134257119,134254774,134246929,134279853,134235884]]
CARDS=[]
for row in CARDROWS:
    aid=row[1];ab=json.loads((ROOT/f'editor_table/abilityall/{aid}.json').read_text('utf8'))
    ep=ROOT/f'ability/{aid}.json';eca=json.loads(ep.read_text('utf8')) if ep.exists() else {}
    triggers=eca.get('trigger_dict',{})
    acts=Counter(str(n['action_type']) for _,n,on in walk(eca) if on and 'action_type' in n)
    events=Counter(str(n['event_type']) for _,n,on in walk(eca) if on and 'event_type' in n)
    calls=sorted({FUNCS[n['sub_type']] for _,n,on in walk(eca) if on and n.get('sub_type') in FUNCS})
    mods=sorted({n['args_list'][1]['args_list'][0] for _,n,on in walk(eca) if on and n.get('action_type')=='ADD_MODIFIER' and n['args_list'][1].get('sub_type')==1 and isinstance(n['args_list'][1]['args_list'][0],int)})
    rec={'id':aid,'name':OBJECTS.get(aid),'set':row[5],'result':row[4],'in_formal_pool':aid in FORMAL_IDS,'cast':ab.get('ability_cast_type'),
         'desc':LANG.get(str(ab.get('description')),ab.get('description')),'kv':{k:v.get('value') for k,v in ab.get('kv',{}).items()},
         'triggers':[{'id':k,'name':v.get('trigger_name'),'valid':v.get('valid'),'enabled':v.get('enabled'),'actions':len(v.get('action',[]))} for k,v in triggers.items()],
         'actions':dict(acts),'events':dict(events),'calls':calls,'modifiers':mods,'bytes':ep.stat().st_size if ep.exists() else 0}
    CARDS.append(rec)
    (OUT/f'ability-{aid}.txt').write_text(outline(eca),encoding='utf8')
INDEX=[]
related_ids={r[1] for r in CARDROWS}
for rel,d in DOCS.items():
    nodes=list(walk(d));calls=sorted({FUNCS[n['sub_type']] for _,n,on in nodes if on and n.get('sub_type') in FUNCS})
    relevant=any(s in rel for s in ['军略','卡牌','universe01','universe02','universe03','AI行为_2','合法目标所在方阵编号','上中下路UI']) or any(any(s in c for s in ['军略','卡牌']) for c in calls)
    if relevant:
        digest=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
        rec={'path':rel,'name':Path(rel).stem,'func_id':d.get('func_id'),'enabled':d.get('enabled'),'valid':d.get('valid'),
             'events':[expr(n) if 'sub_type' in n else str(n.get('event_type')) for _,n,on in nodes if on and 'event_type' in n],
             'calls':calls,'sha256':digest}
        INDEX.append(rec)
        filename=Path(rel).stem+'.txt'
        (OUT/filename).write_text(outline(d),encoding='utf8')
GLOBAL=json.loads((ROOT/'globaltriggervariable.json').read_text('utf8'))
VARS={t:{k:v for k,v in vals.items() if any(s in k for s in ['军令','军略','卡牌','3选1','战斗阶段','军资','刷新'])} for t,vals in GLOBAL['variable_dict'].items()}
VARS={k:v for k,v in VARS.items() if v}
BUFFS=[]
for mid in sorted({m for c in CARDS for m in c['modifiers']}):
    p=ROOT/f'editor_table/modifierall/{mid}.json';d=json.loads(p.read_text('utf8')) if p.exists() else {}
    ep=ROOT/f'modifier/{mid}.json';eca=json.loads(ep.read_text('utf8')) if ep.exists() else {}
    (OUT/f'modifier-{mid}.txt').write_text(outline(eca),encoding='utf8')
    BUFFS.append({'id':mid,'name':LANG.get(str(d.get('name')),d.get('name')),'desc':LANG.get(str(d.get('description')),d.get('description')),
                  'kv':{k:v.get('value') for k,v in d.get('kv',{}).items()},'keys':{k:v for k,v in d.items() if 'attr' in k or 'stack' in k or 'time' in k},
                  'actions':dict(Counter(str(n['action_type']) for _,n,on in walk(eca) if on and 'action_type' in n)),
                  'invalid':[k for k,v in eca.get('trigger_dict',{}).items() if v.get('valid') is False]})
summary={'map':str(ROOT),'cards':CARDS,'buffs':BUFFS,'functions':INDEX,'variables':VARS}
(OUT/'inventory.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
print('CARD STATUS')
for c in CARDS:print(c['id'],c['name'],'triggers',c['triggers'],'events',c['events'],'actions',c['actions'],'mods',c['modifiers'])
print('FUNCTIONS')
for x in INDEX:print(x['name'],x['valid'],x['events'],x['calls'])
print('VARS',json.dumps(VARS,ensure_ascii=False)[:3500])
