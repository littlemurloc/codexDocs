"""Stage readable Shu native ECA; publication is a separate hash-checked step.

Shared lifecycle primitives are reused from the reviewed Wu generator. No Wu
files are changed. Card values come from the workbook and live object metadata.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, uuid, zipfile
from pathlib import Path
import y3_wu_runtime_tables as d
r, b = d.r, d.b
MAP = b.MAP
WORK = Path(__file__).resolve().parents[1] / 'tmp/shu-cards-20261018'
STAGE = WORK / 'staged'
BOOK = Path('C:/Users/littl/Downloads/羁绊.xlsx')
BOOK_SHA = '8c30dc97a60d094fec55e727405dc9feed118e2aa6ea9eb4a2ff03f9caecc46d'
CONTROL, ARMY = 134285101, 134285102
LIUBEI, TAOYUAN_GUAN, TAOYUAN_ZHANG, TAOYUAN, EX = range(134285111, 134285116)
BASE = 134219992
PREFIX = '蜀国军略_'
SOURCE, REV, DIRTY, RULES = (PREFIX+x for x in ('载体','版本','待刷新','属性规则'))
CHANGE, PHASE = 2099456110, b.PHASE
FOLDER = 'global_trigger/function/new/蜀国军略'
NAMES = {**{k:v.replace('吴国','蜀国') for k,v in d.NAMES.items()},
 9:'09_计算阵营兵种与前后排增伤',15:'15_每波声望与品质升级',
 16:'16_结算本单位击杀收益',17:'17_发放首次获得金币',18:'18_检查六套牌并授予终极刘备'}
FIDS = {k:uuid.uuid5(uuid.NAMESPACE_URL,'project01/y3/shu/'+v).hex for k,v in NAMES.items()}
UPGRADE = 'd1b22d80a43a11f1a42a8d8a8b994251'
MERGE = 'e4a62a69b3db11f191048b7bdf2d7282'
RESULTS = {134266951:('蜀汉宿将',15),134247565:('先主旧臣',10),
           134251758:('二代英杰',20),134283217:('五虎上将',30),
           134257279:('蜀汉谋臣',25),TAOYUAN:('桃园结义',25)}
MECHANICS = ['单卡蜀国伤害','套牌蜀国伤害','套牌前排伤害','套牌后排伤害',
 '套牌骑兵伤害','终极骑枪伤害','每波固定声望','每波随机声望下限','每波随机声望上限',
 '每波升级概率','击杀回蓝百分比','击杀成长攻击']
TYPES = {**r.TYPES,**d.EXTRA_TYPES,'PLAYER':(100025,'VARIABLE',0)}

def sha(raw): return hashlib.sha256(raw).hexdigest()
def read(rel): return json.loads((MAP/rel).read_text('utf8'))
def value(entity,key,kind='FLOAT'): return r.value(entity,key,kind)
def rule_table(u): return b.n(100011,'GET_TABLE_KV',u,b.text(RULES))
def expr(index,kind,*args): return b.n(TYPES[kind][0],FIDS[index],*args,call_rt_index=0,op_arg=[],op_arg_enable=[])
def foreign(fid,kind,*args): return b.n(TYPES[kind][0],fid,*args,call_rt_index=0,op_arg=[],op_arg_enable=[])
def call(e,index,*args): return external(e,FIDS[index],*args)
def external(e,fid,*args):
    a=e.action('CALL_TRIGGER_FUNC',b.n(100177,fid,*args,op_arg=[],op_arg_enable=[]));a['call_rt_arg_idxes']=[];return a
def wave(): return b.n(100002,6,r.tp(['INTEGER','当前进程所在波次编号']))
def integer(entity,key): return b.n(100002,'GET_INTEGER_KV',entity,b.text(key))
def imath(a,op,c): return b.n(100002,'MATH_OPERATION',a,b.lit(100016,op),c)
def level(a): return b.n(100002,'GET_ABILITY_INT_ATTR',a,b.lit(100079,'ability_level'))

class Function(r.Function):
    def __init__(self,index,params,comment):
        self.index=index;self.oid=2099851000+index;self.serial=self.oid*1000000;self.modifier=False
        self.obj=read('global_trigger/function/业务逻辑/功能执行/单位移除技能.json')
        self.obj.update(action=[],condition=[],event=[],func_id=FIDS[index],func_name=NAMES[index],
          trigger_name=NAMES[index],trigger_id=self.oid,group_id='shu_cards_20261018',func_comment=comment,
          func_des=NAMES[index]+'：'+ '，'.join(name+'{'+name+'}' for _,name in params),
          func_param_list=[r.tp([name,True]) for _,name in params],var_data=[{},{},[]])
        for k in ('func_return','func_rtv_name_list'):self.obj.pop(k,None)
        self.params=params
        for kind,name in params:self.var(kind,name)
    def var(self,category,name,value_=None):
        typ,sub,default=TYPES[category]
        self.obj['var_data'][0].setdefault(category,{})[name]=default if value_ is None else value_
        self.obj['var_data'][1][name]=0
        if name not in self.obj['var_data'][2]:self.obj['var_data'][2].append(name)
        return b.n(typ,sub,r.tp([category,name,'local']))

def translated(node):
    ids={b.CONTROL:CONTROL,b.ARMY:ARMY,b.CHANGE:CHANGE}
    if isinstance(node,list):return [translated(x) for x in node]
    if isinstance(node,dict):return {translated(k):translated(v) for k,v in node.items()}
    if isinstance(node,str):
        for k,v in d.FIDS.items():
            if node==v:return FIDS[k]
        return node.replace('吴国','蜀国').replace('wu_readable_20261017','shu_cards_20261018')
    if isinstance(node,int) and not isinstance(node,bool):return ids.get(node,node)
    return node

def build_functions(rules,require_level5):
    payload={}
    # Reuse only functions with identical responsibilities and signatures.
    templates=d.build_functions(rules)
    for index in (1,4,5,6,7,8,10,11,12,13,14):
        obj=translated(templates[f'{r.FOLDER}/{d.NAMES[index]}.json'])
        obj['trigger_id']=2099851000+index
        serial=obj['trigger_id']*1000000
        for node in b.walk(obj):
            if 'element_id' in node:serial+=1;node['element_id']=serial
        payload[f'{FOLDER}/{NAMES[index]}.json']=obj
    def save(e,actions):payload[f'{FOLDER}/{NAMES[e.index]}.json']=e.finish(actions)
    e=Function(2,[('UNIT_ENTITY','卡牌载体'),('MODIFIER_ENTITY','控制Buff'),('BOOLEAN','强制阵型刷新')],
      '遍历本玩家持卡记录：有效实例、载体归属、蜀国分类三层校验，按技能类型去重；有变化才汇总。')
    u=e.var('UNIT_ENTITY','卡牌载体');m=e.var('MODIFIER_ENTITY','控制Buff');force=e.var('BOOLEAN','强制阵型刷新')
    pool=e.var('TABLE','玩家持卡记录');held=e.var('TABLE','有效卡牌快照');seen=e.var('TABLE','已统计类型')
    a=e.var('ABILITY','当前卡牌');key=e.var('STRING','当前类型');listing=e.var('STRING','持有清单');count=e.var('INTEGER','持卡数量')
    row=b.n(100002,'ITER_TABLE_KEY_INT')
    scan=d.traverse(e,pool,[e.set(a,d.val_table(pool,row,'技能')),
      e.branch([e.exists(a)],[e.branch([e.compare(d.val_table(pool,row,'归属单位','UNIT_ENTITY'),'==',u,'UNIT_COMPARE')],[
        e.branch([e.cond('HAS_KV_ANY',a,b.text(d.FACTION))],[e.branch([
          e.compare(value(a,d.FACTION,'STRING'),'==',b.text('蜀国'),'STRING_COMPARE')],[
          e.set(key,d.ability_key(a)),e.branch([e.cond('TABLE_HAS_KEY',seen,key)],[],[
            d.set_1d(e,seen,key,r.flag(True)),e.set(count,b.n(100002,'INT_PLUS_ONE',count)),
            d.set_1d(e,held,count,a),e.set(listing,r.join(listing,r.join(key,b.text('；'))))])])])])])])
    save(e,[e.set(pool,expr(11,'TABLE',u)),e.branch([e.exists(pool)],[
      r.section(e,'① 从现有持卡记录生成蜀国实例快照',[e.set(held,b.n(100011,'GET_NEW_TABLE')),
        e.set(seen,b.n(100011,'GET_NEW_TABLE')),e.set(count,r.i(0)),e.set(listing,b.text('')),scan,
        e.setkv(m,r.COUNT,b.math(count,'+',b.f(0))),e.setkv(m,'有效持卡快照',held)]),
      r.section(e,'② 清单或版本变化时整体重算',[e.branch([e.cond('OR',
        e.compare(listing,'!=',value(m,r.APPLIED,'STRING'),'STRING_COMPARE'),e.yes(b.n(100001,'GET_BOOLEAN_KV',u,b.text(DIRTY))))],
        [call(e,3,u,m,listing,held)])]),
      r.section(e,'③ 开战重读排位，覆盖新队长和小兵',[e.branch([e.yes(force)],[e.addkv(u,REV,b.f(1))]),call(e,5,u)]),
      r.section(e,'④ 检查已完成六套牌的终极结果',[call(e,18,u,held)])])])

    e=Function(3,[('UNIT_ENTITY','卡牌载体'),('MODIFIER_ENTITY','控制Buff'),('STRING','本次持有清单'),('TABLE','有效卡牌实例表')],
      '物编 KV 为数值唯一来源；先生成整份待提交配置，再一次提交。套牌结果继续保留；不重复叠组件属性。')
    u=e.var('UNIT_ENTITY','卡牌载体');m=e.var('MODIFIER_ENTITY','控制Buff');listing=e.var('STRING','本次持有清单')
    held=e.var('TABLE','有效卡牌实例表');row=e.var('INTEGER','实例行号');a=e.var('ABILITY','当前实例');ready=e.var('BOOLEAN','全部有效')
    fields=rule_table(u);fr=e.var('INTEGER','规则行号');key=r.get(fields,fr,'参数键')
    save(e,[r.section(e,'① 清空本次待提交参数',[e.set(ready,r.flag(True)),r.loop(e,fr,fields,[r.skv(e,m,r.preview_key(key),b.f(0))])]),
      r.section(e,'② 遍历实例并累加实际配置的参数',[r.loop(e,row,held,[e.set(a,d.get_1d(held,row)),
        e.branch([e.exists(a)],[call(e,4,a,m,fields)],[e.set(ready,r.flag(False))])])]),
      r.section(e,'③ 全部有效才提交，并增加配置版本',[e.branch([e.yes(ready)],[
        r.loop(e,fr,fields,[r.skv(e,u,r.join(b.text(PREFIX),key),value(m,r.preview_key(key)))]),
        e.setkv(m,r.APPLIED,listing),e.setkv(u,DIRTY,r.flag(False)),e.addkv(u,REV,b.f(1))])])])

    e=Function(9,[('UNIT_ENTITY','卡牌载体'),('UNIT_ENTITY','目标单位'),('UNIT_ENTITY','所属队长')],
      '按输出单位计算阵营、兵种和战前排位。骑兵与枪兵交集只算一次；统一写入 extra_dmg，不另乘伤害。')
    u=e.var('UNIT_ENTITY','卡牌载体');target=e.var('UNIT_ENTITY','目标单位');captain=e.var('UNIT_ENTITY','所属队长')
    damage=e.var('FLOAT','合计增伤');formation=integer(captain,'归属阵型编号')
    def c(key):return value(u,PREFIX+key)
    def inc(v):return e.set(damage,b.math(damage,'+',v))
    save(e,[e.set(damage,c(b.field_key('extra_dmg','ATTR_BASE'))),
      r.section(e,'① 蜀国输出单位：单卡被动与已完成套牌相加',[e.branch([e.cond('OR',
        e.cond('UNIT_HAS_TAG',target,b.text('蜀国')),e.cond('UNIT_HAS_TAG',captain,b.text('蜀国')))],[inc(b.math(c('单卡蜀国伤害'),'+',c('套牌蜀国伤害')))])]),
      r.section(e,'② 全军前排与后排：继承队长战前格位',[
        e.branch([e.compare(formation,'>=',r.i(1)),e.compare(formation,'<=',r.i(3))],[inc(c('套牌前排伤害'))]),
        e.branch([e.compare(formation,'>=',r.i(7)),e.compare(formation,'<=',r.i(9))],[inc(c('套牌后排伤害'))])]),
      r.section(e,'③ 全军骑兵：二代英杰套牌收益',[e.branch([e.cond('UNIT_HAS_TAG',target,b.text('骑兵'))],[inc(c('套牌骑兵伤害'))])]),
      r.section(e,'④ 终极：骑兵或枪兵只加一次',[e.branch([e.cond('OR',e.cond('UNIT_HAS_TAG',target,b.text('骑兵')),
        e.cond('UNIT_HAS_TAG',target,b.text('枪兵')))],[inc(c('终极骑枪伤害'))])]),e.ret('FLOAT',damage)])

    e=Function(15,[('UNIT_ENTITY','卡牌载体'),('MODIFIER_ENTITY','控制Buff')],
      '进入战斗时，每个真实波次只结算一次。SSR 刘备固定声望、庞统随机声望与原选卡声望并存；诸葛亮独立概率升一级，上限5。')
    u=e.var('UNIT_ENTITY','卡牌载体');m=e.var('MODIFIER_ENTITY','控制Buff')
    a=e.var('ABILITY','匡扶汉室实例');gain=e.var('INTEGER','本波新增声望');p=e.var('FLOAT','升级概率')
    pool=e.var('TABLE','当前持卡快照');card=e.var('ABILITY','当前波次卡牌');row=e.var('INTEGER','快照行号')
    # Reputation is integer data throughout; read integer object parameters
    # directly instead of guessing an unobserved float-to-int expression.
    per_card=[e.branch([e.cond('HAS_KV_ANY',card,b.text('每波固定声望'))],[
      e.set(gain,imath(gain,'+',integer(card,'每波固定声望')))]),
      e.branch([e.cond('HAS_KV_ANY',card,b.text('每波随机声望下限'))],[
        e.set(gain,imath(gain,'+',b.n(100002,'RANDOM_INT',integer(card,'每波随机声望下限'),integer(card,'每波随机声望上限'))))])]
    per_card_scan=r.loop(e,row,pool,[e.set(card,d.get_1d(pool,row)),e.branch([e.exists(card)],per_card)])
    save(e,[e.branch([e.compare(wave(),'>',r.i(0)),e.compare(wave(),'>',integer(u,PREFIX+'已结算波次'))],[
      e.setkv(u,PREFIX+'已结算波次',wave()),call(e,2,u,m,r.flag(True)),
      e.set(a,b.n(100014,'GET_ABILITY_BY_AID',u,b.lit(100182,2),b.lit(100039,BASE))),
      e.branch([e.exists(a)],[r.section(e,'① 汇总本波声望，复用现有声望升级函数',[
        e.set(gain,r.i(0)),e.set(pool,b.n(100011,'GET_TABLE_KV',m,b.text('有效持卡快照'))),per_card_scan,
        e.setkv(a,'声望累计',imath(integer(a,'声望累计'),'+',gain)),external(e,UPGRADE,a)]),
        r.section(e,'② 诸葛亮独立抽取一次；成功时升一级，上限5',[
          e.set(p,value(u,PREFIX+'每波升级概率')),e.branch([e.compare(p,'>',b.f(0)),e.compare(level(a),'<',r.i(5))],[
            e.branch([e.compare(b.n(100002,'RANDOM_INT',r.i(1),r.i(100)),'<=',p)],[
              e.action('SET_ABILITY_LEVEL',a,imath(level(a),'+',r.i(1)))])])]),
        r.section(e,'③ 通知持卡配置与终极检查',[call(e,14,u)])])])])

    e=Function(16,[('UNIT_ENTITY','击杀单位')],
      '本单位击杀才获得收益。糜竺恢复最大法力的2%，魏延永久攻击写入本单位基础属性；失去卡牌后停止新增，已有成长本局保留。')
    target=e.var('UNIT_ENTITY','击杀单位');u=e.var('UNIT_ENTITY','卡牌载体');mana=e.var('FLOAT','本次回蓝');missing=e.var('FLOAT','缺少法力')
    attrfid=find_fid('指定单位属性增减')
    save(e,[e.set(u,b.ukv(target,SOURCE)),e.branch([e.exists(u)],[e.branch([e.yes(b.hasbuff(u,CONTROL))],[
      r.section(e,'① 糜竺：各自击杀，各自恢复；最多回到法力上限',[e.branch([e.yes(b.hascard(u,134222904)),
        e.compare(value(u,PREFIX+'击杀回蓝百分比'),'>',b.f(0))],[
          e.set(missing,b.math(b.attr(target,'mp_max'),'-',b.n(100000,'GET_MP_CUR',target))),
          e.set(mana,b.math(b.attr(target,'mp_max'),'*',b.math(value(u,PREFIX+'击杀回蓝百分比'),'/',b.f(100)))),
          e.branch([e.compare(mana,'>',missing)],[e.set(mana,missing)]),
          e.branch([e.compare(mana,'>',b.f(0))],[e.action('ADD_CUR_MP',target,mana)])])]),
      r.section(e,'② 魏延：本单位基础攻击成长，刷新和换波不清零',[e.branch([e.yes(b.hascard(u,134282587)),
        e.compare(value(u,PREFIX+'击杀成长攻击'),'>',b.f(0))],[
          external(e,attrfid,target,b.text('攻击'),r.flag(True),value(u,PREFIX+'击杀成长攻击')),
          e.addkv(target,PREFIX+'本局击杀成长攻击',value(u,PREFIX+'击杀成长攻击'))])])])])])

    e=Function(17,[('UNIT_ENTITY','卡牌载体'),('ABILITY','关联卡牌')],
      '金币为一次性获得奖励。按玩家、卡牌类型记录已领取；重获和重复回调不重复发放，不参与持续属性汇总。')
    u=e.var('UNIT_ENTITY','卡牌载体');a=e.var('ABILITY','关联卡牌');key=e.var('STRING','领取记录键')
    save(e,[e.branch([e.cond('HAS_KV_ANY',a,b.text('获得金币'))],[e.set(key,r.join(b.text(PREFIX+'金币已领取_'),d.ability_key(a))),
      e.branch([e.no(b.n(100001,'GET_BOOLEAN_KV',b.player(u),key))],[r.skv(e,b.player(u),key,r.flag(True)),
        external(e,'36487c1f2b4f11f0b8029792acb0a9c5',b.player(u),b.lit(100037,'OGgJIytDEfC5bJeSrLCpxb'),value(a,'获得金币'),r.flag(False))])])])

    e=Function(18,[('UNIT_ENTITY','卡牌载体'),('TABLE','有效卡牌实例表')],
      '六套牌结果齐备后，用原合成函数授予 EX 刘备；不再次吞噬已完成结果。先置重入锁，防获得事件递归。')
    u=e.var('UNIT_ENTITY','卡牌载体');held=e.var('TABLE','有效卡牌实例表');a=e.var('ABILITY','当前实例')
    row=e.var('INTEGER','实例行号');count=e.var('INTEGER','完成套牌数量');exrow=e.var('INTEGER','终极表行号')
    pool=expr(11,'TABLE',u);iterrow=b.n(100002,'ITER_TABLE_KEY_INT');base=b.n(100014,'GET_ABILITY_BY_AID',u,b.lit(100182,2),b.lit(100039,BASE))
    checks=[e.no(b.hascard(u,EX)),e.no(b.n(100001,'GET_BOOLEAN_KV',u,b.text(PREFIX+'终极授予中')))]
    if require_level5:checks += [e.exists(base)]
    grant=[e.setkv(u,PREFIX+'终极授予中',r.flag(True)),external(e,MERGE,b.player(u),exrow),e.setkv(u,PREFIX+'终极授予中',r.flag(False))]
    if require_level5:grant=[e.branch([e.compare(level(base),'>=',r.i(5))],grant)]
    save(e,[e.branch(checks,[e.set(count,r.i(0)),e.set(exrow,r.i(0)),
      r.section(e,'① 计数有效快照中的套牌结果',[r.loop(e,row,held,[e.set(a,d.get_1d(held,row)),
        e.branch([e.compare(value(a,d.IDENTITY,'STRING'),'==',b.text('套牌结果'),'STRING_COMPARE')],[e.set(count,b.n(100002,'INT_PLUS_ONE',count))])])]),
      r.section(e,'② 六套牌齐备后按表行号调用原合成流程',[e.branch([e.compare(count,'>=',r.i(6))],[
        d.traverse(e,pool,[e.branch([e.compare(b.n(100039,'GET_ABILITY_NAME_TABLE_VAR_ND',pool,iterrow,b.text('技能类型')),'==',b.lit(100039,EX),'ABILITY_COMPARE')],[e.set(exrow,iterrow)])]),
        e.branch([e.compare(exrow,'>',r.i(0))],grant)])])])])
    return payload

def find_fid(fragment):
    matches=[p for p in (MAP/'global_trigger/function').rglob('*.json') if fragment in p.stem]
    assert len(matches)==1,(fragment,matches)
    return json.loads(matches[0].read_text('utf8'))['func_id']

def specs_from_book():
    import openpyxl
    assert sha(BOOK.read_bytes())==BOOK_SHA,'Workbook changed: re-audit source rows'
    book=openpyxl.load_workbook(BOOK,read_only=True,data_only=True);sheet=book['套牌'];sheet.reset_dimensions()
    rows=list(sheet.iter_rows(min_row=28,max_row=53,max_col=9,values_only=True));book.close()
    pool=read('tables/蜀国temp.json')['table_data']['data'];lang=read('zhlanguage.json');specs={}
    for row in pool[2:]:
        if not row or not isinstance(row[1],int):continue
        aid=row[1];obj=read(f'editor_table/abilityall/{aid}.json')
        specs[aid]={'id':aid,'name':lang[str(obj['name'])],'set':row[6],'params':{},'base':[],'row':None}
    lookup={(s['set'],s['name']):aid for aid,s in specs.items()}
    lookup[('蜀汉宿将','严颜')]=134248548
    new={('桃园结义','刘备'):LIUBEI,('桃园结义','关羽'):TAOYUAN_GUAN,('桃园结义','张飞'):TAOYUAN_ZHANG,('匡扶汉室','刘备'):EX}
    for offset,row in enumerate(rows,28):
        faction,setname,name,rarity,*values=row
        if faction not in (None,'','蜀国'):continue
        # Merged Excel cells are blank; set and faction carry forward.
        if setname:current_set=setname
        setname=current_set
        aid=new.get((setname,name),lookup.get((setname,name)))
        assert aid is not None,(offset,row,setname)
        s=specs.setdefault(aid,{'id':aid,'name':name,'set':setname,'params':{},'base':[]})
        s.update(row=offset,rarity=rarity,base=list(values[:3]),special=values[3])
        for val in values[:3]:
            if val in (None,'','-'):continue
            if str(val).startswith('金币'):s['params']['获得金币']=float(str(val).split('+')[1]);continue
            s['params'].update(b.parse_base([val]))
    specs[TAOYUAN]={'id':TAOYUAN,'name':'桃园结义','set':'桃园结义','params':{},'base':[],'row':None}
    for aid,(_,damage) in RESULTS.items():specs[aid]['params']['套牌蜀国伤害']=float(damage)
    specs[134266951]['params']['套牌前排伤害']=15.
    specs[134251758]['params']['套牌骑兵伤害']=20.
    specs[134283217]['params'].update({b.field_key('critical_chance','ATTR_BASE'):30.,b.field_key('critical_dmg','ATTR_BASE'):100.})
    specs[134257279]['params']['套牌后排伤害']=25.
    specs[134222904]['params']['击杀回蓝百分比']=2.
    specs[134282587]['params']['击杀成长攻击']=1.
    specs[LIUBEI]['params']['每波固定声望']=30
    specs[134230426]['params'].update(每波随机声望下限=10,每波随机声望上限=20)
    specs[134223259]['params']['每波升级概率']=10.
    specs[EX]['params'].update(单卡蜀国伤害=30.,套牌蜀国伤害=60.,终极骑枪伤害=50.)
    for aid,s in specs.items():
        s['identity']='起始载体' if aid==BASE else 'EX' if aid==EX else '套牌结果' if aid in RESULTS else '普通组件'
        s['description']='；'.join(str(x) for x in s['base'] if x not in (None,'','-'))
        if s.get('special') not in (None,'','-'):s['description']+='；'+s['special']
        if aid in RESULTS:
            s['description']='套牌吞噬：蜀国角色伤害+'+str(RESULTS[aid][1])+'%'
            s['description']+= {134266951:'；全军前排伤害+15%',134251758:'；全军骑兵伤害+20%',134283217:'；全军暴击率+30%、暴击伤害+100%',134257279:'；全军后排伤害+25%'}.get(aid,'')
        if aid==BASE:s['description']='蜀国起始军略；保留原获得/合成声望与30/60/90/120声望升级规则，上限5级。'
        if aid==EX:s['description']+='；终极：蜀国伤害+60%，全军骑兵或枪兵伤害+50%（交集只加一次）；已完成套牌收益保留。'
    assert len(specs)==33
    return specs

def make_rules(specs):
    integer_wave={'每波固定声望','每波随机声望下限','每波随机声望上限'}
    keys=sorted((set(MECHANICS)|{k for s in specs.values() for k in s['params']})-integer_wave-{'获得金币'})
    rules=[]
    for k in keys:
        if k.startswith('属性_'):
            attr,mode=k[3:].rsplit('_ATTR_',1);mode='ATTR_'+mode;direct=attr!='extra_dmg'
            label=next((n for n,pair in b.FIELDS.items() if pair==(attr,mode)),('全属性比例' if mode=='ATTR_ALL_RATIO' else '属性')+':'+attr)
        else:attr,mode,direct,label='strength','ATTR_BASE',False,k
        rules.append({'收益名称':label,'参数键':k,'单位属性':attr,'属性计算方式':mode,'直接写入面板':direct})
    return rules

def build_embedded(specs):
    out={};b.TID=2099861000
    for aid,s in specs.items():
        e=b.Eca(aid);u=b.unit('ABILITY_OWNER');actions=[]
        if (MAP/f'ability/{aid}.json').exists():
            old=read(f'ability/{aid}.json')
            ts=list(old['trigger_dict'].values())
            assert len(ts)==1 and ts[0]['event'][0]['event_type']=='ABILITY_OBTAIN'
            actions=copy.deepcopy(ts[0]['action'])
        elif aid in (LIUBEI,TAOYUAN_GUAN,TAOYUAN_ZHANG,TAOYUAN):
            lo,hi=(80,120) if aid==TAOYUAN else (10,200)
            actions=[e.setkv(b.ability(),'获得声望',b.n(100002,'RANDOM_INT',r.i(lo),r.i(hi)))]
        actions += [call(e,1,u,b.ability()),call(e,17,u,b.ability())]
        e.trigger('获得卡牌：保留声望赋值，建立控制并结算一次性收益','ABILITY_OBTAIN',actions)
        e.trigger('等级变化：由当前技能取得拥有者后标记刷新','ABILITY_LEVEL_CHANGED',[call(e,14,b.n(100006,'GET_ABILITY_OWNER',b.ability()))])
        e.trigger('失去卡牌：通知刷新，周期校验覆盖删除时序','ABILITY_LOSE',[call(e,14,u)])
        out[f'ability/{aid}.json']=e.done()
    e=b.Eca(CONTROL,True);u=b.owner();m=b.buff()
    gain=e.trigger('获得控制：只注册监听，等待持卡记录写入','OBTAIN_MODIFIER')
    change=e.trigger('卡牌变化：刷新有效实例与全军收益','RECEIVE_CUSTOM_EVENT',[call(e,2,u,m,r.flag(False))],
      args=[b.lit(100238,CHANGE)],conditions=[e.compare(b.n(100006,'GET_CUS_EVENT_PARAM',b.lit(100240,'载体单位')),'==',u,'UNIT_COMPARE')],parent=gain,handle='持卡变化监听')
    phase=e.trigger('进入战斗：每波声望与品质结算一次','RECEIVE_CUSTOM_EVENT',[call(e,15,u,m)],args=[b.lit(100238,PHASE)],
      conditions=[e.compare(b.n(100002,'GET_CUS_EVENT_PARAM',b.lit(100240,'阶段编号')),'==',r.i(2))],parent=gain,handle='开战监听')
    e.obj['trigger_dict'][str(gain)]['action']=[e.setkv(m,r.APPLIED,b.text('未初始化')),e.setkv(m,r.COUNT,b.f(-1)),
      e.branch([e.compare(b.n(100002,6,r.tp(['INTEGER','当前游戏进程阶段'])),'==',r.i(2))],[e.setkv(u,PREFIX+'已结算波次',wave())]),change,phase]
    e.trigger('周期校验：持卡删除、补兵和召唤兜底','MODIFIER_CYCLE_TRIGGER',[call(e,2,u,m,r.flag(False)),
      e.branch([e.compare(value(m,r.COUNT),'==',b.f(0))],[e.action('REMOVE_BUFF_INS',m)])])
    e.trigger('失去控制：注销两个监听并清空本系统缓存','LOSS_MODIFIER',[
      e.unreg('持卡变化监听'),e.unreg('开战监听'),call(e,10,u)])
    out[f'modifier/{CONTROL}.json']=e.done()
    e=b.Eca(ARMY,True);u=b.owner();m=b.buff()
    gain=e.trigger('获得收益：注册配置与本单位击杀监听','OBTAIN_MODIFIER')
    change=e.trigger('配置变化：覆盖本Buff的属性贡献','RECEIVE_CUSTOM_EVENT',[call(e,7,m,u,r.flag(True))],args=[b.lit(100238,CHANGE)],
      conditions=[e.compare(b.n(100006,'GET_CUS_EVENT_PARAM',b.lit(100240,'载体单位')),'==',b.ukv(u,SOURCE),'UNIT_COMPARE')],parent=gain,handle='配置变化监听')
    kill=e.trigger('本单位击杀：糜竺回蓝与魏延成长','SPECIAL_UNIT_EVENT',[call(e,16,u)],args=[u,b.lit(100007,'ET_KILL_UNIT')],parent=gain,handle='本单位击杀监听')
    e.obj['trigger_dict'][str(gain)]['action']=[e.setkv(m,REV,b.f(-1)),change,kill,call(e,7,m,u,r.flag(False))]
    e.trigger('周期校验：配置版本改变时刷新','MODIFIER_CYCLE_TRIGGER',[call(e,7,m,u,r.flag(False))])
    e.var('FLOAT','移除前生命比例',0.)
    ratio=b.av(100000,'移除前生命比例',2,'FLOAT')
    clear=e.action('CLEAR_MODIFIER_OWNER_ATTR',m)
    e.trigger('失去收益：保持生命比例，撤销本Buff贡献并注销监听','LOSS_MODIFIER',[
      e.branch([e.alive(u)],[e.setvar('FLOAT','移除前生命比例',b.math(b.n(100000,'GET_HP_CUR',u),'/',b.attr(u,'hp_max'))),clear,
        e.action('ADD_CUR_HP',u,b.math(b.math(b.attr(u,'hp_max'),'*',ratio),'-',b.n(100000,'GET_HP_CUR',u)))],[clear]),
      e.unreg('配置变化监听'),e.unreg('本单位击杀监听')])
    out[f'modifier/{ARMY}.json']=e.done()
    return out

def kv_entry(key,v,sort):
    text=isinstance(v,str);integer_=isinstance(v,int) and not isinstance(v,bool)
    return dict(annotation='蜀国军略',desc='本卡独立配置；公共函数只读取参数',etype=0 if text else 1 if integer_ else 2,key=key,
      prop_cls='PText' if text else 'PInt' if integer_ else 'PFloat',remark='',show_in_attr=True,sort=sort,type=0 if text else 2 if integer_ else 1,value=v)

def stage(require_level5=False):
    assert not (WORK/'published.json').exists(),'Already published: do not rerun against changed live files'
    WORK.mkdir(parents=True,exist_ok=True)
    specs=specs_from_book();rules=make_rules(specs)
    for oid in (CONTROL,ARMY,LIUBEI,TAOYUAN_GUAN,TAOYUAN_ZHANG,TAOYUAN,EX):
        assert not any((MAP/folder/f'{oid}.json').exists() for folder in ('ability','modifier','editor_table/abilityall','editor_table/modifierall')),f'ID occupied: {oid}'
    payload=build_functions(rules,require_level5);payload.update(build_embedded(specs))
    language=read('zhlanguage.json');nextlang=1918100000
    def string(text):
        nonlocal nextlang
        while str(nextlang) in language:nextlang+=1
        key=nextlang;language[str(key)]=text;nextlang+=1;return key
    clones={LIUBEI:134223259,TAOYUAN_GUAN:134267079,TAOYUAN_ZHANG:134261267,TAOYUAN:134283217,EX:BASE}
    for aid,s in specs.items():
        obj=read(f'editor_table/abilityall/{clones.get(aid,aid)}.json')
        obj.update(_ref_=aid,key=aid,uid=str(aid))
        if aid in clones:
            obj['name']=string(s['name']);obj['suffix']='被动-EX' if aid==EX else '被动-result' if aid==TAOYUAN else '被动-set'
            obj['kv']={};obj['ability_max_level']=1
        desc=s['description']+'；基础属性覆盖己方队长及其小兵，条件增伤按输出单位判断。'
        obj['description']=obj['desc']=string('<html><body><p>'+desc+'</p></body></html>')
        values={**s['params'],d.FACTION:'蜀国',d.IDENTITY:s['identity']}
        if aid in clones:values['获得声望']=0 if aid==EX else 10
        for key,v in values.items():obj['kv'][key]=kv_entry(key,v,len(obj['kv']))
        payload[f'editor_table/abilityall/{aid}.json']=obj
    for oid,name,cycle in [(CONTROL,'蜀国军略·全军配置控制',.5),(ARMY,'蜀国军略·单位收益',.1)]:
        obj=read(f'editor_table/modifierall/{b.CONTROL if oid==CONTROL else b.ARMY}.json')
        obj.update(_ref_=oid,key=oid,uid=str(oid),name=string(name),desc=string('蜀国军略专用；收益版本变化才重算，失去时清理自身贡献。'),
          suffix='蜀国军略',cycle_time=cycle,kv={})
        obj['description']=obj['desc'];payload[f'editor_table/modifierall/{oid}.json']=obj
    # Extend the existing formal Shu pool and its faction source together.
    for rel in ['tables/军令卡牌技能表.json','tables/蜀国temp.json']:
        obj=read(rel);data=obj['table_data']['data'];header=data[:2];rows=[x for x in data[2:] if x and str(x[0]).isdigit()]
        assert {x[1] for x in rows if x[2]=='蜀国'}==set(specs)-set(clones)
        for row in rows:
            if row[1]==134283217:row[9]='桃园结义'
        template=next(x for x in rows if x[1]==134267079)
        for aid in (LIUBEI,TAOYUAN_GUAN,TAOYUAN_ZHANG,TAOYUAN,EX):
            row=copy.deepcopy(template);row[0]=str(max(int(x[0]) for x in rows)+1);row[1]=aid
            row[5]='true' if aid in (TAOYUAN,EX) else 'false';row[6]='匡扶汉室终极' if aid==EX else '桃园结义'
            row[7]='false';row[8]='false';row[9]='无';rows.append(row)
        obj['table_data']['data']=header+rows;payload[rel]=obj
    folder=read('editor/folderinfo/folderinfo_ability_all.json')
    shu=next(x['items'] for x in folder['f'] if x['items'][3]=='蜀国');path=shu[0]+'/'+str(shu[2])
    for folderid,label,ids in [('shutaoyuan20261018','桃园结义',[LIUBEI,TAOYUAN_GUAN,TAOYUAN_ZHANG,TAOYUAN]),('shuex20261018','匡扶汉室EX',[EX])]:
        assert not any(x['items'][2]==folderid for x in folder['f'])
        order=max((x['items'][1] for x in folder['f'] if x['items'][0]==path),default=-1)+1
        folder['f'].append(r.tp([path,order,folderid,label]))
        for i,aid in enumerate(ids):folder['d'][str(aid)]=r.tp([folderid,i])
    payload['editor/folderinfo/folderinfo_ability_all.json']=folder
    folder=read('editor/folderinfo/folderinfo_modifier_all.json');parent=next(x['items'] for x in folder['f'] if x['items'][2]==folder['d'][str(b.CONTROL)]['items'][0])
    order=max(x['items'][1] for x in folder['f'] if x['items'][0]==parent[0])+1
    folder['f'].append(r.tp([parent[0],order,'shucardmod20261018','蜀国军略']))
    for i,oid in enumerate((CONTROL,ARMY)):folder['d'][str(oid)]=r.tp(['shucardmod20261018',i])
    payload['editor/folderinfo/folderinfo_modifier_all.json']=folder
    custom=read('customevent.json');assert str(CHANGE) not in custom['conf']
    custom['conf'][str(CHANGE)]=[['载体单位',100006]];custom['group_info'].append(r.tp([CHANGE,'蜀国军略配置刷新']));payload['customevent.json']=custom
    index=read('global_trigger/function/new/index.txt');index['蜀国军略.folder']=max(index.values())+1
    payload['global_trigger/function/new/index.txt']=index
    payload[FOLDER+'/index.txt']={name+'.json':i-1 for i,name in NAMES.items()}
    # Only append one post-record-write notification in the two shared paths.
    for filename in ['3选1军略卡牌处理.json','军略3选1-处理合成的新卡牌.json']:
        path=next((MAP/'global_trigger/function').rglob(filename));doc=json.loads(path.read_text('utf8'))
        u=copy.deepcopy(next(n for n in b.walk(doc) if n.get('arg_type')==100006 and n.get('sub_type')==11 and n.get('args_list') and
          isinstance(n['args_list'][0],dict) and n['args_list'][0].get('items',[None,None])[:2]==['UNIT_ENTITY','playerHeroList']))
        e=b.Eca(2099851999);action=call(e,14,u);action['element_id']=max(n.get('element_id',0) for n in b.walk(doc))+1
        at=len(doc['action'])-1 if doc['action'][-1].get('action_type')==400342 else len(doc['action']);doc['action'].insert(at,action)
        payload[path.relative_to(MAP).as_posix()]=doc
    desc=read('tables/技能作用描述表.json');rows=desc['table_data']['data'];width=len(rows[0]);count=max(int(x[0]) for x in rows[2:] if x and str(x[0]).isdigit())
    for aid,s in specs.items():
        matches=[row for row in rows[2:] if len(row)>1 and row[1]==aid]
        if matches:
            for row in matches:
                for j in range(3,min(14,len(row))):row[j]=s['description']
        else:count+=1;rows.append(([str(count),aid,'被动']+[s['description']]*11+['']*width)[:width])
    payload['tables/技能作用描述表.json']=desc;payload['zhlanguage.json']=language
    manifest={}
    with zipfile.ZipFile(WORK/'before-shu.zip','w',compression=zipfile.ZIP_DEFLATED) as backup:
        for rel,obj in payload.items():
            live=MAP/rel;before=live.read_bytes() if live.exists() else None
            if before is not None:backup.writestr(rel,before)
            target=STAGE/rel;target.parent.mkdir(parents=True,exist_ok=True)
            raw=(json.dumps(obj,ensure_ascii=True,indent=4)+'\n').encode('utf8');target.write_bytes(raw)
            manifest[rel]={'before':sha(before) if before is not None else None,'after':sha(raw)}
    for name,obj in [('manifest',manifest),('specs',specs),('attribute-rules',rules),('scope',{'require_level5':require_level5,'source_sha256':BOOK_SHA,'map':str(MAP)})]:
        (WORK/(name+'.json')).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
    print('Staged',len(manifest),'files;',len(specs),'cards; 18 functions; 2 Buffs;',len(rules),'runtime rules. Live map unchanged.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--require-level5',action='store_true');stage(parser.parse_args().require_level5)
