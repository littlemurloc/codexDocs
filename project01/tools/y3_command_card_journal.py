"""Native military-card result journal and sparse, change-driven snapshots.

Logging helpers touch only their own PLAYER KV. Gameplay actions are retained
verbatim, no extra random numbers, abilities, attributes or platform saves.
"""
from __future__ import annotations
import copy,uuid
import y3_wei_command_cards as w
b,r,d=w.b,w.r,w.d
FOLDER='global_trigger/function/new/军略日志'
NAMES={1:'01_记录军略获卡结果',2:'02_记录实际持卡快照',3:'03_记录参战玩家持卡快照'}
FIDS={i:uuid.uuid5(uuid.NAMESPACE_URL,'project01/y3/card-journal/v1/'+name).hex for i,name in NAMES.items()}
FLAG='军略日志_启用'
CTX,BOUND,SEQ,SNAP,SIG=('军略日志_'+x for x in ('奖励来源','奖励目标类型','流水序号','快照序号','上次持卡签名'))
TRIGGER='global_trigger/trigger/军略卡牌日志与持卡快照.json'
ROOTID=2099895100
SELECT='global_trigger/function/new/功能执行/3选1军略卡牌处理.json'
MERGE='global_trigger/function/new/功能执行/军略3选1-处理合成的新卡牌.json'

def enabled():return b.n(100001,'VARIABLE',r.tp(['BOOLEAN',FLAG]))
def idx(p):return w.s.foreign('9384d061198e11ef967be8c829c05699','INTEGER',p)
def array(kind,name,index):
    typ,sub,_=w.s.TYPES[kind];return b.n(typ,sub,r.tp([kind,name]),index)
def pool(index):return array('TABLE','卡牌技能池-表',index)
def catalog(index):return array('TABLE','军令卡牌base-表',index)
def unit(index):return array('UNIT_ENTITY','playerHeroList',index)
def asstr(v):return b.n(100003,'ANY_VAR_TO_STR',v)
def text(*parts):
    result=b.text('')
    for part in parts:result=r.join(result,b.text(part) if isinstance(part,str) else asstr(part))
    return result
def emit(e,*parts):return e.action('PRINT_MESSAGE_ACTION_TO_DIALOG',b.lit(100175,3),text(*parts))
def call(e,i,*args):return w.s.external(e,FIDS[i],*args)
def getstr(p,key):return r.value(p,key,'STRING')
def increment(e,p,key):return e.setkv(p,key,b.n(100002,'INT_PLUS_ONE',w.integer(p,key)))

class Function(w.Function):
    def __init__(self,i,params,comment):
        super().__init__(i,params,comment)
        self.oid=2099895000+i;self.serial=self.oid*1000000
        self.obj.update(func_id=FIDS[i],func_name=NAMES[i],trigger_name=NAMES[i],trigger_id=self.oid,group_id='command_card_journal_v1',
          func_des=NAMES[i]+'：'+ '，'.join(n+'{'+n+'}' for _,n in params))

def valid_card(e,a,u,records,row,actions):
    return e.branch([e.exists(a)],[e.branch([
      e.compare(d.val_table(records,row,'归属单位','UNIT_ENTITY'),'==',u,'UNIT_COMPARE')],[
      e.branch([e.compare(b.n(100006,'GET_ABILITY_OWNER',a),'==',u,'UNIT_COMPARE')],actions)])])

def build_functions():
    out={}
    def save(e,actions):out[f'{FOLDER}/{NAMES[e.index]}.json']=e.finish(actions)
    e=Function(1,[('PLAYER','执行玩家'),('ABILITY_NAME','卡牌类型'),('STRING','记录来源')],
      '写表后核实实例才记成功。记录玩家索引、流水、波次、阶段、卡牌类型与名称、等级、实际授予来源；只写日志专用状态。')
    p=e.var('PLAYER','执行玩家');aid=e.var('ABILITY_NAME','卡牌类型');reason=e.var('STRING','记录来源');i=e.var('INTEGER','玩家索引')
    u=e.var('UNIT_ENTITY','卡牌载体');t=e.var('TABLE','持卡记录');a=e.var('ABILITY','实际卡牌');candidate=e.var('ABILITY','候选实例');source=e.var('STRING','最终来源')
    kind=e.var('STRING','卡牌身份');row=b.n(100002,'ITER_TABLE_KEY_INT')
    find=w.traverse(e,t,[e.set(candidate,d.val_table(t,row,'技能')),valid_card(e,candidate,u,t,row,[
      e.branch([e.compare(b.n(100039,'ABILITY_NAME_OF_ABILITY',candidate),'==',aid,'ABILITY_COMPARE')],[e.set(a,candidate)])])])
    save(e,[e.branch([e.yes(enabled())],[e.set(i,idx(p)),e.branch([e.compare(i,'>',r.i(0))],[
      e.set(u,unit(i)),e.set(t,pool(i)),e.branch([e.exists(u)],[e.branch([e.exists(t)],[
        e.set(a,b.n(100014,'NONE_ABILITY')),e.set(source,reason),e.set(kind,b.text('未分类')),find,
        e.branch([e.compare(reason,'==',b.text('合成授予'),'STRING_COMPARE'),
          e.compare(getstr(p,BOUND),'==',w.typekey(aid),'STRING_COMPARE'),
          e.compare(getstr(p,CTX),'!=',b.text(''),'STRING_COMPARE')],[e.set(source,getstr(p,CTX))]),
        increment(e,p,SEQ),e.branch([e.exists(a)],[
          e.branch([e.cond('HAS_KV_ANY',a,b.text(d.IDENTITY))],[e.set(kind,r.value(a,d.IDENTITY,'STRING'))]),
          emit(e,'[军略日志/v1] 结果=已持有；流水=',w.integer(p,SEQ),'；玩家=',i,'；波次=',w.s.wave(),'；阶段=',w.phase(),
            '；卡牌=',aid,'；等级=',w.s.level(a),'；身份=',kind,'；来源=',source)],
          [emit(e,'[军略日志/v1] 结果=未读到有效实例；流水=',w.integer(p,SEQ),'；玩家=',i,'；卡牌=',aid,'；来源=',source)])])])])])])

    e=Function(2,[('PLAYER','执行玩家'),('STRING','快照原因'),('BOOLEAN','强制记录')],
      '只从当前军略目录与有效持卡记录读取。排除英雄技能、无效实例和错误归属；按类型去重，显示折叠卡。5秒兜底只在签名变化时输出。')
    p=e.var('PLAYER','执行玩家');reason=e.var('STRING','快照原因');force=e.var('BOOLEAN','强制记录');i=e.var('INTEGER','玩家索引')
    u=e.var('UNIT_ENTITY','卡牌载体');t=e.var('TABLE','持卡记录');cfg=e.var('TABLE','军略目录');known=e.var('TABLE','目录类型索引');seen=e.var('TABLE','已统计类型');held=e.var('TABLE','快照实例')
    a=e.var('ABILITY','当前实例');key=e.var('STRING','当前类型');signature=e.var('STRING','本次签名');count=e.var('INTEGER','持卡种数');ur=e.var('INTEGER','八虎骑种数');ex=e.var('INTEGER','EX种数');fr=e.var('INTEGER','目录行号');n=e.var('INTEGER','快照行号')
    row=b.n(100002,'ITER_TABLE_KEY_INT');getint=lambda table,key:b.n(100002,'GET_INTEGER_TABLE_VAR_1D',table,key)
    declared=w.traverse(e,cfg,[d.set_1d(e,known,w.typekey(w.typename(cfg,row)),row)])
    accept=[e.set(key,d.ability_key(a)),e.branch([e.cond('TABLE_HAS_KEY',known,key)],[e.branch([e.cond('TABLE_HAS_KEY',seen,key)],[],[
      d.set_1d(e,seen,key,r.flag(True)),e.set(count,b.n(100002,'INT_PLUS_ONE',count)),d.set_1d(e,held,count,a),e.set(fr,getint(known,key)),
      e.set(signature,text(signature,'|',key,'@',w.s.level(a),'/',r.get(cfg,fr,'是否格子展示','BOOLEAN'))),
      e.branch([e.compare(r.get(cfg,fr,'子归类'),'==',b.text('八虎骑'),'STRING_COMPARE')],[e.set(ur,b.n(100002,'INT_PLUS_ONE',ur))]),
      e.branch([e.compare(r.get(cfg,fr,'所属set'),'==',b.text('EX'),'STRING_COMPARE')],[e.set(ex,b.n(100002,'INT_PLUS_ONE',ex))],[
        e.branch([e.cond('HAS_KV_ANY',a,b.text(d.IDENTITY))],[e.branch([e.compare(r.value(a,d.IDENTITY,'STRING'),'==',b.text('EX'),'STRING_COMPARE')],[e.set(ex,b.n(100002,'INT_PLUS_ONE',ex))])])])])])]
    scan=w.traverse(e,t,[e.set(a,d.val_table(t,row,'技能')),valid_card(e,a,u,t,row,accept)])
    entries=r.loop(e,n,held,[e.set(a,d.get_1d(held,n)),e.branch([e.exists(a)],[e.set(fr,getint(known,d.ability_key(a))),
      emit(e,'[军略快照/v1] 条目；玩家=',i,'；快照=',w.integer(p,SNAP),'；卡牌=',b.n(100039,'ABILITY_NAME_OF_ABILITY',a),
        '；等级=',w.s.level(a),'；阵营=',r.get(cfg,fr,'升级机制'),'；套牌=',r.get(cfg,fr,'所属set'),'；界面展示=',r.get(cfg,fr,'是否格子展示','BOOLEAN'))],
      [emit(e,'[军略快照/v1] 条目失效；玩家=',i,'；快照=',w.integer(p,SNAP),'；条目=',n)])])
    unavailable=e.branch([e.yes(force)],[emit(e,'[军略快照/v1] 当前记录不可读；玩家=',i,'；原因=',reason,'；最后有效快照=',w.integer(p,SNAP))])
    ready=[e.set(known,b.n(100011,'GET_NEW_TABLE')),e.set(seen,b.n(100011,'GET_NEW_TABLE')),e.set(held,b.n(100011,'GET_NEW_TABLE')),
      e.set(count,r.i(0)),e.set(ur,r.i(0)),e.set(ex,r.i(0)),e.set(signature,text('波次=',w.s.wave(),'；阶段=',w.phase())),declared,scan,
      e.branch([e.cond('OR',e.yes(force),e.compare(signature,'!=',getstr(p,SIG),'STRING_COMPARE'))],[
        increment(e,p,SNAP),e.setkv(p,SIG,signature),
        emit(e,'[军略快照/v1] 开始；玩家=',i,'；快照=',w.integer(p,SNAP),'；波次=',w.s.wave(),'；阶段=',w.phase(),'；原因=',reason,'；卡牌种数=',count),entries,
        emit(e,'[军略快照/v1] 结束；玩家=',i,'；快照=',w.integer(p,SNAP),'；卡牌种数=',count,'；八虎骑种数=',ur,'；EX种数=',ex)])]
    save(e,[e.branch([e.yes(enabled())],[e.set(i,idx(p)),e.branch([e.compare(i,'>',r.i(0))],[
      e.set(u,unit(i)),e.set(t,pool(i)),e.set(cfg,catalog(i)),e.branch([e.exists(u)],[e.branch([e.exists(t)],[e.branch([e.exists(cfg)],ready,[unavailable])],[unavailable])],[unavailable])])])])

    e=Function(3,[('STRING','快照原因'),('BOOLEAN','强制记录')],'只遍历项目实际参战玩家数组。快照按玩家隔离，不输出平台存档、昵称或其他账号数据。')
    reason=e.var('STRING','快照原因');force=e.var('BOOLEAN','强制记录')
    player=b.n(100025,'VARIABLE',r.tp(['PLAYER','playersDetail']),b.n(100002,'GET_LOOP_LIST_INDEX'))
    save(e,[e.branch([e.yes(enabled())],[e.action('LIST_LOOP',b.n(100081,1,r.tp(['PLAYER','playersDetail'])),b.n(100022,1,call(e,2,player,reason,force)))])])
    return out

def refresh_new_ids(doc,old_ids):
    doc=copy.deepcopy(doc);serial=max(old_ids,default=0)+1000
    for n in b.walk(doc):
        if 'element_id' in n and n['element_id'] not in old_ids:serial+=1;n['element_id']=serial
    return doc

def patch_gameplay():
    out={};tracking={}
    # Selection is logged after its pool record exists, before automatic merges.
    for rel in (SELECT,MERGE):
        doc=w.read(rel);before=copy.deepcopy(doc);old={n['element_id'] for n in b.walk(doc) if 'element_id' in n};e=Function(1,[],'')
        p=b.n(100025,'VARIABLE',r.tp(['PLAYER','执行玩家','local']))
        if rel==SELECT:
            aid=b.n(100039,'VARIABLE',r.tp(['ABILITY_NAME','处理技能类型','local']))
            doc['action'].insert(1,call(e,1,p,aid,b.text('选卡获得或升级')))
            doc['action'].append(call(e,2,p,b.text('选卡处理结束'),r.flag(False)))
        else:
            aid=w.typename(w.config(p),b.n(100002,6,r.tp(['INTEGER','合成的新卡牌Index','local'])))
            at=next(i for i,a in enumerate(doc['action']) if a.get('action_type')=='CALL_TRIGGER_FUNC')
            doc['action'].insert(at,call(e,1,p,aid,b.text('合成授予')))
            doc['action'].insert(len(doc['action'])-1,call(e,2,p,b.text('授予流程结束'),r.flag(False)))
        out[rel]=refresh_new_ids(doc,old)
        tracking[rel]={'original':before,'added_ids':[n['element_id'] for n in b.walk(out[rel]) if 'element_id' in n and n['element_id'] not in old]}
    # Source strings are bound to the exact result type. Nested foreign-faction
    # grants cannot inherit the outer Wei gift's attribution.
    for i in (17,19,21):
        rel=f'{w.FOLDER}/{w.NAMES[i]}.json';doc=w.read(rel);before=copy.deepcopy(doc);old={n['element_id'] for n in b.walk(doc) if 'element_id' in n}
        e=Function(1,[],'');e.obj['var_data']=doc['var_data'];u=e.var('UNIT_ENTITY','卡牌载体');p=b.player(u)
        oldkey='日志_上级来源' if i!=21 else '日志_上级目标类型';previous=e.var('STRING',oldkey)
        kvkey=CTX if i!=21 else BOUND
        if i==17:
            a=e.var('ABILITY','当前卡牌');key=e.var('STRING','概率参数键');prob=e.var('FLOAT','本卡概率');roll=e.var('INTEGER','本次掷骰')
            value=text('随机赠送；来源卡牌=',b.n(100039,'ABILITY_NAME_OF_ABILITY',a),'；触发=',key,'；概率=',prob,'；掷骰=',roll)
            matches=lambda n:n.get('action_type')=='CALL_TRIGGER_FUNC' and n['args_list'][0]['sub_type']==w.FIDS[18]
        elif i==19:
            value=text('EX授予；条件=八虎骑数量达标；门槛=',w.threshold())
            matches=lambda n:n.get('action_type')=='SET_VARIABLE' and n['args_list'][1].get('sub_type')==w.FIDS[21]
        else:
            row=e.var('INTEGER','奖励表行号');value=w.typekey(w.typename(w.config(p),row))
            matches=lambda n:n.get('action_type')=='SET_VARIABLE' and n['args_list'][1].get('sub_type')==w.MERGE
        found=[0]
        def wrap(x):
            if isinstance(x,list):
                result=[]
                for a in x:
                    if isinstance(a,dict) and matches(a):
                        found[0]+=1
                        result += [e.branch([e.yes(enabled())],[e.set(previous,getstr(p,kvkey)),e.setkv(p,kvkey,value)]),copy.deepcopy(a),
                          e.branch([e.yes(enabled())],[e.setkv(p,kvkey,previous)])]
                    else:result.append(wrap(a))
                return result
            if isinstance(x,dict):return {k:wrap(v) for k,v in x.items()}
            return x
        doc['action']=wrap(doc['action']);assert found[0]==1,(i,found)
        out[rel]=refresh_new_ids(doc,old)
        tracking[rel]={'original':before,'added_ids':[n['element_id'] for n in b.walk(out[rel]) if 'element_id' in n and n['element_id'] not in old],
          'new_variables':[oldkey]}
    return out,tracking

def build_trigger():
    root=w.read('global_trigger/trigger/初始化随机模型清单.json')
    root.update(action=[],condition=[],enabled=True,group_id=0,p_trigger_id=None,trigger_id=ROOTID,
      trigger_name='军略卡牌日志与持卡快照',var_data=[{},{},[]],sub_trigger={},event=[dict(event_type='INIT_FINISHED',args_list=[],enable=True,element_id=1)])
    e=Function(1,[],'')
    root['action']=[e.branch([e.yes(enabled())],[emit(e,'[军略日志/v1] 会话开始；地图=map3；只记录卡牌结果与变更快照')])]
    children=[('阶段变化','RECEIVE_CUSTOM_EVENT',[b.lit(100238,b.PHASE)],True),
      ('持卡变化兜底','GAME_ELAPSE_REPEAT',[b.f(5)],False),('主动退出','ROLE_ACTIVE_EXIT_GAME_EVENT',[],True),
      ('断线','ROLE_LOSE_CONNECT',[],True),('关卡结算','RECEIVE_CUSTOM_EVENT',[b.lit(100238,1990730222)],True)]
    for offset,(name,event,args,force) in enumerate(children,1):
        tid=ROOTID+offset
        actions=[call(e,3,b.text(name),r.flag(force))]
        child=dict(action=actions,call_enabled=True,condition=[],enabled=False,event=[dict(event_type=event,args_list=args,enable=True,element_id=1)],
          group_id=0,is_conf=True,p_trigger_id=ROOTID,trigger_id=tid,trigger_name='军略日志：'+name,valid=True,var_data=[{},{},[]])
        root['sub_trigger'][str(tid)]=child;root['action'].append(tid)
    return w.reidentify(root,ROOTID)


if __name__=='__main__':
    raise SystemExit("Maintenance library only; original one-time staging/publication has been retired. Use the regression tests and review scoped changes against the current map.")
