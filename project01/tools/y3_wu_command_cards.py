"""Stage Wu command-card ECA against the observed map3 schemas; publish separately."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import zipfile

MAP = Path(r'D:\littl\testTempFile\ProjectMonster02\maps\map3')
WORK = Path(__file__).resolve().parents[1] / 'tmp/wu-cards-20261016'
STAGE = WORK / 'staged'
CATALOG = Path(__file__).resolve().parents[1] / 'tmp/deck-audit-20261016/inventory.json'
CONTROL, ARMY = 134285001, 134285002
CHANGE, PHASE = 2099456010, 1646669129
PREFIX = '吴国军略_'
SOURCE = PREFIX + '载体'
REV = PREFIX + '版本'
SIGNATURE = PREFIX + '签名'
SKILL_DAMAGE = '000B-7tIEfG4drFPxYCzSH'
UR = (134271490, 134223316, 134231639, 134238466, 134248984, 134272174)
EX = 134245355
BASE = 134250143
RESULTS = {134275559: (10, 0, 0), 134228375: (15, 0, 0),
           134273390: (20, 20, 0), 134269447: (25, 0, 0)}

FIELDS = {
    '力量': ('strength', 'ATTR_BASE'), '敏捷': ('agility', 'ATTR_BASE'),
    '智力': ('intelligence', 'ATTR_BASE'), '攻击力': ('attack_phy', 'ATTR_BASE'),
    '生命值': ('hp_max', 'ATTR_BASE'), '生命%': ('hp_max', 'ATTR_ALL_RATIO'),
    '攻速': ('attack_speed', 'ATTR_BASE'), '速度': ('ori_speed', 'ATTR_ALL_RATIO'),
    '暴击率': ('critical_chance', 'ATTR_BASE'), '暴击伤害': ('critical_dmg', 'ATTR_BASE'),
    '技能伤害': (SKILL_DAMAGE, 'ATTR_BASE'), '所有伤害': ('extra_dmg', 'ATTR_BASE'),
}
ALL_BASE = [('strength', 'ATTR_BASE'), ('agility', 'ATTR_BASE'), ('intelligence', 'ATTR_BASE')]
ALL_RATIO = [('strength', 'ATTR_ALL_RATIO'), ('agility', 'ATTR_ALL_RATIO'), ('intelligence', 'ATTR_ALL_RATIO')]
def field_key(attr, mode): return '属性_' + attr + '_' + mode
CONDITIONAL = ['单卡吴国伤害', '套牌吴国伤害', '套牌弓兵伤害', '套牌后排伤害', '终极弓兵后排伤害']

def read(relative): return json.loads((MAP / relative).read_text('utf8'))
def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values(): yield from walk(child)
    elif isinstance(value, list):
        for child in value: yield from walk(child)
def n(kind, subtype, *args, **extra):
    return dict(arg_type=kind, args_list=list(args), sub_type=subtype, **extra)
def lit(kind, value): return n(kind, 1, value)
def f(value): return lit(100000, float(value))
def text(value): return lit(100003, value)
def unit(kind): return n(100006, kind)
def ability(): return n(100014, 'CUR_ABILITY')
def buff(): return n(100076, 'CUR_MODIFIER')
def owner(): return unit('MODIFIER_OWNER')
def av(kind, name, subtype, category):
    return n(kind, subtype, {'__tuple__': True, 'items': [category, name, 'actor']})
def kv(entity, key): return n(100000, 'GET_FLOAT_KV', entity, text(key))
def ukv(entity, key): return n(100006, 'GET_UNIT_ENTITY_KV', entity, text(key))
def math(a, op, b): return n(100000, 'ARITHMETIC_OPERATION', a, lit(100017, op), b)
def player(u): return n(100025, 'OWNER_PLAYER', u)
def hascard(u, aid): return n(100001, 'CHECK_HAS_ABILITY_TYPE', u, lit(100039, aid))
def hasbuff(u, bid): return n(100001, 'UNIT_HAS_MODIFIER', u, lit(100046, bid))
def source(): return ukv(owner(), SOURCE)
def skill(u, aid):
    # Match the two existing grant paths: selections use category 2;
    # 军略3选1-处理合成的新卡牌 grants merge results in category 3.
    category = 3 if aid in RESULTS or aid in (BASE, EX) else 2
    return n(100014, 'GET_ABILITY_BY_AID', u, lit(100182, category), lit(100039, aid))
def attr(u, key): return n(100000, 'GET_UNIT_ATTR', u, lit(100301, 'ATTR_RESULT'), lit(100042, key))
def captains(u):
    return n(100026, '6570be50be1a11f1916d7b0e2885c54e', player(u),
             lit(100001, False), text('所有队长'), call_rt_index=0, op_arg=[], op_arg_enable=[])

TID = 2099600000
class Eca:
    def __init__(self, oid, modifier=False):
        self.oid, self.modifier, self.serial = oid, modifier, oid * 1000000
        template = read('ability/134284020.json')
        self.obj = {k: copy.deepcopy(v) for k, v in template.items() if k not in
                    ('trigger_dict', 'local_variable', 'trigger_group_info', 'variable_dict',
                     'variable_group_info', 'variable_length_dict')}
        self.obj.update(trigger_dict={}, local_variable={}, trigger_group_info=[],
                        variable_dict={}, variable_group_info=[], variable_length_dict={})
    def id(self): self.serial += 1; return self.serial
    def action(self, kind, *args):
        node = dict(action_type=kind, args_list=list(args), bp=False, element_id=self.id(), enable=True)
        if kind == 'IF_THEN_ELSE': node['fake_op'] = []
        return node
    def cond(self, kind, *args):
        if kind in ('OR','AND'):args=(n(100021,1,*args),)
        return dict(condition_type=kind, args_list=list(args), element_id=self.id(), enable=True)
    def compare(self, a, op, b, kind='FLOAT_COMPARE'):
        return self.cond(kind, a, lit(100015 if kind == 'FLOAT_COMPARE' else 100035, op), b)
    def yes(self, predicate): return self.compare(predicate, '==', lit(100001, True), 'BOOL_COMPARE')
    def no(self, predicate): return self.compare(predicate, '==', lit(100001, False), 'BOOL_COMPARE')
    def exists(self, u): return self.cond('TYPE_IS_EXIST', u)
    def alive(self, u): return self.cond('IS_UNIT_ALIVE', u)
    def branch(self, checks, actions, otherwise=()):
        return self.action('IF_THEN_ELSE', n(100021, 1, *checks),
                           n(100022, 1, *actions), n(100022, 1, *otherwise))
    def setkv(self, entity, key, val): return self.action('SET_ENTITY_KV', entity, text(key), val)
    def addkv(self, entity, key, val): return self.setkv(entity, key, math(kv(entity, key), '+', val))
    def pick(self, group, actions): return self.action('PICK_UNIT_DO_ACTION', group, n(100022, 1, *actions))
    def setvar(self, category, name, value):
        return self.action('SET_VARIABLE', av(100030, name, 1, category), value)
    def var(self, category, name, value):
        self.obj['variable_dict'].setdefault(category, {})[name] = value
        self.obj['variable_length_dict'][name] = 0
        self.obj['variable_group_info'].append({'__tuple__': True, 'items': [name, name]})
    def trigger(self, name, event, actions=(), args=(), conditions=(), parent=None, handle=None):
        global TID
        TID += 1; tid = TID
        t = dict(action=list(actions), call_enabled=True, condition=list(conditions),
                 enabled=parent is None, event=[dict(args_list=list(args), element_id=self.id(),
                 enable=True, event_type=event)], group_id=self.oid, p_trigger_id=parent,
                 trigger_id=tid, trigger_name=name, valid=True, var_data=[{}, {}, []])
        if parent is not None:
            t['is_conf'] = True
            self.var('DYNAMIC_TRIGGER_INSTANCE', handle, 0)
            t['sub_trigger_owner_set_var_action'] = self.action('SET_VARIABLE',
                av(100178, handle, 'VARIABLE', 'DYNAMIC_TRIGGER_INSTANCE'),
                n(100178, 'REG_MODIFIER_TRIGGER' if self.modifier else 'REG_ABILITY_TRIGGER',
                  lit(100069 if self.modifier else 100068, tid)))
        self.obj['trigger_dict'][str(tid)] = t
        self.obj['local_variable'][str(tid)] = dict(variable_dict={}, variable_length_dict={})
        return tid
    def unreg(self, handle):
        return self.action('UNREG_TRIGGER', av(100178, handle, 'VARIABLE', 'DYNAMIC_TRIGGER_INSTANCE'))
    def addbuff(self, u, bid, releaser, linked=None):
        node = self.action('ADD_MODIFIER', u, lit(100046, bid))
        node.update(op_arg=[releaser, linked, None, None, None, None],
                    op_arg_enable=[True, linked is not None, False, False, False, False])
        return node
    def send(self, u): return self.action('SEND_CUSTOM_EVENT', lit(100238, CHANGE), u)
    def done(self):
        roots = [dict(__tuple__=True, items=[int(k), t['trigger_name']])
                 for k,t in self.obj['trigger_dict'].items() if t.get('p_trigger_id') is None]
        children = [dict(__tuple__=True, items=[int(k), t['trigger_name']])
                    for k,t in self.obj['trigger_dict'].items() if t.get('p_trigger_id') is not None]
        self.obj['trigger_group_info'] = [dict(_trigger_group_=True, key=self.oid,
                                             name=str(self.oid), group=roots)] + children
        # Branch fragments are reused while building. JSON round-trip separates those
        # copies before assigning unique UI node identities to the final graph.
        self.obj=json.loads(json.dumps(self.obj))
        self.serial=self.oid*1000000
        for node in walk(self.obj):
            if 'element_id' in node:node['element_id']=self.id()
        return self.obj

def parse_base(values):
    out = {}
    for value in values:
        if value in (None, '', '-'): continue
        name, value = value.split('+', 1)
        value = float(value.rstrip('%'))
        pairs = ALL_BASE if name == '全属性' else ALL_RATIO if name == '全属性%' else [FIELDS[name]]
        for attr_, mode in pairs:
            key = field_key(attr_, mode); out[key] = out.get(key, 0) + value
    return out

def load_specs():
    data = json.loads(CATALOG.read_text('utf8'))
    if hashlib.sha256(Path(data['source']).read_bytes()).hexdigest()!=data['source_sha256']:
        raise ValueError('Workbook changed since the audited row mapping; re-read before staging')
    specs = {r['技能类型']:dict(id=r['技能类型'],name=next(c['name'] for c in data['cards'] if c['id']==r['技能类型']),
             params={},description='吴国军略起始载体；沿用原进阶路线。',row=None)
             for r in data['tables']['吴国']}
    for row in data['rows']:
        if row['faction'] != '吴国': continue
        assert len(row['ids']) == 1
        aid = row['ids'][0]
        spec = specs[aid]; spec['params'].update(parse_base(row['base'])); spec['row']=row['row']
        descriptions = [x for x in row['base'] if x not in (None,'','-')]
        if row['special'] not in (None,'','-'):
            value = float(re.search(r'伤害\+(\d+)%',row['special']).group(1))
            spec['params']['单卡吴国伤害'] = value
            descriptions.append(row['special'])
        if aid == EX:
            spec['params'].update(套牌吴国伤害=60.,终极弓兵后排伤害=50.)
            descriptions.append('终极：吴国角色伤害+60%，全军弓兵或战前后排单位伤害+50%，同时符合两类仅加一次。本卡另有吴国被动+30%。')
        spec['description']='；'.join(descriptions)
    for aid, values in RESULTS.items():
        p = specs[aid]['params']
        p.update({k:float(v) for k,v in zip(CONDITIONAL[1:4],values) if v})
        specs[aid]['description'] = f'吞噬收益：吴国角色伤害+{values[0]}%'+('；全军弓兵伤害+20%' if values[1] else '')+'。已取得的早期套牌收益保留。'
    return specs

def ability_eca(aid):
    e=Eca(aid); u=unit('ABILITY_OWNER')
    ensure=e.branch([e.no(hasbuff(u,CONTROL))], [e.addbuff(u,CONTROL,u,ability())])
    e.trigger('获得卡牌：建立吴国收益控制并刷新', 'ABILITY_OBTAIN',[ensure,e.send(u)])
    e.trigger('等级变化：刷新配置，避免重复叠加', 'ABILITY_LEVEL_CHANGED',
              [e.send(n(100006,'GET_ABILITY_OWNER',ability()))])
    e.trigger('失去卡牌：刷新；周期校验覆盖失去事件时序', 'ABILITY_LOSE',[e.send(u)])
    return e.done()

def controller_eca(specs):
    e=Eca(CONTROL,True)
    e.var('FLOAT','新签名',0.)
    allfields=sorted({k for spec in specs.values() for k in spec['params']}|set(CONDITIONAL))
    signature=av(100000,'新签名',2,'FLOAT')
    scan=[e.setvar('FLOAT','新签名',f(0))]
    for index,aid in enumerate(sorted(specs)):
        scan += [e.setkv(buff(),f'拥有_{aid}',f(0)),e.branch([e.yes(hascard(owner(),aid))],[e.setkv(buff(),f'拥有_{aid}',f(1)),
                 e.setvar('FLOAT','新签名',math(signature,'+',f(2**index)))])]
    recompute=[e.setkv(owner(),PREFIX+k,f(0)) for k in allfields]
    for aid,spec in sorted(specs.items()):
        if spec['params']:
            recompute.append(e.branch([e.compare(kv(buff(),f'拥有_{aid}'),'==',f(1))],
                [e.addkv(owner(),PREFIX+k,kv(skill(owner(),aid),k)) for k in spec['params']]))
    # UR completion and the EX terminal result are alternatives at this tier.
    recompute.append(e.branch([e.compare(kv(buff(),f'拥有_{i}'),'==',f(1)) for i in UR]+
                             [e.compare(kv(buff(),f'拥有_{EX}'),'==',f(0))],
        [e.addkv(owner(),PREFIX+'套牌吴国伤害',kv(buff(),'末阶UR吴国伤害')),
         e.addkv(owner(),PREFIX+'套牌后排伤害',kv(buff(),'末阶UR后排伤害'))]))
    recompute += [e.setkv(buff(),SIGNATURE,signature),e.addkv(owner(),REV,f(1))]
    scan.append(e.branch([e.compare(signature,'!=',kv(buff(),SIGNATURE))],recompute))
    selected=unit('FOR_EACH_SELECTED_UNIT')
    def apply():
        return e.branch([e.alive(selected)], [e.setkv(selected,SOURCE,owner()),
            e.branch([e.no(hasbuff(selected,ARMY))],[e.addbuff(selected,ARMY,owner())])])
    # The nested selector evaluates its group before changing the current selected unit.
    gather=e.pick(captains(owner()),[apply(),e.pick(n(100026,'GET_UNIT_GROUP_KV',selected,text('带领小队')),[apply()])])
    gain=e.trigger('获得控制：计算配置并为全军建立收益 Buff','OBTAIN_MODIFIER')
    change=e.trigger('卡牌配置变化：重新聚合并覆盖新单位','RECEIVE_CUSTOM_EVENT',scan+[gather],
        args=[lit(100238,CHANGE)],conditions=[e.compare(n(100006,'GET_CUS_EVENT_PARAM',lit(100240,'载体单位')),'==',owner(),'UNIT_COMPARE')],
        parent=gain,handle='配置刷新监听')
    phase=e.trigger('开战：重读配置及强制刷新战前阵型分类','RECEIVE_CUSTOM_EVENT',scan+[gather,e.addkv(owner(),REV,f(1))],
        args=[lit(100238,PHASE)],conditions=[e.compare(n(100002,'GET_CUS_EVENT_PARAM',lit(100240,'阶段编号')),'==',lit(100002,2))],
        parent=gain,handle='开战监听')
    e.obj['trigger_dict'][str(gain)]['action']=[e.setkv(buff(),SIGNATURE,f(-1)),change,phase]+copy.deepcopy(scan)+[copy.deepcopy(gather)]
    e.trigger('周期校验：获取/失去卡牌、召唤及补兵兜底','MODIFIER_CYCLE_TRIGGER',scan+[gather,
        e.branch([e.compare(signature,'==',f(0))],[e.action('REMOVE_BUFF_INS',buff())])])
    e.trigger('失去控制：注销监听并清除本控制器缓存','LOSS_MODIFIER',
        [e.unreg('配置刷新监听'),e.unreg('开战监听')]+[e.setkv(owner(),PREFIX+k,f(0)) for k in allfields]+[e.addkv(owner(),REV,f(1))])
    return e.done()

def army_eca(specs):
    e=Eca(ARMY,True)
    for category,name,value in [('UNIT_ENTITY','编队队长',0),('FLOAT','本次额外伤害',0.),('FLOAT','原生命比例',0.)]:e.var(category,name,value)
    captain=av(100006,'编队队长',11,'UNIT_ENTITY')
    damage=av(100000,'本次额外伤害',2,'FLOAT')
    hp_ratio=av(100000,'原生命比例',2,'FLOAT')
    allfields=sorted({k for spec in specs.values() for k in spec['params'] if k.startswith('属性_')})
    rebuild=[e.setvar('FLOAT','原生命比例',math(n(100000,'GET_HP_CUR',owner()),'/',attr(owner(),'hp_max'))),
             e.setvar('UNIT_ENTITY','编队队长',owner()),
             e.branch([e.exists(ukv(owner(),'所属英雄'))],[e.setvar('UNIT_ENTITY','编队队长',ukv(owner(),'所属英雄'))])]
    for key in allfields:
        attr_,mode=key[len('属性_'):].split('_ATTR_',1);mode='ATTR_'+mode
        if attr_=='extra_dmg':continue
        rebuild.append(e.action('SET_MODIFIER_OWNER_ATTR',buff(),lit(100042,attr_),lit(100300,mode),kv(source(),PREFIX+key)))
    rebuild += [e.setvar('FLOAT','本次额外伤害',kv(source(),PREFIX+field_key('extra_dmg','ATTR_BASE'))),
        e.branch([e.cond('OR',e.cond('UNIT_HAS_TAG',owner(),text('吴国')),e.cond('UNIT_HAS_TAG',captain,text('吴国')))],
            [e.setvar('FLOAT','本次额外伤害',math(damage,'+',math(kv(source(),PREFIX+'单卡吴国伤害'),'+',kv(source(),PREFIX+'套牌吴国伤害'))))]),
        e.branch([e.cond('UNIT_HAS_TAG',owner(),text('弓兵'))],
            [e.setvar('FLOAT','本次额外伤害',math(damage,'+',kv(source(),PREFIX+'套牌弓兵伤害')))]),
        e.branch([e.cond('OR',*[e.compare(n(100002,'GET_INTEGER_KV',captain,text('归属阵型编号')),'==',lit(100002,i)) for i in [7,8,9]])],
            [e.setvar('FLOAT','本次额外伤害',math(damage,'+',kv(source(),PREFIX+'套牌后排伤害')))]),
        e.branch([e.cond('OR',e.cond('UNIT_HAS_TAG',owner(),text('弓兵')),
                  *[e.compare(n(100002,'GET_INTEGER_KV',captain,text('归属阵型编号')),'==',lit(100002,i)) for i in [7,8,9]])],
            [e.setvar('FLOAT','本次额外伤害',math(damage,'+',kv(source(),PREFIX+'终极弓兵后排伤害')))]),
        e.action('SET_MODIFIER_OWNER_ATTR',buff(),lit(100042,'extra_dmg'),lit(100300,'ATTR_BASE'),damage),
        e.action('ADD_CUR_HP',owner(),math(math(attr(owner(),'hp_max'),'*',hp_ratio),'-',n(100000,'GET_HP_CUR',owner()))),
        e.setkv(buff(),REV,kv(source(),REV))]
    valid=[e.exists(source()),e.yes(hasbuff(source(),CONTROL))]
    guard=e.branch(valid,[e.branch([e.compare(kv(buff(),REV),'!=',kv(source(),REV))],rebuild)],
                   [e.action('REMOVE_BUFF_INS',buff())])
    gain=e.trigger('获得收益：按所属玩家配置重算一次','OBTAIN_MODIFIER')
    change=e.trigger('配置变化：刷新自身收益','RECEIVE_CUSTOM_EVENT',
        [e.setkv(buff(),REV,f(-1)),copy.deepcopy(guard)],args=[lit(100238,CHANGE)],
        conditions=[e.compare(n(100006,'GET_CUS_EVENT_PARAM',lit(100240,'载体单位')),'==',source(),'UNIT_COMPARE')],
        parent=gain,handle='配置刷新监听')
    e.obj['trigger_dict'][str(gain)]['action']=[e.setkv(buff(),REV,f(-1)),change,copy.deepcopy(guard)]
    e.trigger('配置版本变化/来源丢失兜底','MODIFIER_CYCLE_TRIGGER',[guard])
    e.trigger('失去收益：清除自身属性贡献并注销监听','LOSS_MODIFIER',
              [e.action('CLEAR_MODIFIER_OWNER_ATTR',buff()),e.unreg('配置刷新监听')])
    return e.done()

def stage():
    global TID
    TID=2099600000
    WORK.mkdir(parents=True,exist_ok=True)
    if (WORK/'published.json').exists(): raise RuntimeError('Already published; do not regenerate against changed source')
    for oid in (CONTROL,ARMY):
        for kind in ['editor_table/modifierall','modifier','editor_table/abilityall','ability']:
            if (MAP/f'{kind}/{oid}.json').exists():raise ValueError(f'Object ID occupied: {oid}')
    specs=load_specs()
    payload={}
    language=read('zhlanguage.json'); langkey=1916000000
    def string(value):
        nonlocal langkey
        while str(langkey) in language:langkey+=1
        key=langkey; language[str(key)]=value; langkey+=1; return key
    def params(values):
        return {k:dict(annotation='',desc='',etype=2,key=k,prop_cls='PFloat',remark='',show_in_attr=True,sort=i,type=1,value=float(v))
                for i,(k,v) in enumerate(values.items())}
    for aid,spec in sorted(specs.items()):
        obj=read(f'editor_table/abilityall/{aid}.json')
        if (MAP/f'ability/{aid}.json').exists():raise ValueError(f'Unexpected live Wu ECA: {aid}; review before replacing')
        description=spec['description']+'；基础属性作用于己方队长及其小兵；伤害按来源阵营、兵种与战前阵型判断。'
        key=string('<html><body><p>'+description+'</p></body></html>')
        obj['description']=key;obj['desc']=key; obj['kv'].update(params(spec['params']))
        payload[f'editor_table/abilityall/{aid}.json']=obj
        payload[f'ability/{aid}.json']=ability_eca(aid)
    for oid,name,cycle,eca in [(CONTROL,'吴国军略·全军配置控制',.5,controller_eca(specs)),(ARMY,'吴国军略·单位收益',.1,army_eca(specs))]:
        obj=read('editor_table/modifierall/134226306.json')
        nk=string(name);dk=string('吴国军略专用共用被动；按所属卡牌重新计算，重复刷新不叠加。')
        obj.update(_ref_=oid,key=oid,uid=str(oid),name=nk,desc=dk,description=dk,suffix='吴国军略',
            cycle_time=cycle,disappear_when_dead=oid!=CONTROL,show_on_ui=False,get_effect_list=[],lose_effect_list={'__tuple__':True,'items':[]},
            kv=params({'末阶UR吴国伤害':40.,'末阶UR后排伤害':30.}) if oid==CONTROL else {})
        payload[f'editor_table/modifierall/{oid}.json']=obj; payload[f'modifier/{oid}.json']=eca
    folder=read('editor/folderinfo/folderinfo_modifier_all.json')
    templateid=folder['d']['134226306']['items'][0]
    parent=next(v['items'] for v in folder['f'] if v['items'][2]==templateid)
    folderid='wucardmod20261016'
    if any(v['items'][2]==folderid for v in folder['f']):raise ValueError('Wu folder already exists')
    order=max((v['items'][1] for v in folder['f'] if v['items'][0]==parent[0]),default=-1)+1
    folder['f'].append({'__tuple__':True,'items':[parent[0],order,folderid,'吴国军略']})
    for i,oid in enumerate((CONTROL,ARMY)):folder['d'][str(oid)]={'__tuple__':True,'items':[folderid,i]}
    payload['editor/folderinfo/folderinfo_modifier_all.json']=folder
    custom=read('customevent.json')
    if str(CHANGE) in custom['conf']:raise ValueError('Custom event occupied')
    custom['conf'][str(CHANGE)]=[['载体单位',100006]]
    custom['group_info'].append({'__tuple__':True,'items':[CHANGE,'吴国军略配置刷新']})
    payload['customevent.json']=custom
    desc=read('tables/技能作用描述表.json');data=desc['table_data']['data'];width=len(data[0])
    assert not any(len(row)>1 and row[1] in specs for row in data[2:]),'Unexpected existing Wu descriptions'
    count=max(int(row[0]) for row in data[2:] if row and str(row[0]).isdigit())
    for aid,spec in sorted(specs.items()):
        count+=1;data.append(([str(count),aid,'被动']+[spec['description']]*11+['']*width)[:width])
    payload['tables/技能作用描述表.json']=desc
    payload['zhlanguage.json']=language
    manifest={}
    with zipfile.ZipFile(WORK/'before-wu-cards.zip','w',compression=zipfile.ZIP_DEFLATED) as backup:
        for rel,obj in payload.items():
            path=MAP/rel;before=path.read_bytes() if path.exists() else None
            if before is not None:backup.writestr(rel,before)
            target=STAGE/rel;target.parent.mkdir(parents=True,exist_ok=True)
            content=(json.dumps(obj,ensure_ascii=True,indent=4)+'\n').encode()
            target.write_bytes(content)
            manifest[rel]={'before':hashlib.sha256(before).hexdigest() if before else None,'after':hashlib.sha256(content).hexdigest()}
    (WORK/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    (WORK/'specs.json').write_text(json.dumps(specs,ensure_ascii=False,indent=2),encoding='utf8')
    print('Staged',len(payload),'files;',len(specs),'Wu abilities, 2 Buffs; formal pool and other factions untouched')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['stage'])
    args=parser.parse_args();stage()
