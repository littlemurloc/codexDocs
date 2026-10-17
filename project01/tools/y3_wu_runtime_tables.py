"""Wu card runtime records + one-time native-ECA attribute rule initialization."""
from __future__ import annotations
import copy,hashlib,json,uuid,zipfile
from pathlib import Path
import refactor_y3_wu_cards as r
b=r.b
WORK=Path(__file__).resolve().parents[1]/'tmp/wu-runtime-20261018'
STAGE=WORK/'staged'
RULES_KEY=b.PREFIX+'属性规则'
DIRTY=b.PREFIX+'待刷新'
FACTION='军略阵营'
IDENTITY='军略身份'
NAMES={**r.NAMES,11:'11_读取玩家持卡记录',12:'12_初始化军略属性规则',
       13:'13_追加一条属性规则',14:'14_持卡记录更新后刷新'}
FIDS={**r.FIDS,**{i:uuid.uuid5(uuid.NAMESPACE_URL,'project01/y3/wu/runtime/'+NAMES[i]).hex for i in (12,13,14)}}
EXTRA_TYPES={'TABLE':(100011,'VARIABLE',None),'UNIT_WRITE_ATTRIBUTE':(100042,2,'strength'),
             'ATTR_ELEMENT':(100300,2,'ATTR_BASE')}

def load(path):return json.loads(path.read_text('utf8'))
def rule_table(u):return b.n(100011,'GET_TABLE_KV',u,b.text(RULES_KEY))
def val_table(t,row,key,kind='ABILITY'):
    types={'ABILITY':(100014,'GET_ABILITY_TABLE_VAR_ND'),'UNIT_ENTITY':(100006,'GET_UNIT_ENTITY_TABLE_VAR_ND')}
    typ,sub=types[kind];return b.n(typ,sub,t,row,b.text(key))
def get_1d(t,row):return b.n(100014,'GET_ABILITY_TABLE_VAR_1D',t,row)
def set_1d(e,t,key,value):return e.action('SET_TABLE_VALUE_1D',t,key,value)
def traverse(e,t,actions):return e.action('TRAVERSE_TABLE_NEW',t,b.n(100022,1,*actions))
def ability_key(a):return b.n(100003,'ANY_VAR_TO_STR',b.n(100039,'ABILITY_NAME_OF_ABILITY',a))
def owned(e,a,u,pool,row,actions):
    # Each guard is nested: never dereference an absent/stale instance.
    return e.branch([e.exists(a)],[e.branch([e.compare(val_table(pool,row,'归属单位','UNIT_ENTITY'),'==',u,'UNIT_COMPARE')],[
        e.branch([e.cond('HAS_KV_ANY',a,b.text(FACTION))],[
            e.branch([e.compare(r.value(a,FACTION,'STRING'),'==',b.text('吴国'),'STRING_COMPARE')],actions)])])])
def finish(e,actions,payload):payload[f'{r.FOLDER}/{NAMES[e.index]}.json']=e.finish(actions)

def build_functions(rules):
    # Reuse the already reviewed unit lifecycle and conditional-damage functions.
    # Redirect their mapping reads to the carrier's runtime table.
    payload={};current=[None]
    oldclass,oldtable,oldtypes,oldnames,oldfids=r.Function,r.table,dict(r.TYPES),dict(r.NAMES),dict(r.FIDS)
    r.TYPES.update(EXTRA_TYPES);r.FIDS.update(FIDS);r.NAMES.update(NAMES)
    class Function(oldclass):
        def __init__(self,index,params,comment):
            current[0]=self
            if index==4:params=params+[('TABLE','属性规则表')]
            super().__init__(index,params,comment)
            self.obj.update(func_name=NAMES[index],trigger_name=NAMES[index])
    def dynamic_table(tid):
        if isinstance(tid,dict):return tid
        if tid==r.FIELD_TID:
            e=current[0]
            return e.var('TABLE','属性规则表') if e.index==4 else rule_table(e.var('UNIT_ENTITY','卡牌载体'))
        return oldtable(tid)
    try:
        r.Function=Function;r.table=dynamic_table
        old=r.functions()
        for index in (4,5,6,7,8,9,10):
            rel=f'{r.FOLDER}/{r.NAMES[index]}.json';payload[rel]=old[rel]
        # 11 obtains the existing per-player card instance records, without any card ID list.
        e=Function(11,[('UNIT_ENTITY','卡牌载体')],
            '返回现有玩家“卡牌技能池-表”。普通选卡与合成结果均复用其中的技能实例，不按技能类别反查。')
        u=e.var('UNIT_ENTITY','卡牌载体')
        idx=b.n(100002,'9384d061198e11ef967be8c829c05699',b.player(u),call_rt_index=0,op_arg=[],op_arg_enable=[])
        pool=b.n(100011,'VARIABLE',r.tp(['TABLE','卡牌技能池-表']),idx)
        finish(e,[e.ret('TABLE',pool)],payload)

        e=Function(13,[('TABLE','属性规则表'),('STRING','收益名称'),('STRING','参数键'),
            ('UNIT_WRITE_ATTRIBUTE','单位属性'),('ATTR_ELEMENT','计算方式'),('BOOLEAN','直接写入面板')],
            '初始化函数的公共行构造器：追加一条属性规则。这里不包含任何卡牌名单或数值。')
        t=e.var('TABLE','属性规则表');row=e.var('INTEGER','新增行号')
        actions=[e.set(row,b.n(100002,'INT_PLUS_ONE',b.n(100002,'GET_TABLE_LENGTH',t)))]
        for kind,name,column in [('STRING','收益名称','收益名称'),('STRING','参数键','参数键'),
             ('UNIT_WRITE_ATTRIBUTE','单位属性','单位属性'),('ATTR_ELEMENT','计算方式','属性计算方式'),
             ('BOOLEAN','直接写入面板','直接写入面板')]:
            actions.append(e.action('SET_TABLE_VALUE_ND',t,row,b.text(column),e.var(kind,name)))
        finish(e,actions,payload)

        e=Function(12,[('UNIT_ENTITY','卡牌载体')],
            '每个卡牌载体只初始化一次公共属性规则。新增卡沿用现有参数键即可；只有新增属性语义才需补充规则。')
        u=e.var('UNIT_ENTITY','卡牌载体');t=e.var('TABLE','属性规则表')
        grouped={False:[],True:[]}
        for rule in rules:
            grouped[rule['直接写入面板']].append(r.call(e,13,t,b.text(rule['收益名称']),b.text(rule['参数键']),
                b.lit(100042,rule['单位属性']),b.lit(100300,rule['属性计算方式']),r.flag(rule['直接写入面板'])))
        finish(e,[e.set(t,rule_table(u)),e.branch([e.exists(t)],[e.ret('TABLE',t)]),
            e.set(t,b.n(100011,'GET_NEW_TABLE')),
            r.section(e,'① 条件增伤参数：由函数 09 统一计算',grouped[False]),
            r.section(e,'② 直接面板属性：按属性键与计算方式应用',grouped[True]),
            e.setkv(u,RULES_KEY,t),e.ret('TABLE',t)],payload)

        e=Function(1,[('UNIT_ENTITY','卡牌载体'),('ABILITY','关联卡牌')],
            '先初始化运行时属性规则，再确保一个控制 Buff。获得事件早于持卡表写入，本函数只标记待刷新。')
        u=e.var('UNIT_ENTITY','卡牌载体');a=e.var('ABILITY','关联卡牌')
        finish(e,[r.call(e,12,u),e.setkv(u,DIRTY,r.flag(True)),
            e.branch([e.no(b.hasbuff(u,b.CONTROL))],[e.addbuff(u,b.CONTROL,u,a)])],payload)

        e=Function(14,[('UNIT_ENTITY','卡牌载体')],
            '普通选卡、合成写表结束后调用；等级变化和失去事件也可标记。仅有吴国控制 Buff 的载体会收到刷新。')
        u=e.var('UNIT_ENTITY','卡牌载体')
        finish(e,[e.branch([e.exists(u)],[e.branch([e.yes(b.hasbuff(u,b.CONTROL))],[
            e.setkv(u,DIRTY,r.flag(True)),e.send(u)])])],payload)

        e=Function(2,[('UNIT_ENTITY','卡牌载体'),('MODIFIER_ENTITY','控制Buff'),('BOOLEAN','强制阵型刷新')],
            '遍历已更新的玩家持卡记录，筛选有效吴国实例并按技能类型去重。记录可有空洞；不维护卡牌 ID 白名单。')
        u=e.var('UNIT_ENTITY','卡牌载体');m=e.var('MODIFIER_ENTITY','控制Buff');force=e.var('BOOLEAN','强制阵型刷新')
        pool=e.var('TABLE','玩家持卡记录');held=e.var('TABLE','本次有效卡牌');seen=e.var('TABLE','已统计类型')
        a=e.var('ABILITY','当前卡牌实例');key=e.var('STRING','当前技能标识');listing=e.var('STRING','本次持有清单')
        count=e.var('INTEGER','持有卡牌数');ur=e.var('INTEGER','持有UR数量');ex=e.var('BOOLEAN','持有EX')
        row=b.n(100002,'ITER_TABLE_KEY_INT')
        add=[set_1d(e,seen,key,r.flag(True)),e.set(count,b.n(100002,'INT_PLUS_ONE',count)),set_1d(e,held,count,a),
            e.set(listing,r.join(listing,r.join(key,b.text('；')))),
            e.branch([e.compare(r.value(a,IDENTITY,'STRING'),'==',b.text('UR组件'),'STRING_COMPARE')],
                [e.set(ur,b.n(100002,'INT_PLUS_ONE',ur))]),
            e.branch([e.compare(r.value(a,IDENTITY,'STRING'),'==',b.text('EX'),'STRING_COMPARE')],[e.set(ex,r.flag(True))])]
        scan=traverse(e,pool,[e.set(a,val_table(pool,row,'技能')),owned(e,a,u,pool,row,[
            e.set(key,ability_key(a)),e.branch([e.cond('TABLE_HAS_KEY',seen,key)],[],add)])])
        refresh=e.branch([e.cond('OR',e.compare(listing,'!=',r.value(m,r.APPLIED,'STRING'),'STRING_COMPARE'),
            e.yes(b.n(100001,'GET_BOOLEAN_KV',u,b.text(DIRTY))))],[r.call(e,3,u,m,listing,ur,ex,held)])
        finish(e,[e.set(pool,r.expr(11,'TABLE',u)),e.branch([e.exists(pool)],[
            r.section(e,'① 从现有持卡记录生成有效吴国实例快照',[
                e.set(held,b.n(100011,'GET_NEW_TABLE')),e.set(seen,b.n(100011,'GET_NEW_TABLE')),
                e.set(listing,b.text('')),e.set(count,r.i(0)),e.set(ur,r.i(0)),e.set(ex,r.flag(False)),scan,
                r.skv(e,m,r.COUNT,b.math(count,'+',b.f(0)))]),
            r.section(e,'② 持有变化或已标记时重新汇总',[refresh]),
            r.section(e,'③ 覆盖新队长、召唤和补兵',[r.call(e,5,u)]),
            r.section(e,'④ 开战时重新读取战前排位',[e.branch([e.yes(force)],[e.addkv(u,b.REV,b.f(1))])])])],payload)

        e=Function(3,[('UNIT_ENTITY','卡牌载体'),('MODIFIER_ENTITY','控制Buff'),('STRING','本次持有清单'),
            ('INTEGER','持有UR数量'),('BOOLEAN','持有EX'),('TABLE','有效卡牌实例表')],
            '按动态实例快照读取物编参数，整体提交。六 UR 且没有 EX 时使用原末阶 UR 规则，所有数值保持原样。')
        u=e.var('UNIT_ENTITY','卡牌载体');m=e.var('MODIFIER_ENTITY','控制Buff');listing=e.var('STRING','本次持有清单')
        ur=e.var('INTEGER','持有UR数量');ex=e.var('BOOLEAN','持有EX');held=e.var('TABLE','有效卡牌实例表')
        a=e.var('ABILITY','当前卡牌实例');ready=e.var('BOOLEAN','实例全部就绪');row=e.var('INTEGER','持卡行号')
        def submit(row):
            key=r.get(r.FIELD_TID,row,'参数键')
            return [r.skv(e,u,r.join(b.text(b.PREFIX),key),r.value(m,r.preview_key(key)))]
        finish(e,[r.section(e,'① 清空本次待提交收益',[e.set(ready,r.flag(True)),r.fields_loop(e,'清空参数行',
            lambda row:[r.skv(e,m,r.preview_key(r.get(r.FIELD_TID,row,'参数键')),b.f(0))])]),
            r.section(e,'② 遍历有效实例，读取每张卡的物编参数',[r.loop(e,row,held,[e.set(a,get_1d(held,row)),
                e.branch([e.exists(a)],[r.call(e,4,a,m,rule_table(u))],[e.set(ready,r.flag(False))])])]),
            r.section(e,'③ 原末阶规则：六 UR 且无 EX',[
                e.branch([e.compare(ur,'==',r.i(6)),e.no(ex)],[
                    r.addkv(e,m,'待提交_套牌吴国伤害',r.value(m,'末阶UR吴国伤害')),
                    r.addkv(e,m,'待提交_套牌后排伤害',r.value(m,'末阶UR后排伤害'))])]),
            r.section(e,'④ 快照有效才整体提交，并清除待刷新标记',[
                e.branch([e.yes(ready)],[r.fields_loop(e,'提交参数行',submit),e.setkv(m,r.APPLIED,listing),
                    e.setkv(u,DIRTY,r.flag(False)),e.addkv(u,b.REV,b.f(1))])])],payload)
    finally:
        r.Function=oldclass;r.table=oldtable;r.TYPES.clear();r.TYPES.update(oldtypes)
        r.NAMES.clear();r.NAMES.update(oldnames);r.FIDS.clear();r.FIDS.update(oldfids)
    return payload

def build_embedded(ids):
    payload={};b.TID=2099800000
    oldfids=dict(r.FIDS);r.FIDS.update(FIDS)
    try:
        for aid in ids:
            e=b.Eca(aid);u=b.unit('ABILITY_OWNER')
            e.trigger('获得卡牌：初始化规则并标记，等待持卡记录写入','ABILITY_OBTAIN',[r.call(e,1,u,b.ability())])
            e.trigger('等级变化：通知统一刷新','ABILITY_LEVEL_CHANGED',
                      [r.call(e,14,b.n(100006,'GET_ABILITY_OWNER',b.ability()))])
            e.trigger('失去卡牌：标记刷新，周期校验覆盖删除时序','ABILITY_LOSE',[r.call(e,14,u)])
            payload[f'ability/{aid}.json']=e.done()
        payload.update(r.modifiers())
        controller=payload[f'modifier/{b.CONTROL}.json']
        gain=next(t for t in controller['trigger_dict'].values() if t['event'][0]['event_type']=='OBTAIN_MODIFIER')
        gain['trigger_name']='获得控制：注册监听，等待选卡或合成写表完成'
        for node in b.walk(controller['trigger_group_info']):
            if node.get('__tuple__') and node.get('items',[None])[0]==gain['trigger_id']:
                node['items'][1]=gain['trigger_name']
        gain['action']=[a for a in gain['action'] if not (isinstance(a,dict) and a.get('action_type')=='CALL_TRIGGER_FUNC')]
        # Add a distinct element ID after the Eca.done() allocation.
        eid=max(n.get('element_id',0) for n in b.walk(controller))+1
        gain['action'].append({'action_type':'SET_ENTITY_KV','args_list':[b.buff(),b.text(r.COUNT),b.f(-1)],
                              'bp':False,'element_id':eid,'enable':True})
        for t in controller['trigger_dict'].values():
            if t['event'][0]['event_type']=='MODIFIER_CYCLE_TRIGGER':t['trigger_name']='周期兜底：检查持卡记录与新单位'
    finally:r.FIDS.clear();r.FIDS.update(oldfids)
    return payload

def stage():
    WORK.mkdir(parents=True,exist_ok=True);assert not (WORK/'published.json').exists()
    tables={}
    for p in (b.MAP/'tables').glob('*.json'):
        d=load(p)
        if d.get('tid') in (r.CARD_TID,r.FIELD_TID):tables[d['tid']]=(p,d)
    assert set(tables)=={r.CARD_TID,r.FIELD_TID}
    def rows(doc):
        data=doc['table_data']['data'];return [dict(zip(data[0],row)) for row in data[2:]]
    cards=rows(tables[r.CARD_TID][1]);rules=rows(tables[r.FIELD_TID][1]);assert len(cards)==31
    payload=build_functions(rules);payload.update(build_embedded([card['技能类型'] for card in cards]))
    for card in cards:
        aid=card['技能类型'];rel=f'editor_table/abilityall/{aid}.json';obj=b.read(rel)
        identity='EX' if card['EX结果'] else 'UR组件' if card['UR组件'] else '起始载体' if aid==b.BASE else '套牌结果' if card['合成结果'] else '普通组件'
        for key,value_ in [(FACTION,'吴国'),(IDENTITY,identity)]:
            assert key not in obj['kv'],'Review existing metadata before overwrite'
            obj['kv'][key]={'annotation':'吴国公共 ECA 分类','desc':'复制卡牌时按实际阵营与身份填写；不填数值',
                'etype':0,'key':key,'prop_cls':'PText','remark':'运行时收益筛选使用','show_in_attr':True,
                'sort':max((x.get('sort',0) for x in obj['kv'].values()),default=-1)+1,'type':0,'value':value_}
        payload[rel]=obj
    # Refresh only after existing pool writes and all existing selection/merge work.
    for filename in ['3选1军略卡牌处理.json','军略3选1-处理合成的新卡牌.json']:
        path=next((b.MAP/'global_trigger/function').rglob(filename));doc=load(path)
        u=copy.deepcopy(next(n for n in b.walk(doc) if n.get('arg_type')==100006 and n.get('sub_type')==11 and
            n.get('args_list') and isinstance(n['args_list'][0],dict) and n['args_list'][0].get('items',[None,None])[:2]==['UNIT_ENTITY','playerHeroList']))
        action={'action_type':'CALL_TRIGGER_FUNC','args_list':[b.n(100177,FIDS[14],u,op_arg=[],op_arg_enable=[])],
            'call_rt_arg_idxes':[],'bp':False,'element_id':max(n.get('element_id',0) for n in b.walk(doc))+1,'enable':True}
        at=len(doc['action'])-1 if doc['action'][-1].get('action_type')==400342 else len(doc['action'])
        doc['action'].insert(at,action);payload[str(path.relative_to(b.MAP)).replace('\\','/')]=doc
    index={NAMES[k]+'.json':k-1 for k in sorted(NAMES)};payload[r.FOLDER+'/index.txt']=index
    group=b.read('editor/tableeditorgroupinfo.json')
    def remove_refs(items):
        result=[]
        for item in items:
            if item.get('__tuple__') and item['items'][0] in (r.CARD_TID,r.FIELD_TID):continue
            item=copy.deepcopy(item)
            if 'group' in item:
                item['group']=remove_refs(item['group'])
                if not item['group'] and item.get('name')=='吴国军略':continue
            result.append(item)
        return result
    payload['editor/tableeditorgroupinfo.json']=remove_refs(group)
    removed=[str(p.relative_to(b.MAP)).replace('\\','/') for p,_ in tables.values()]
    removed.append(r.FOLDER+'/'+r.NAMES[11]+'.json')
    for rel in removed:payload[rel]=None
    manifest={}
    with zipfile.ZipFile(WORK/'before-runtime.zip','w',compression=zipfile.ZIP_DEFLATED) as backup:
        for rel,obj in payload.items():
            path=b.MAP/rel;before=path.read_bytes() if path.exists() else None
            if before is not None:backup.writestr(rel,before)
            after=None
            if obj is not None:
                target=STAGE/rel;target.parent.mkdir(parents=True,exist_ok=True)
                raw=(json.dumps(obj,ensure_ascii=True,indent=4)+'\n').encode('utf8');target.write_bytes(raw)
                after=hashlib.sha256(raw).hexdigest()
            manifest[rel]={'before':hashlib.sha256(before).hexdigest() if before is not None else None,'after':after}
    (WORK/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    (WORK/'attribute-rules.json').write_text(json.dumps(rules,ensure_ascii=False,indent=2),encoding='utf8')
    print('Staged',len(manifest),'paths;',len(rules),'runtime rules;',len(cards),'metadata migrations; removed',len(removed),'obsolete files.')

if __name__=='__main__':stage()
