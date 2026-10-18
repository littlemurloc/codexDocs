"""Guard map3 formation reads and hero auto-cast state reads.

The staged patch preserves existing combat formulae, cast conditions, timers,
IDs and payloads. Publication is explicit, hash checked and reversible. This
is the maintained builder for the new native-ECA helper; do not regenerate
historical hero templates over the patched live resources.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, os, uuid, zipfile
from pathlib import Path

MAP = Path('D:/littl/testTempFile/ProjectMonster02/maps/map3')
WORK = Path(__file__).resolve().parents[1] / 'tmp/combat-warning-fix-20261018'
STAGE = WORK / 'staged'
FUNCTION_FOLDER = 'global_trigger/function/new/功能执行'
NAME = '英雄主动技能-检查自动施法动作状态'
HELPER = f'{FUNCTION_FOLDER}/{NAME}.json'
INDEX = f'{FUNCTION_FOLDER}/index.txt'
FID = uuid.uuid5(uuid.NAMESPACE_URL, 'project01/y3/hero/autocast-action-guard/v1').hex
TID = 2099992001
UNIVERSE = 'global_trigger/trigger/关卡初始化内容/universe05.json'
DAMAGE_TID = '1404961588'
SELF_SLOT, HERO_SLOT = '站位判定_受伤单位阵位', '站位判定_所属英雄阵位'
TARGET, CAPTAIN = '站位判定_受伤单位', '站位判定_所属英雄'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def load(path): return json.loads(path.read_text('utf8'))
def encode(doc): return (json.dumps(doc, ensure_ascii=True, indent=4)+'\n').encode('utf8')
def walk(node, path=()):
    if isinstance(node, dict):
        yield path, node
        for k,v in node.items(): yield from walk(v, path+(k,))
    elif isinstance(node, list):
        for i,v in enumerate(node): yield from walk(v, path+(i,))
def at(doc, path):
    for k in path: doc=doc[k]
    return doc
def expr(typ, sub, *args, **extra):
    return dict(arg_type=typ, sub_type=sub, args_list=list(args), **extra)
def lit(typ, value): return expr(typ, 1, value)
def text(value): return lit(100003, value)
def var(kind, name):
    typ,sub={'UNIT_ENTITY':(100006,11),'ABILITY':(100014,2),'INTEGER':(100002,6),'BOOLEAN':(100001,'VARIABLE')}[kind]
    return expr(typ,sub,{'__tuple__':True,'items':[kind,name,'local']})
def declare(doc, kind, name):
    values,lengths,order=doc['var_data']
    assert name not in lengths, 'Variable already declared: '+name
    values.setdefault(kind,{})[name]=False if kind=='BOOLEAN' else 0;lengths[name]=0;order.append(name)
    return var(kind,name)

class Nodes:
    def __init__(self, used=()): self.serial=TID*1000000;self.used=set(used)
    def id(self):
        self.serial+=1
        assert self.serial not in self.used, 'New node ID collision'
        self.used.add(self.serial);return self.serial
    def action(self,kind,*args):
        x=dict(action_type=kind,args_list=list(args),element_id=self.id(),bp=False,enable=True)
        if kind=='IF_THEN_ELSE':x['fake_op']=[]
        return x
    def cond(self,kind,*args):
        return dict(condition_type=kind,args_list=list(args),element_id=self.id(),enable=True)
    def exists(self,u):return self.cond('TYPE_IS_EXIST',u)
    def compare(self,a,op,b,kind='BOOL_COMPARE'):
        return self.cond(kind,a,lit(100015 if kind=='FLOAT_COMPARE' else 100035,op),b)
    def branch(self,checks,actions,other=()):
        return self.action('IF_THEN_ELSE',expr(100021,1,*checks),expr(100022,1,*actions),expr(100022,1,*other))
    def set(self,v,value):return self.action('SET_VARIABLE',expr(100030,1,*copy.deepcopy(v['args_list'])),value)
    def ret(self,value):return self.action(400342,copy.deepcopy(value) if isinstance(value,dict) else lit(100001,value))
    def section(self,title,actions):
        return self.action('STORAGE_BOX',expr(100021,1),expr(100022,1,*actions),expr(100022,1),text(title))

def cast_compare(node):
    return node.get('condition_type')=='ABILITY_CAST_TYPE_COMPARE' and any(
        n.get('sub_type')=='GET_UNIT_CUR_RECORD_ABILITY' for _,n in walk(node))

def unsafe_auto_or(node):
    if node.get('condition_type')!='OR':return False
    checks=node.get('args_list',[{}])[0].get('args_list',[])
    return len(checks)==2 and checks[0].get('condition_type')=='BOOL_NOT' and (
        checks[0].get('args_list',[{}])[0].get('sub_type')=='UNIT_HAS_RUNNING_ABILITY') and cast_compare(checks[1])

def helper_call(owner):
    return expr(100001,FID,copy.deepcopy(owner),call_rt_index=0,op_arg=[],op_arg_enable=[])

def make_helper(n):
    # This same-map function supplies the observed function/return metadata.
    doc=load(MAP/'global_trigger/function/new/蜀国军略/11_读取玩家持卡记录.json')
    doc.update(action=[],condition=[],event=[],trigger_id=TID,func_id=FID,
       func_name=NAME,trigger_name=NAME,group_id=load(MAP/f'{FUNCTION_FOLDER}/是否锁定队伍行动状态.json')['group_id'],
       func_comment='每次先清零允许标记。确认单位存在后，未施法则允许；正在施法时仅在有效技能实例类型为原模板枚举1时允许。分支只更新标记，末尾统一设置一次返回值；返回值节点不当作提前退出。各技能冷却、阶段、自动施法标记和目标条件保持原样。',
       func_des='检查自动施法动作状态：施法单位{施法单位}',
       func_param_list=[{'__tuple__':True,'items':['施法单位',True]}],
       func_return=True,func_rtv_name_list=[{'__tuple__':True,'items':['允许自动施法','BOOLEAN']}],
       var_data=[{},{},[]],valid=True)
    owner=declare(doc,'UNIT_ENTITY','施法单位');current=declare(doc,'ABILITY','当前施法技能')
    allowed=declare(doc,'BOOLEAN','动作状态允许施法')
    doc['action']=[n.set(allowed,lit(100001,False)),n.branch([n.exists(owner)],[
        n.branch([n.compare(expr(100001,'UNIT_HAS_RUNNING_ABILITY',owner),'==',lit(100001,False))],
          [n.set(allowed,lit(100001,True))],[
            n.set(current,expr(100014,'GET_UNIT_CUR_RECORD_ABILITY',owner)),
            n.branch([n.exists(current)],[n.branch([
                n.compare(expr(100219,'GET_ABILITY_CAST_TYPE',current),'==',lit(100219,1),'ABILITY_CAST_TYPE_COMPARE')
            ],[n.set(allowed,lit(100001,True))])])
          ])
    ]),n.ret(allowed)]
    return doc

def patch_ability(doc):
    result=copy.deepcopy(doc);changes=[]
    for path,node in list(walk(result)):
        if not unsafe_auto_or(node):continue
        checks=node['args_list'][0]['args_list'];running=checks[0]['args_list'][0]
        owner=running['args_list'][0]
        comparison=checks[1]
        assert comparison['args_list'][1:]==[lit(100035,'=='),lit(100219,1)]
        assert comparison['args_list'][0]==expr(100219,'GET_ABILITY_CAST_TYPE',expr(100014,'GET_UNIT_CUR_RECORD_ABILITY',owner))
        # Retain the original condition node ID and all unrelated metadata.
        node['condition_type']='BOOL_COMPARE'
        node['args_list']=[helper_call(owner),lit(100035,'=='),lit(100001,True)]
        changes.append({'pointer':'/'+ '/'.join(map(str,path)),'path':list(path),'element_id':node['element_id']})
    return result,changes

def patch_formation(doc,n):
    result=copy.deepcopy(doc);trigger=result['sub_trigger'][DAMAGE_TID]
    block=trigger['action'][1]
    assert block['action_type']=='STORAGE_BOX' and block['args_list'][3]==text('站位伤害%加成')
    target=declare(trigger,'UNIT_ENTITY',TARGET);captain=declare(trigger,'UNIT_ENTITY',CAPTAIN)
    own=declare(trigger,'INTEGER',SELF_SLOT);hero=declare(trigger,'INTEGER',HERO_SLOT)
    changed={'self':0,'hero':0}
    for _,node in walk(block):
        if node.get('sub_type')!='GET_INTEGER_KV' or node.get('args_list',[None,None])[1]!=text('归属阵型编号'):continue
        source=node['args_list'][0]
        if source==expr(100006,'DAMAGE_TARGET_UNIT'): replacement=own;kind='self'
        else:
            assert source==expr(100006,'GET_UNIT_ENTITY_KV',expr(100006,'DAMAGE_TARGET_UNIT'),text('所属英雄'))
            replacement=hero;kind='hero'
        node.clear();node.update(copy.deepcopy(replacement));changed[kind]+=1
    assert changed=={'self':9,'hero':9},changed
    has=lambda unit,key:n.cond('HAS_KV_ANY',unit,text(key))
    readslot=lambda unit:expr(100002,'GET_INTEGER_KV',unit,text('归属阵型编号'))
    prepare=[n.set(target,expr(100006,'DAMAGE_TARGET_UNIT')),n.set(captain,expr(100006,'NONE_UNIT')),
      n.set(own,lit(100002,0)),n.set(hero,lit(100002,0)),
      n.branch([n.exists(target)],[
        n.branch([has(target,'归属阵型编号')],[n.set(own,readslot(target))]),
        n.branch([has(target,'所属英雄')],[
          n.set(captain,expr(100006,'GET_UNIT_ENTITY_KV',target,text('所属英雄'))),
          n.branch([n.exists(captain)],[n.branch([has(captain,'归属阵型编号')],[n.set(hero,readslot(captain))])])
        ])
      ])]
    block['args_list'][1]['args_list'].insert(1,n.section('① 安全读取本次受伤单位与所属英雄阵位；缺失时按0处理',prepare))
    return result,changed

def hero_inventory():
    folders=load(MAP/'editor/folderinfo/folderinfo_ability_all.json')
    lookup={str(x['items'][2]):x['items'] for x in folders['f']}
    language=load(MAP/'zhlanguage.json');rows=[]
    for oid,entry in folders['d'].items():
        folder=str(entry['items'][0]);info=lookup[folder]
        labels=[lookup[k][3] for k in (info[0]+'/'+folder).split('/') if k in lookup]
        if '英雄' not in labels:continue
        meta=load(MAP/'editor_table/abilityall'/f'{oid}.json')
        if meta.get('ability_cast_type')!=2:continue
        rows.append({'id':int(oid),'hero':labels[-1],'name':language.get(str(meta['name']),str(meta['name'])),
                     'path':f'ability/{oid}.json','metadata_sha256':sha((MAP/'editor_table/abilityall'/f'{oid}.json').read_bytes())})
    return sorted(rows,key=lambda x:x['id'])

def stage():
    assert not (WORK/'manifest.json').exists(),'Existing candidate must not be overwritten'
    assert not (MAP/HELPER).exists(),'Helper already exists; inspect instead of rerunning migration'
    rows=hero_inventory();used=set()
    for root in ['ability','modifier','global_trigger']:
        for p in (MAP/root).rglob('*.json'):
            d=load(p)
            for _,node in walk(d):
                if 'element_id' in node:used.add(node['element_id'])
                assert node.get('trigger_id')!=TID and node.get('func_id')!=FID
    n=Nodes(used);payload={};details={}
    for row in rows:
        original=load(MAP/row['path']);fixed,changes=patch_ability(original)
        row['fixed_conditions']=len(changes)
        if changes:payload[row['path']]=encode(fixed);details[row['path']]={'kind':'hero_autocast','changes':changes}
        else:assert not any(cast_compare(x) for _,x in walk(original)),row
    # Scan all ability ECA, including objects outside the hero folder.
    hero_paths={r['path'] for r in rows}
    for p in (MAP/'ability').glob('*.json'):
        if p.relative_to(MAP).as_posix() not in hero_paths:
            assert not any(unsafe_auto_or(x) for _,x in walk(load(p))), 'Same pattern outside requested hero scope: '+str(p)
    helper=make_helper(n);payload[HELPER]=encode(helper);details[HELPER]={'kind':'new_helper'}
    original=load(MAP/UNIVERSE);fixed,changes=patch_formation(original,n)
    payload[UNIVERSE]=encode(fixed);details[UNIVERSE]={'kind':'formation_guard','changes':changes}
    index=load(MAP/INDEX);assert NAME+'.json' not in index
    index[NAME+'.json']=max(index.values(),default=-1)+1
    payload[INDEX]=encode(index);details[INDEX]={'kind':'function_index'}
    WORK.mkdir(parents=True,exist_ok=True);manifest={}
    with zipfile.ZipFile(WORK/'before-warning-fix.zip','w',zipfile.ZIP_DEFLATED) as backup:
        for rel,after in payload.items():
            source=MAP/rel;raw=source.read_bytes() if source.exists() else None
            if raw is not None:backup.writestr(rel,raw)
            dest=STAGE/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(after)
            manifest[rel]={'before':sha(raw) if raw is not None else None,'after':sha(after),**details[rel]}
    protected={p.relative_to(MAP).as_posix():sha(p.read_bytes()) for p in MAP.rglob('*')
               if p.is_file() and p.suffix in ('.json','.txt','.lua') and p.relative_to(MAP).as_posix() not in manifest}
    (WORK/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    (WORK/'hero-active-audit.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
    (WORK/'protected-hashes.json').write_text(json.dumps(protected,ensure_ascii=False,indent=2),encoding='utf8')
    print(f'Staged {len(manifest)} files; audited {len(rows)} active skills; patched {sum(r["fixed_conditions"] for r in rows)} conditions.')

def publish(apply=False):
    assert MAP.resolve()==Path('D:/littl/testTempFile/ProjectMonster02/maps/map3').resolve()
    assert not (WORK/'published.json').exists(),'Already published'
    manifest=load(WORK/'manifest.json');protected=load(WORK/'protected-hashes.json')
    with zipfile.ZipFile(WORK/'before-warning-fix.zip') as backup:
        for rel,record in manifest.items():
            dest=(MAP/rel).resolve();assert MAP.resolve() in dest.parents
            assert (sha(dest.read_bytes()) if dest.exists() else None)==record['before'],'Concurrent edit: '+rel
            assert sha((STAGE/rel).read_bytes())==record['after'],'Candidate changed: '+rel
            if record['before'] is not None:assert sha(backup.read(rel))==record['before']
    for rel,digest in protected.items():assert sha((MAP/rel).read_bytes())==digest,'Protected changed before publish: '+rel
    print('Preflight passed:',len(manifest),'target files;',len(protected),'protected files.')
    if not apply:return
    done=[]
    try:
        for rel in manifest:
            dest=(MAP/rel).resolve();pending=dest.with_name(dest.name+'.codex-warning-pending')
            assert not pending.exists()
            try:pending.write_bytes((STAGE/rel).read_bytes());os.replace(pending,dest)
            finally:
                if pending.exists():pending.unlink()
            done.append(rel)
        for rel,row in manifest.items():assert sha((MAP/rel).read_bytes())==row['after']
        for rel,digest in protected.items():assert sha((MAP/rel).read_bytes())==digest,'Protected changed: '+rel
    except BaseException:
        with zipfile.ZipFile(WORK/'before-warning-fix.zip') as backup:
            for rel in reversed(done):
                if manifest[rel]['before'] is None:(MAP/rel).unlink()
                else:(MAP/rel).write_bytes(backup.read(rel))
        raise
    (WORK/'published.json').write_text(json.dumps({'map':str(MAP),'files':len(done),'editor_verified':False,'game_verified':False},indent=2),encoding='utf8')
    print('Published; all protected hashes unchanged.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['stage','publish']);parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if args.command=='stage':stage()
    else:publish(args.apply)
