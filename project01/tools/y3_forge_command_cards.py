"""Maintain forge rules, functions and embedded ECA building blocks.

Initial full-map staging/publication retired after the 2026-10-29 delivery.
Regression inputs live in tests/fixtures/y3-recent-work.
"""
from __future__ import annotations
import copy,json,uuid
from pathlib import Path
import y3_qun_command_cards as q
b,r,d,s,w=q.b,q.r,q.d,q.s,q.w
MAP=q.MAP
BASE,EX=134219838,134238136
CONTROL,ARMY,CHANGE=134285401,134285402,2099456410
PREFIX='锻造军略_';RULES=PREFIX+'属性规则';DIRTY=PREFIX+'待刷新'
BUSY,CLAIMED,COMPLETE,COUNT,RETRY=(PREFIX+x for x in ('结算中','本局终局已领取','五神兵已完成','完成锻造数','需要重试'))
DONE=PREFIX+'完成神兵_';TID=2099936000
NAMES={**{i:n.replace('群雄','锻造')for i,n in q.NAMES.items()if i<=14},
15:'15_选卡写表后检查锻造',16:'16_读取指定类型的有效实例',17:'17_开放图纸与材料',
18:'18_读取材料实际数量',19:'19_按完成数量同步锤子等级',20:'20_校验并完成一次锻造',
21:'21_带来源授予指定表行',22:'22_五神兵终局及唯一额外奖励'}
FOLDER='global_trigger/function/new/锻造军略'
FIDS={i:uuid.uuid5(uuid.NAMESPACE_URL,'project01/y3/forge/'+n).hex for i,n in NAMES.items()}
MATERIALS={'铜':134275195,'铁':134260011,'精钢':134222206,'镔铁':134276867,'陨铁':134274353}
BLUEPRINTS={134248137:134264094,134239632:134255392,134253383:134242388,134264424:134229761,134236820:134256398}
WEAPONS={134264094:('agility',60),134255392:('attack_phy',100),134242388:('attack_phy',100),134229761:('attack_phy',100),134256398:('attack_speed',10)}
ALL=(5,10,20,30,45,60);ATTACK=(10,25,50,80,110,150)
ATTRS=('strength','agility','intelligence','attack_phy','attack_speed')
read=q.read;sha=q.sha;config=q.config;carrier=q.carrier;integer=q.integer;boolean=q.boolean
def expr(i,kind,*args):return s.foreign(FIDS[i],kind,*args)
def call(e,i,*args):return s.external(e,FIDS[i],*args)
def done(p,aid):return boolean(p,r.join(b.text(DONE),w.typekey(aid)))
def log(e,*parts):return e.branch([e.yes(q.journal.enabled())],[q.journal.emit(e,'[锻造军略/v1] ',*parts)])
def rel(i):return f'{FOLDER}/{NAMES[i]}.json'
def rulekey(attr):return b.field_key(attr,'ATTR_BASE')
def rules():return [dict(收益名称=k,参数键=k,单位属性=a,属性计算方式='ATTR_BASE',直接写入面板=True)for a in ATTRS for k in [rulekey(a)]]
def translate(x):
    if isinstance(x,list):return [translate(v)for v in x]
    if isinstance(x,dict):return {k:translate(v)for k,v in x.items()}
    if isinstance(x,str):
        if x in q.FIDS.values():return FIDS[next(i for i,v in q.FIDS.items()if v==x)]
        return x.replace('群雄','锻造').replace('qun_cards_20261027','forge_cards_20261029')
    if isinstance(x,int)and not isinstance(x,bool):return {q.CONTROL:CONTROL,q.ARMY:ARMY,q.CHANGE:CHANGE}.get(x,x)
    return x
class Function(q.Function):
    def __init__(self,i,params,comment):
        super().__init__(i,params,comment);self.oid=TID+i;self.serial=self.oid*1000000
        self.obj.update(func_id=FIDS[i],func_name=NAMES[i],trigger_name=NAMES[i],trigger_id=self.oid,group_id='forge_cards_20261029',
          func_des=NAMES[i]+'：'+ '，'.join(n+'{'+n+'}'for _,n in params))

def build_functions():
    out={}
    for i in range(1,15):out[rel(i)]=w.reidentify(translate(read(f'{q.FOLDER}/{q.NAMES[i]}.json')),TID+i)
    out[rel(16)]=w.reidentify(translate(read(f'{q.FOLDER}/{q.NAMES[16]}.json')),TID+16)
    out[rel(21)]=w.reidentify(translate(read(f'{q.FOLDER}/{q.NAMES[21]}.json')),TID+21)
    def save(e,actions):out[rel(e.index)]=e.finish(actions)
    # Existing formation traversal gives a soldier its captain, and a hero itself.
    e=Function(8,[],'');target=e.var('UNIT_ENTITY','目标单位');cap=e.var('UNIT_ENTITY','所属队长')
    doc=out[rel(8)]
    for n in b.walk(doc):
        if n.get('action_type')=='IF_THEN_ELSE' and any(v.get('args_list')==['直接写入面板']for v in b.walk(n['args_list'][0])):
            body=n['args_list'][1]['args_list'];n['args_list'][1]['args_list']=[e.branch([e.compare(target,'==',cap,'UNIT_COMPARE')],body)]
    out[rel(8)]=w.reidentify(doc,TID+8)
    # Keep growth after source-card loss: controller remains while a completion exists.
    doc=out[rel(2)];e=Function(2,[],'');u=e.var('UNIT_ENTITY','卡牌载体');count=e.var('INTEGER','持卡数量')
    for n in b.walk(doc):
        if n.get('arg_type')==100022:
            for idx,a in list(enumerate(n.get('args_list',[]))):
                if a.get('action_type')=='SET_ENTITY_KV' and a['args_list'][1].get('args_list')==[r.COUNT]:
                    n['args_list'].insert(idx,e.branch([e.compare(count,'==',r.i(0)),e.compare(integer(b.player(u),COUNT),'>',r.i(0))],[e.set(count,r.i(1))]));break
    out[rel(2)]=w.reidentify(doc,TID+2)
    # Add player-scoped permanent growth to the normal staged attribute sum.
    doc=out[rel(3)];e=Function(3,[],'');u=e.var('UNIT_ENTITY','卡牌载体');mod=e.var('MODIFIER_ENTITY','控制Buff')
    growth=b.math(b.math(integer(b.player(u),COUNT),'*',r.i(2)),'+',b.f(0))
    increments=[r.skv(e,mod,r.preview_key(b.text(rulekey(a))),b.math(r.value(mod,r.preview_key(b.text(rulekey(a)))),'+',growth))for a in ATTRS[:3]]
    doc['action'].insert(2,r.section(e,'③ 玩家本局锻造成长：每完成一件＋2全属性；只在英雄面板应用',increments))
    out[rel(3)]=w.reidentify(doc,TID+3)
    e=Function(4,[('ABILITY','卡牌实例'),('MODIFIER_ENTITY','控制Buff'),('TABLE','属性规则表')],'基础属性读物编；锤子按等级选择一档，不累加历级。')
    a=e.var('ABILITY','卡牌实例');mod=e.var('MODIFIER_ENTITY','控制Buff');t=e.var('TABLE','属性规则表');fr=e.var('INTEGER','参数行号');value=e.var('FLOAT','本项数值');key=r.get(t,fr,'参数键')
    load=[e.set(value,b.f(0)),e.branch([e.cond('HAS_KV_ANY',a,key)],[e.set(value,r.value(a,key))])]
    for level in range(1,7):load.append(e.branch([e.compare(b.n(100039,'ABILITY_NAME_OF_ABILITY',a),'==',b.lit(100039,BASE),'ABILITY_COMPARE'),e.compare(s.level(a),'==',r.i(level))],[e.set(value,r.value(a,r.join(b.text(f'等级{level}_'),key))) ]))
    load.append(r.skv(e,mod,r.preview_key(key),b.math(r.value(mod,r.preview_key(key)),'+',value)))
    save(e,[r.loop(e,fr,t,load)])
    e=Function(9,[('UNIT_ENTITY','卡牌载体'),('UNIT_ENTITY','目标单位'),('UNIT_ENTITY','所属队长')],'五件神兵完成后全军＋20%与锤子EX＋30%相加一次；额外方天画戟不重复加成。')
    u=e.var('UNIT_ENTITY','卡牌载体');e.var('UNIT_ENTITY','目标单位');e.var('UNIT_ENTITY','所属队长');value=e.var('FLOAT','合计增伤')
    save(e,[e.set(value,b.f(0)),e.branch([e.yes(boolean(b.player(u),COMPLETE))],[e.set(value,b.f(50))]),e.ret('FLOAT',value)])
    e=Function(12,[('UNIT_ENTITY','卡牌载体')],'每载体首次创建属性规则；不维护第二份持卡名单。')
    u=e.var('UNIT_ENTITY','卡牌载体');t=e.var('TABLE','属性规则表')
    save(e,[e.set(t,b.n(100011,'GET_TABLE_KV',u,b.text(RULES))),e.branch([e.exists(t)],[],[e.set(t,b.n(100011,'GET_NEW_TABLE')),
      *[call(e,13,t,b.text(x['参数键']),b.text(x['参数键']),b.lit(100042,x['单位属性']),b.lit(100300,'ATTR_BASE'),r.flag(True))for x in rules()],e.setkv(u,RULES,t)]),e.ret('TABLE',t)])
    e=Function(17,[('PLAYER','执行玩家')],'只开放图纸和材料；结果与方天画戟永不进入普通报价。')
    p=e.var('PLAYER','执行玩家');cfg=e.var('TABLE','卡牌配置');row=b.n(100002,'ITER_TABLE_KEY_INT')
    save(e,[e.branch([e.compare(integer(p,COUNT),'<',r.i(5))],[e.set(cfg,config(p)),w.traverse(e,cfg,[e.branch([e.compare(r.get(cfg,row,'升级机制'),'==',b.text('武器锻造'),'STRING_COMPARE'),e.no(r.get(cfg,row,'是否合成','BOOLEAN')),
      e.cond('OR',e.compare(r.get(cfg,row,'子归类'),'==',b.text('材料'),'STRING_COMPARE'),e.compare(r.get(cfg,row,'子归类'),'==',b.text('图纸'),'STRING_COMPARE'))],[e.action('SET_TABLE_VALUE_ND',cfg,row,b.text('是否解锁'),r.flag(True)),
      e.branch([e.compare(r.get(cfg,row,'子归类'),'==',b.text('材料'),'STRING_COMPARE')],[e.action('SET_TABLE_VALUE_ND',cfg,row,b.text('是否已抽取'),r.flag(False))])])])])])
    e=Function(18,[('PLAYER','执行玩家'),('ABILITY_NAME','材料类型')],'有效实例存在才读取库存；缺失返回0，不读取空技能。')
    p=e.var('PLAYER','执行玩家');typ=e.var('ABILITY_NAME','材料类型');a=e.var('ABILITY','材料实例');num=e.var('INTEGER','实际数量')
    save(e,[e.set(num,r.i(0)),e.set(a,expr(16,'ABILITY',p,typ)),e.branch([e.exists(a)],[e.set(num,integer(a,'累计总数'))]),e.ret('INTEGER',num)])
    e=Function(19,[('PLAYER','执行玩家')],'按成功完成数量同步等级1～6，不重复加级；等级只读一次完成账。')
    p=e.var('PLAYER','执行玩家');a=e.var('ABILITY','锤子实例');level=e.var('INTEGER','应有等级')
    save(e,[e.set(a,expr(16,'ABILITY',p,b.lit(100039,BASE))),e.branch([e.exists(a)],[e.set(level,b.n(100002,'INT_PLUS_ONE',integer(p,COUNT))),
      e.branch([e.compare(level,'>',r.i(6))],[e.set(level,r.i(6))]),e.branch([e.compare(s.level(a),'!=',level)],[e.action('SET_ABILITY_LEVEL',a,level)])])])
    e=Function(20,[('PLAYER','执行玩家'),('INTEGER','图纸表行'),('INTEGER','结果表行')],'在函数15的玩家重入锁内：读配方→校验→发卡成功→扣料一次→记账→升锤。失败不扣料、不加成长。')
    p=e.var('PLAYER','执行玩家');bp=e.var('INTEGER','图纸表行');row=e.var('INTEGER','结果表行');cfg=e.var('TABLE','卡牌配置');paper=e.var('ABILITY','图纸实例');result=e.var('ABILITY','神兵实例');ok=e.var('BOOLEAN','材料足够')
    needed={name:e.var('INTEGER','需要'+name)for name in MATERIALS};handles={name:e.var('ABILITY',name+'实例')for name in MATERIALS}
    resulttype=w.typename(cfg,row);actions=[e.set(ok,r.flag(True))]
    for name,aid in MATERIALS.items():actions += [e.set(needed[name],integer(paper,name)),e.branch([e.compare(needed[name],'<',r.i(0))],[e.set(ok,r.flag(False))]),
      e.branch([e.compare(expr(18,'INTEGER',p,b.lit(100039,aid)),'<',needed[name])],[e.set(ok,r.flag(False))])]
    debit=[]
    for name,aid in MATERIALS.items():debit.append(e.branch([e.compare(needed[name],'>',r.i(0))],[e.set(handles[name],expr(16,'ABILITY',p,b.lit(100039,aid))),
      e.setkv(handles[name],'累计总数',s.imath(integer(handles[name],'累计总数'),'-',needed[name])),
      log(e,'扣料；玩家=',q.journal.idx(p),'；神兵=',resulttype,'；材料=',name,'；消耗=',needed[name],'；剩余=',integer(handles[name],'累计总数'))]))
    commit=[*debit,r.skv(e,p,r.join(b.text(DONE),w.typekey(resulttype)),r.flag(True)),e.setkv(p,COUNT,b.n(100002,'INT_PLUS_ONE',integer(p,COUNT))),
      s.external(e,'5ec39849b3e211f197f88b7bdf2d7282',p,r.get(cfg,row,'所属set')),call(e,19,p),call(e,14,carrier(p)),
      log(e,'完成锻造；玩家=',q.journal.idx(p),'；神兵=',resulttype,'；完成数=',integer(p,COUNT),'；英雄累计全属性=',s.imath(integer(p,COUNT),'*',r.i(2)))]
    attempt=[e.set(result,expr(21,'ABILITY',p,row,b.text('锻造成功；消耗材料合成神兵'))),e.branch([e.exists(result)],commit,[e.setkv(p,RETRY,r.flag(True)),log(e,'发卡失败保留材料；玩家=',q.journal.idx(p),'；目标=',resulttype)])]
    save(e,[e.set(cfg,config(p)),e.branch([e.no(done(p,resulttype))],[e.set(paper,expr(16,'ABILITY',p,w.typename(cfg,bp))),e.branch([e.exists(paper)],
      [r.section(e,'① 配方只读图纸物编，查询不扣料',actions),e.branch([e.yes(ok)],[r.section(e,'② 发卡成功才扣料并登记一次完成',attempt)])])])])
    e=Function(22,[('PLAYER','执行玩家')],'五种神兵自然完成后开启终局收益；额外方天画戟按玩家仅发一次，失败保留资格重试。')
    p=e.var('PLAYER','执行玩家');cfg=e.var('TABLE','卡牌配置');row=b.n(100002,'ITER_TABLE_KEY_INT');a=e.var('ABILITY','额外奖励')
    grant=w.traverse(e,cfg,[e.branch([e.compare(w.typename(cfg,row),'==',b.lit(100039,EX),'ABILITY_COMPARE')],[
      e.set(a,expr(21,'ABILITY',p,row,b.text('五神兵完成；锻造锤EX额外奖励'))),e.branch([e.exists(a)],[e.setkv(p,CLAIMED,r.flag(True)),log(e,'锤子EX终局；玩家=',q.journal.idx(p),'；额外奖励=',b.lit(100039,EX),'；全军伤害合计=50%')])])])
    close=w.traverse(e,cfg,[e.branch([e.compare(r.get(cfg,row,'升级机制'),'==',b.text('武器锻造'),'STRING_COMPARE')],[
      e.branch([e.compare(r.get(cfg,row,'子归类'),'==',b.text('材料'),'STRING_COMPARE')],[e.action('SET_TABLE_VALUE_ND',cfg,row,b.text('是否解锁'),r.flag(False))]),
      e.branch([e.yes(r.get(cfg,row,'是否合成','BOOLEAN'))],[e.action('SET_TABLE_VALUE_ND',cfg,row,b.text('是否格子展示'),r.flag(False))])])])
    save(e,[e.branch([e.no(boolean(p,BUSY)),e.compare(integer(p,COUNT),'>=',r.i(5)),e.cond('OR',e.no(boolean(p,COMPLETE)),e.no(boolean(p,CLAIMED)))],[
      e.setkv(p,BUSY,r.flag(True)),e.set(cfg,config(p)),e.branch([e.no(boolean(p,COMPLETE))],[close]),e.setkv(p,COMPLETE,r.flag(True)),call(e,19,p),
      e.branch([e.no(boolean(p,CLAIMED))],[grant]),e.setkv(p,BUSY,r.flag(False)),call(e,14,carrier(p))])])
    e=Function(15,[('PLAYER','执行玩家'),('ABILITY_NAME','变更卡牌类型')],'选卡写表结束后执行。只处理锻造配置，按图纸表序尝试各未完成神兵；共享材料不足则不合成。')
    p=e.var('PLAYER','执行玩家');e.var('ABILITY_NAME','变更卡牌类型');cfg=e.var('TABLE','卡牌配置');bp=e.var('INTEGER','图纸行');deck=e.var('STRING','图纸组');row=b.n(100002,'ITER_TABLE_KEY_INT')
    find=w.traverse(e,cfg,[e.branch([e.compare(r.get(cfg,row,'升级机制'),'==',b.text('武器锻造'),'STRING_COMPARE'),e.yes(r.get(cfg,row,'是否合成','BOOLEAN')),
      e.compare(r.get(cfg,row,'所属set'),'==',deck,'STRING_COMPARE')],[call(e,20,p,bp,row)])])
    scan=w.traverse(e,cfg,[e.branch([e.compare(r.get(cfg,row,'升级机制'),'==',b.text('武器锻造'),'STRING_COMPARE'),e.compare(r.get(cfg,row,'子归类'),'==',b.text('图纸'),'STRING_COMPARE')],[e.set(bp,row),e.set(deck,r.get(cfg,row,'所属set')),find])])
    save(e,[e.branch([e.no(boolean(p,BUSY))],[e.branch([e.exists(expr(16,'ABILITY',p,b.lit(100039,BASE)))],[e.setkv(p,BUSY,r.flag(True)),e.setkv(p,RETRY,r.flag(False)),
      e.set(cfg,config(p)),call(e,17,p),scan,call(e,19,p),e.setkv(p,BUSY,r.flag(False)),call(e,22,p),call(e,14,carrier(p))])])])
    return out

def build_embedded():
    out={};b.TID=2099937000
    for aid in (BASE,EX,*BLUEPRINTS,*WEAPONS,*MATERIALS.values()):
        e=b.Eca(aid)
        e.trigger('获得：准备锻造属性，等待持卡记录写入','ABILITY_OBTAIN',[call(e,1,b.unit('ABILITY_OWNER'),b.ability())])
        e.trigger('等级变化：刷新当前拥有者收益','ABILITY_LEVEL_CHANGED',[call(e,14,b.n(100006,'GET_ABILITY_OWNER',b.ability()))])
        e.trigger('失去：标记刷新，周期复核实际实例','ABILITY_LOSE',[call(e,14,b.unit('ABILITY_OWNER'))])
        out[f'ability/{aid}.json']=e.done()
    for oid,template in ((CONTROL,q.CONTROL),(ARMY,q.ARMY)):
        doc=translate(read(f'modifier/{template}.json'))
        if oid==CONTROL:
            for tr in doc['trigger_dict'].values():
                if tr['event'][0]['event_type']=='MODIFIER_CYCLE_TRIGGER':
                    e=b.Eca(oid,True);tr['action'].insert(0,e.branch([e.yes(boolean(b.player(b.owner()),RETRY))],[call(e,15,b.player(b.owner()),b.n(100039,'NONE_ABILITY_KEY'))]))
        ids={int(k):2099937300+(100 if oid==ARMY else 0)+i for i,k in enumerate(doc['trigger_dict'])}
        def remap(x):
            if isinstance(x,list):return [remap(v)for v in x]
            if isinstance(x,dict):return {str(ids[int(k)])if str(k).isdigit()and int(k)in ids else k:remap(v)for k,v in x.items()}
            return ids.get(x,x)if isinstance(x,int)and not isinstance(x,bool)else x
        doc=remap(doc);serial=oid*1000000
        for n in b.walk(doc):
            if 'element_id'in n:serial+=1;n['element_id']=serial
        out[f'modifier/{oid}.json']=doc
    return out

if __name__ == '__main__':
    raise SystemExit('Initial map deployment retired; use maintained helpers and read-only regression fixtures.')
