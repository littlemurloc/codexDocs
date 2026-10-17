"""Readable native-ECA refactor. Stage and verify before touching the map."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import uuid
import zipfile
import argparse
import shutil
import y3_wu_command_cards as b

WORK=Path(__file__).resolve().parents[1]/'tmp/wu-readable-20261017'
STAGE=WORK/'staged'
CARD_TID=str(uuid.uuid5(uuid.NAMESPACE_URL,'project01/y3/wu/cards/v1'))
FIELD_TID=str(uuid.uuid5(uuid.NAMESPACE_URL,'project01/y3/wu/fields/v1'))
FOLDER='global_trigger/function/new/吴国军略'
NAMES={
 1:'01_确保吴国配置控制',2:'02_检查并刷新全军配置',3:'03_汇总已持有卡牌收益',
 4:'04_累加一张卡的物编参数',5:'05_同步队长与小兵收益',6:'06_为一个单位建立收益',
 7:'07_检查并刷新单位收益',8:'08_重算单位属性并保持生命比例',
 9:'09_计算阵营兵种与后排增伤',10:'10_清空全军收益缓存',11:'11_按登记类别读取卡牌实例'}
FIDS={i:uuid.uuid5(uuid.NAMESPACE_URL,'project01/y3/wu/'+name).hex for i,name in NAMES.items()}
APPLIED='已应用卡牌清单'
COUNT='持有卡牌数量'
TYPES={'UNIT_ENTITY':(100006,11,0),'MODIFIER_ENTITY':(100076,11,0),
       'ABILITY':(100014,2,0),'ABILITY_NAME':(100039,'VARIABLE',0),
       'FLOAT':(100000,2,0.),'INTEGER':(100002,6,0),
       'STRING':(100003,2,''),'BOOLEAN':(100001,'VARIABLE',False)}

def tp(items):return {'__tuple__':True,'items':items}
def i(v):return b.lit(100002,v)
def flag(v):return b.lit(100001,v)
def table(tid):return b.lit(100011,tid)
def get(tid,row,key,kind='STRING'):
    kinds={'STRING':(100003,'GET_STRING_TABLE_VAR_ND'),'ABILITY_NAME':(100039,'GET_ABILITY_NAME_TABLE_VAR_ND'),
           'BOOLEAN':(100001,'GET_BOOLEAN_TABLE_VAR_ND'),'ATTRIBUTE':(100042,'GET_UNIT_WRITE_ATTRIBUTE_TABLE_VAR_ND'),
           'MODE':(100300,'GET_ATTR_ELEMENT_TABLE_VAR_ND')}
    typ,sub=kinds[kind];return b.n(typ,sub,table(tid),row,b.text(key))
def join(a,c):return b.n(100003,'STR_JOIN',a,c,op_arg=[None]*8,op_arg_enable=[False]*8)
def value(entity,key,kind='FLOAT'):
    typ,sub={'FLOAT':(100000,'GET_FLOAT_KV'),'STRING':(100003,'GET_STRING_KV')}[kind]
    return b.n(typ,sub,entity,b.text(key) if isinstance(key,str) else key)
def cache(entity,key):return value(entity,join(b.text(b.PREFIX),key))
def preview_key(key):return join(b.text('待提交_'),key)
def call(e,index,*args):
    node=e.action('CALL_TRIGGER_FUNC',b.n(100177,FIDS[index],*args,op_arg=[],op_arg_enable=[]))
    node['call_rt_arg_idxes']=[]
    return node
def expr(index,kind,*args):
    return b.n(TYPES[kind][0],FIDS[index],*args,call_rt_index=0,op_arg=[],op_arg_enable=[])
def section(e,title,actions):
    return e.action('STORAGE_BOX',b.n(100021,1),b.n(100022,1,*actions),b.n(100022,1),b.text(title))
def loop(e,row,tid,actions):
    node=e.action('FOR_INT_DO_ACTION_NEW',row,i(1),b.n(100002,'GET_TABLE_LENGTH',table(tid)),
                    b.n(100022,1,*actions))
    node.update(op_arg=[None],op_arg_enable=[False])
    return node
def fields_loop(e,name,actions):
    row=e.var('INTEGER',name);return loop(e,row,FIELD_TID,actions(row))
def card_loop(e,name,actions):
    row=e.var('INTEGER',name);return loop(e,row,CARD_TID,actions(row))
def skv(e,entity,key,v):return e.action('SET_ENTITY_KV',entity,b.text(key) if isinstance(key,str) else key,v)
def addkv(e,entity,key,v):return skv(e,entity,key,b.math(value(entity,key),'+',v))
def boolean(e,p):return e.yes(p)

class Function(b.Eca):
    def __init__(self,index,params,comment):
        self.index=index;self.oid=2099750000+index;self.serial=self.oid*1000000
        self.modifier=False
        self.obj=b.read('global_trigger/function/业务逻辑/功能执行/单位移除技能.json')
        self.obj.update(action=[],condition=[],event=[],func_id=FIDS[index],
          func_name=NAMES[index],trigger_name=NAMES[index],trigger_id=self.oid,
          group_id='wu_readable_20261017',func_comment=comment,
          func_des=NAMES[index]+'：'+ '，'.join(name+'{'+name+'}' for _,name in params),
          func_param_list=[tp([name,True]) for _,name in params],var_data=[{},{},[]])
        for key in ('func_return','func_rtv_name_list'):self.obj.pop(key,None)
        self.params=params
        for kind,name in params:self.var(kind,name)
    def var(self,category,name,value_=None):
        typ,sub,default=TYPES[category]
        self.obj['var_data'][0].setdefault(category,{})[name]=default if value_ is None else value_
        self.obj['var_data'][1][name]=0
        if name not in self.obj['var_data'][2]:self.obj['var_data'][2].append(name)
        return b.n(typ,sub,tp([category,name,'local']))
    def set(self,v,x):return self.action('SET_VARIABLE',b.n(100030,1,*v['args_list']),x)
    def ret(self,kind,v):
        self.obj.update(func_return=True,func_rtv_name_list=[tp(['返回值',kind])])
        return self.action(400342,v)
    def finish(self,actions):
        self.obj['action']=actions
        self.obj=json.loads(json.dumps(self.obj))
        self.serial=self.oid*1000000
        for node in b.walk(self.obj):
            if 'element_id' in node:node['element_id']=self.id()
        return self.obj

def functions():
    out={}
    def save(e,actions):out[f'{FOLDER}/{NAMES[e.index]}.json']=e.finish(actions)
    e=Function(1,[('UNIT_ENTITY','卡牌载体'),('ABILITY','关联卡牌')],
        '31 张吴国卡的统一获得入口。保证只有一个控制 Buff，再发送配置刷新事件。')
    u=e.var('UNIT_ENTITY','卡牌载体');a=e.var('ABILITY','关联卡牌')
    save(e,[e.branch([e.no(b.hasbuff(u,b.CONTROL))],[e.addbuff(u,b.CONTROL,u,a)]),e.send(u)])

    e=Function(11,[('UNIT_ENTITY','卡牌载体'),('ABILITY_NAME','技能类型'),('BOOLEAN','合成结果')],
        '技能类别必须与现有添加路径一致：普通选卡为 2，合成结果为 3。实例未就绪时返回空，由汇总函数延后提交。')
    u=e.var('UNIT_ENTITY','卡牌载体');aid=e.var('ABILITY_NAME','技能类型');result=e.var('BOOLEAN','合成结果')
    find=lambda slot:b.n(100014,'GET_ABILITY_BY_AID',u,b.lit(100182,slot),aid)
    save(e,[e.branch([e.yes(result)],[e.ret('ABILITY',find(3))]),e.ret('ABILITY',find(2))])

    e=Function(4,[('ABILITY','卡牌实例'),('MODIFIER_ENTITY','控制Buff')],
        '数值唯一来源是卡牌物编 KV。按参数映射表循环，只累加该卡实际配置的键；不逐卡编写分支。')
    a=e.var('ABILITY','卡牌实例');m=e.var('MODIFIER_ENTITY','控制Buff')
    def accumulate(row):
        key=get(FIELD_TID,row,'参数键')
        return [e.branch([e.cond('HAS_KV_ANY',a,key)],
           [addkv(e,m,preview_key(key),value(a,key))])]
    save(e,[fields_loop(e,'参数行号',accumulate)])

    e=Function(3,[('UNIT_ENTITY','卡牌载体'),('MODIFIER_ENTITY','控制Buff'),('STRING','本次持有清单'),
                  ('INTEGER','持有UR数量'),('BOOLEAN','持有EX')],
        '先在控制 Buff 上计算待提交收益；全部已持有卡的实例就绪后才整体提交。六 UR 且无 EX 时附加 UR 档。')
    u=e.var('UNIT_ENTITY','卡牌载体');m=e.var('MODIFIER_ENTITY','控制Buff')
    listing=e.var('STRING','本次持有清单');ur=e.var('INTEGER','持有UR数量');ex=e.var('BOOLEAN','持有EX')
    ready=e.var('BOOLEAN','实例全部就绪',True);a=e.var('ABILITY','当前卡牌实例')
    def sumcard(row):
        aid=get(CARD_TID,row,'技能类型','ABILITY_NAME')
        return [e.branch([e.yes(b.n(100001,'CHECK_HAS_ABILITY_TYPE',u,aid)),e.yes(get(CARD_TID,row,'有收益参数','BOOLEAN'))],
            [e.set(a,expr(11,'ABILITY',u,aid,get(CARD_TID,row,'合成结果','BOOLEAN'))),
             e.branch([e.exists(a)],[call(e,4,a,m)],[e.set(ready,flag(False))])])]
    def submit(row):
        key=get(FIELD_TID,row,'参数键')
        return [skv(e,u,join(b.text(b.PREFIX),key),value(m,preview_key(key)))]
    save(e,[section(e,'① 清空本次待提交收益',[e.set(ready,flag(True)),
             fields_loop(e,'清空参数行',lambda row:[skv(e,m,preview_key(get(FIELD_TID,row,'参数键')),b.f(0))])]),
        section(e,'② 循环已持有卡牌，读取物编数值',[card_loop(e,'卡牌行号',sumcard)]),
        section(e,'③ 末阶 UR 规则：六张 UR 且没有 EX',[
             e.branch([e.compare(ur,'==',i(6)),e.no(ex)],
              [addkv(e,m,'待提交_套牌吴国伤害',value(m,'末阶UR吴国伤害')),
               addkv(e,m,'待提交_套牌后排伤害',value(m,'末阶UR后排伤害'))])]),
        section(e,'④ 实例全部就绪后整体提交；否则下次周期重试',[
             e.branch([e.yes(ready)],[fields_loop(e,'提交参数行',submit),skv(e,m,APPLIED,listing),
                  e.addkv(u,b.REV,b.f(1))])])])

    e=Function(2,[('UNIT_ENTITY','卡牌载体'),('MODIFIER_ENTITY','控制Buff'),('BOOLEAN','强制阵型刷新')],
       '循环登记表形成可读的持有清单。清单变化才重新汇总；每次都同步新队长和补兵；开战强制刷新单位阵型分类。')
    u=e.var('UNIT_ENTITY','卡牌载体');m=e.var('MODIFIER_ENTITY','控制Buff');force=e.var('BOOLEAN','强制阵型刷新')
    listing=e.var('STRING','本次持有清单');count=e.var('INTEGER','持有卡牌数');ur=e.var('INTEGER','持有UR数量');ex=e.var('BOOLEAN','持有EX')
    def inspect(row):
        aid=get(CARD_TID,row,'技能类型','ABILITY_NAME')
        return [e.branch([e.yes(b.n(100001,'CHECK_HAS_ABILITY_TYPE',u,aid))],[
            e.set(listing,join(listing,join(get(CARD_TID,row,'卡牌名称'),b.text('；')))),
            e.set(count,b.n(100002,'INT_PLUS_ONE',count)),
            e.branch([e.yes(get(CARD_TID,row,'UR组件','BOOLEAN'))],[e.set(ur,b.n(100002,'INT_PLUS_ONE',ur))]),
            e.branch([e.yes(get(CARD_TID,row,'EX结果','BOOLEAN'))],[e.set(ex,flag(True))])])]
    save(e,[section(e,'① 读取当前持有卡牌',[e.set(listing,b.text('')),e.set(count,i(0)),e.set(ur,i(0)),e.set(ex,flag(False)),
                card_loop(e,'登记行号',inspect),skv(e,m,COUNT,b.math(count,'+',b.f(0)))]),
            section(e,'② 持有清单变化时重新汇总',[e.branch([e.compare(listing,'!=',value(m,APPLIED,'STRING'),'STRING_COMPARE')],
                [call(e,3,u,m,listing,ur,ex)])]),
            section(e,'③ 覆盖新队长、召唤及补兵',[call(e,5,u)]),
            section(e,'④ 开战时重新读取阵型',[e.branch([e.yes(force)],[e.addkv(u,b.REV,b.f(1))])])])

    e=Function(6,[('UNIT_ENTITY','卡牌载体'),('UNIT_ENTITY','目标单位')],
        '存活友军登记卡牌载体，缺少收益 Buff 时添加一次；重复调用不叠加 Buff。')
    u=e.var('UNIT_ENTITY','卡牌载体');target=e.var('UNIT_ENTITY','目标单位')
    save(e,[e.branch([e.alive(target)],[e.setkv(target,b.SOURCE,u),
            e.branch([e.no(b.hasbuff(target,b.ARMY))],[e.addbuff(target,b.ARMY,u)])])])

    e=Function(5,[('UNIT_ENTITY','卡牌载体')],
        '使用工程现有队长筛选函数；依次处理每个队长及其带领小队，不遍历其他玩家部队。')
    u=e.var('UNIT_ENTITY','卡牌载体');picked=b.unit('FOR_EACH_SELECTED_UNIT')
    save(e,[e.pick(b.captains(u),[call(e,6,u,picked),
          e.pick(b.n(100026,'GET_UNIT_GROUP_KV',picked,b.text('带领小队')),[call(e,6,u,picked)])])])

    e=Function(9,[('UNIT_ENTITY','卡牌载体'),('UNIT_ENTITY','目标单位'),('UNIT_ENTITY','所属队长')],
        '所有伤害 + 阵营收益 + 弓兵收益 + 后排收益 + EX 弓兵/后排并集。所有增伤统一交给原全局伤害结算消费。')
    u=e.var('UNIT_ENTITY','卡牌载体');target=e.var('UNIT_ENTITY','目标单位');captain=e.var('UNIT_ENTITY','所属队长')
    wu=e.var('BOOLEAN','属于吴国');bow=e.var('BOOLEAN','属于弓兵');rear=e.var('BOOLEAN','属于战前后排');damage=e.var('FLOAT','合计增伤')
    formation=b.n(100002,'GET_INTEGER_KV',captain,b.text('归属阵型编号'))
    def c(key):return value(u,b.PREFIX+key)
    def inc(v):return e.set(damage,b.math(damage,'+',v))
    save(e,[section(e,'① 明确本单位的阵营、兵种与战前排位',[
            e.set(wu,flag(False)),e.set(bow,flag(False)),e.set(rear,flag(False)),
            e.branch([e.cond('OR',e.cond('UNIT_HAS_TAG',target,b.text('吴国')),e.cond('UNIT_HAS_TAG',captain,b.text('吴国')))],[e.set(wu,flag(True))]),
            e.branch([e.cond('UNIT_HAS_TAG',target,b.text('弓兵'))],[e.set(bow,flag(True))]),
            e.branch([e.compare(formation,'>=',i(7)),e.compare(formation,'<=',i(9))],[e.set(rear,flag(True))])]),
        e.set(damage,c(b.field_key('extra_dmg','ATTR_BASE'))),
        section(e,'② 吴国单位：单卡被动与套牌收益相加',[e.branch([e.yes(wu)],[inc(b.math(c('单卡吴国伤害'),'+',c('套牌吴国伤害')))])]),
        section(e,'③ 弓兵：早阶套牌收益',[e.branch([e.yes(bow)],[inc(c('套牌弓兵伤害'))])]),
        section(e,'④ 后排：UR 档收益',[e.branch([e.yes(rear)],[inc(c('套牌后排伤害'))])]),
        section(e,'⑤ EX：弓兵或后排只加一次',[e.branch([e.cond('OR',e.yes(bow),e.yes(rear))],[inc(c('终极弓兵后排伤害'))])]),
        e.ret('FLOAT',damage)])

    e=Function(8,[('MODIFIER_ENTITY','收益Buff'),('UNIT_ENTITY','目标单位'),('UNIT_ENTITY','卡牌载体')],
        '按映射表覆盖当前 Buff 的属性贡献，保持其他 Buff 不变。保持原生命比例，阵营等条件增伤交给函数 09。')
    m=e.var('MODIFIER_ENTITY','收益Buff');target=e.var('UNIT_ENTITY','目标单位');u=e.var('UNIT_ENTITY','卡牌载体')
    captain=e.var('UNIT_ENTITY','所属队长');ratio=e.var('FLOAT','原生命比例');damage=e.var('FLOAT','合计增伤')
    def set_attr(row):
        key=get(FIELD_TID,row,'参数键')
        return [e.branch([e.yes(get(FIELD_TID,row,'直接写入面板','BOOLEAN'))],[
            e.action('SET_MODIFIER_OWNER_ATTR',m,get(FIELD_TID,row,'单位属性','ATTRIBUTE'),
                     get(FIELD_TID,row,'属性计算方式','MODE'),cache(u,key))])]
    save(e,[section(e,'① 记录生命比例并确定所属队长',[
            e.set(ratio,b.math(b.n(100000,'GET_HP_CUR',target),'/',b.attr(target,'hp_max'))),
            e.set(captain,target),e.branch([e.exists(b.ukv(target,'所属英雄'))],[e.set(captain,b.ukv(target,'所属英雄'))])]),
        section(e,'② 循环映射表，覆盖本 Buff 的基础属性贡献',[fields_loop(e,'属性映射行',set_attr)]),
        section(e,'③ 计算条件增伤并写入统一伤害属性',[
            e.set(damage,expr(9,'FLOAT',u,target,captain)),
            e.action('SET_MODIFIER_OWNER_ATTR',m,b.lit(100042,'extra_dmg'),b.lit(100300,'ATTR_BASE'),damage)]),
        section(e,'④ 恢复生命比例并记录已应用版本',[
            e.action('ADD_CUR_HP',target,b.math(b.math(b.attr(target,'hp_max'),'*',ratio),'-',b.n(100000,'GET_HP_CUR',target))),
            e.setkv(m,b.REV,value(u,b.REV))])])

    e=Function(7,[('MODIFIER_ENTITY','收益Buff'),('UNIT_ENTITY','目标单位'),('BOOLEAN','强制刷新')],
        '先验证来源，再检查版本。来源无效则移除自身；只有配置版本变化或事件要求时重算。')
    m=e.var('MODIFIER_ENTITY','收益Buff');target=e.var('UNIT_ENTITY','目标单位');force=e.var('BOOLEAN','强制刷新')
    u=e.var('UNIT_ENTITY','卡牌载体');remove=e.action('REMOVE_BUFF_INS',m)
    save(e,[e.set(u,b.ukv(target,b.SOURCE)),e.branch([e.exists(u)],[
        e.branch([e.yes(b.hasbuff(u,b.CONTROL))],[
            e.branch([e.cond('OR',e.yes(force),e.compare(value(m,b.REV),'!=',value(u,b.REV)))],[call(e,8,m,target,u)])],[remove])],[remove])])

    e=Function(10,[('UNIT_ENTITY','卡牌载体')],
        '控制 Buff 移除时将全部收益缓存清零并增加版本，单位 Buff 将清理各自贡献。')
    u=e.var('UNIT_ENTITY','卡牌载体')
    save(e,[fields_loop(e,'缓存参数行',lambda row:[skv(e,u,join(b.text(b.PREFIX),get(FIELD_TID,row,'参数键')),b.f(0))]),
            e.addkv(u,b.REV,b.f(1))])
    return out

def embedded(aid):
    e=b.Eca(aid);u=b.unit('ABILITY_OWNER')
    e.trigger('获得卡牌：调用 01 确保吴国配置控制','ABILITY_OBTAIN',[call(e,1,u,b.ability())])
    e.trigger('等级变化：通知重新统计收益','ABILITY_LEVEL_CHANGED',
              [e.send(b.n(100006,'GET_ABILITY_OWNER',b.ability()))])
    e.trigger('失去卡牌：通知刷新，删除时序由周期校验覆盖','ABILITY_LOSE',[e.send(u)])
    return e.done()

def modifiers():
    out={}
    e=b.Eca(b.CONTROL,True);u=b.owner();m=b.buff()
    gain=e.trigger('获得控制：注册监听，调用 02 刷新全军配置','OBTAIN_MODIFIER')
    change=e.trigger('卡牌变化：调用 02 刷新全军配置','RECEIVE_CUSTOM_EVENT',[call(e,2,u,m,flag(False))],
        args=[b.lit(100238,b.CHANGE)],conditions=[e.compare(b.n(100006,'GET_CUS_EVENT_PARAM',b.lit(100240,'载体单位')),'==',u,'UNIT_COMPARE')],
        parent=gain,handle='配置刷新监听')
    phase=e.trigger('进入战斗：调用 02，强制刷新战前排位','RECEIVE_CUSTOM_EVENT',[call(e,2,u,m,flag(True))],
        args=[b.lit(100238,b.PHASE)],conditions=[e.compare(b.n(100002,'GET_CUS_EVENT_PARAM',b.lit(100240,'阶段编号')),'==',i(2))],
        parent=gain,handle='开战监听')
    e.obj['trigger_dict'][str(gain)]['action']=[e.setkv(m,APPLIED,b.text('未初始化')),change,phase,call(e,2,u,m,flag(False))]
    e.trigger('周期校验：调用 02，覆盖卡牌删除与新单位','MODIFIER_CYCLE_TRIGGER',[
        call(e,2,u,m,flag(False)),e.branch([e.compare(value(m,COUNT),'==',b.f(0))],[e.action('REMOVE_BUFF_INS',m)])])
    e.trigger('失去控制：注销监听，调用 10 清空缓存','LOSS_MODIFIER',[
        e.unreg('配置刷新监听'),e.unreg('开战监听'),call(e,10,u)])
    out[f'modifier/{b.CONTROL}.json']=e.done()
    e=b.Eca(b.ARMY,True);u=b.owner();m=b.buff()
    gain=e.trigger('获得收益：注册监听，调用 07 检查与应用','OBTAIN_MODIFIER')
    change=e.trigger('配置变化：调用 07 强制刷新单位收益','RECEIVE_CUSTOM_EVENT',[call(e,7,m,u,flag(True))],
        args=[b.lit(100238,b.CHANGE)],conditions=[e.compare(b.n(100006,'GET_CUS_EVENT_PARAM',b.lit(100240,'载体单位')),'==',b.source(),'UNIT_COMPARE')],
        parent=gain,handle='配置刷新监听')
    e.obj['trigger_dict'][str(gain)]['action']=[e.setkv(m,b.REV,b.f(-1)),change,call(e,7,m,u,flag(False))]
    e.trigger('周期校验：调用 07，版本不变时不重算','MODIFIER_CYCLE_TRIGGER',[call(e,7,m,u,flag(False))])
    e.trigger('失去收益：清除本 Buff 贡献并注销监听','LOSS_MODIFIER',[
        e.action('CLEAR_MODIFIER_OWNER_ATTR',m),e.unreg('配置刷新监听')])
    out[f'modifier/{b.ARMY}.json']=e.done()
    return out

def table_doc(tid,headers,types,rows,descriptions):
    return {'column_width':{str(j):220 for j in range(len(headers))},
        'table_data':{'column_desc':{str(j):descriptions.get(name,'') for j,name in enumerate(headers)},
                      'data':[headers,types]+rows,'key':[0]},'table_type':0,'tid':tid}

def build_tables(specs):
    ordered=sorted(specs,key=lambda aid:(0 if aid==b.BASE else 2 if aid in b.RESULTS else 3 if aid==b.EX else 1,aid))
    rows=[[str(j),specs[aid]['name'],aid,aid in b.RESULTS or aid in (b.BASE,b.EX),bool(specs[aid]['params']),aid in b.UR,aid==b.EX,
           '物编 KV 为数值来源；此表只登记卡牌与分类'] for j,aid in enumerate(ordered,1)]
    cards=table_doc(CARD_TID,['key','卡牌名称','技能类型','合成结果','有收益参数','UR组件','EX结果','说明'],
        ['int','string','ability_type','bool','bool','bool','bool','string'],rows,
        {'合成结果':'True 按类别 3 读取；False 按普通选卡类别 2 读取。与原添加路径一致。',
         'UR组件':'计入六张 UR 集齐判断，不包括 EX。','技能类型':'沿用现有吴国技能 ID。'})
    fields=sorted({key for spec in specs.values() for key in spec['params']}|set(b.CONDITIONAL))
    rows=[]
    for j,key in enumerate(fields,1):
        if key.startswith('属性_'):
            attr,mode=key[len('属性_'):].split('_ATTR_',1);mode='ATTR_'+mode
            label=next((name for name,pair in b.FIELDS.items() if pair==(attr,mode)),
                       ('全属性比例：' if mode=='ATTR_ALL_RATIO' else '全属性：')+attr)
            direct=attr!='extra_dmg'
        else:attr,mode,direct,label='strength','ATTR_BASE',False,key
        rows.append([str(j),label,key,attr,mode,direct,
            '由函数 09 计算后统一写入 extra_dmg' if not direct else '由函数 08 循环覆盖当前收益 Buff 的属性贡献'])
    mapping=table_doc(FIELD_TID,['key','收益名称','参数键','单位属性','属性计算方式','直接写入面板','说明'],
         ['int','string','string','unit_attribute','unit_attribute_type','bool','string'],rows,
         {'参数键':'对应卡牌物编 KV，数值只在物编维护。','直接写入面板':'False 的条件增伤由函数 09 统一处理；该行的单位属性与计算方式不参与直接写入。'})
    return {'tables/吴国军略_卡牌登记表.json':cards,'tables/吴国军略_收益参数映射表.json':mapping}

def register_tables(group):
    group=copy.deepcopy(group)
    registrations=[(CARD_TID,'吴国军略_卡牌登记表'),(FIELD_TID,'吴国军略_收益参数映射表')]
    existing={n['items'][0]:n['items'][1] for n in b.walk(group)
              if n.get('__tuple__') and len(n.get('items',[]))==2}
    missing=[tp([tid,name]) for tid,name in registrations if tid not in existing]
    for tid,name in registrations:
        if tid in existing:assert existing[tid]==name, 'Table ID registered with another name'
    if missing:
        target=next((g for g in group if g.get('name')=='吴国军略'),None)
        if target is None:
            target={'name':'吴国军略','key':'wu_card_tables_20261018','group':[]};group.append(target)
        target['group']+=missing
    return group

def editor_invalid_variable_defaults(node):
    if isinstance(node,list):return [editor_invalid_variable_defaults(v) for v in node]
    if not isinstance(node,dict):return node
    args=node.get('args_list',[])
    if node.get('sub_type')==2 and args and isinstance(args[0],dict) and args[0].get('__tuple__'):
        category=args[0]['items'][0]
        if node.get('arg_type')==100039 and category=='ABILITY_NAME':return None
        if node.get('arg_type')==100001 and category=='BOOLEAN':
            return {**node,'sub_type':1,'args_list':[True]}
    return {k:editor_invalid_variable_defaults(v) for k,v in node.items()}

def only_editor_variable_loss(prior,current):
    if prior==current:return True
    if isinstance(prior,dict) and prior.get('arg_type') in (100001,100039) and prior.get('sub_type')==2:
        if current is None and prior.get('args_list') and isinstance(prior['args_list'][0],dict) and prior['args_list'][0].get('__tuple__'):return True
        if editor_invalid_variable_defaults(prior)==current:return True
    if isinstance(prior,dict) and isinstance(current,dict):
        return set(prior)==set(current) and all(only_editor_variable_loss(prior[k],current[k]) for k in prior)
    if isinstance(prior,list) and isinstance(current,list):
        return len(prior)==len(current) and all(only_editor_variable_loss(a,c) for a,c in zip(prior,current))
    return False

def stage(update=False,recover_native_variables=False):
    WORK.mkdir(parents=True,exist_ok=True)
    published=(WORK/'published.json').exists()
    assert update or not published, 'Already published'
    if published:
        previous=json.loads((WORK/'manifest.json').read_text('utf8'))
        for rel in previous:
            current=json.loads((b.MAP/rel).read_text('utf8'));prior=json.loads((STAGE/rel).read_text('utf8'))
            for doc in (current,prior):
                for node in b.walk(doc):node.pop('valid',None)
            if current!=prior:
                assert recover_native_variables and rel.startswith(FOLDER+'/') and only_editor_variable_loss(prior,current), 'Live changed, review before update: '+rel
                print('Restoring editor-cleared invalid variable references:',rel)
        if not (WORK/'before-readable-original.zip').exists():
            shutil.copyfile(WORK/'before-readable.zip',WORK/'before-readable-original.zip')
            shutil.copyfile(WORK/'manifest.json',WORK/'manifest-first-publish.json')
    specs=b.load_specs()
    # Use the latest live object values, never silently reset user numeric edits.
    for aid,spec in specs.items():
        live=b.read(f'editor_table/abilityall/{aid}.json')['kv']
        for key in spec['params']:spec['params'][key]=float(live[key]['value'])
    b.TID=2099700000
    payload=functions();payload.update(build_tables(specs));payload.update(modifiers())
    payload['editor/tableeditorgroupinfo.json']=register_tables(b.read('editor/tableeditorgroupinfo.json'))
    for aid in specs:payload[f'ability/{aid}.json']=embedded(aid)
    index=b.read('global_trigger/function/new/index.txt')
    if not published:assert '吴国军略.folder' not in index
    index.setdefault('吴国军略.folder',max(index.values(),default=-1)+1)
    payload['global_trigger/function/new/index.txt']=index
    payload[FOLDER+'/index.txt']={NAMES[k]+'.json':k-1 for k in sorted(NAMES)}
    manifest={}
    with zipfile.ZipFile(WORK/'before-readable.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
        for rel,obj in payload.items():
            path=b.MAP/rel;before=path.read_bytes() if path.exists() else None
            if before is not None:z.writestr(rel,before)
            target=STAGE/rel;target.parent.mkdir(parents=True,exist_ok=True)
            content=(json.dumps(obj,ensure_ascii=True,indent=4)+'\n').encode('utf8');target.write_bytes(content)
            manifest[rel]={'before':hashlib.sha256(before).hexdigest() if before is not None else None,
                           'after':hashlib.sha256(content).hexdigest()}
    (WORK/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    (WORK/'specs.json').write_text(json.dumps(specs,ensure_ascii=False,indent=2),encoding='utf8')
    print('Staged',len(payload),'files; 31 card ECAs, 2 Buff ECAs, 11 named functions and 2 mapping tables.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--update',action='store_true')
    parser.add_argument('--recover-native-variables',action='store_true')
    args=parser.parse_args();stage(args.update,args.recover_native_variables)
