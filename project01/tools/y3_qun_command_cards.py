"""Maintain Qun native-ECA builders; no one-time staging or publication entry.

Two independent chains; first terminal completion decides the unique UR.
The other chain may finish its unlocked set, with no subsequent unlock.
"""
from __future__ import annotations
import copy,uuid
import y3_wei_command_cards as w
import y3_command_card_journal as journal
b,r,d,s=w.b,w.r,w.d,w.s
MAP=w.MAP
BASE=134279984
CONTROL,ARMY=134285301,134285302
CHANGE=2099456310
PREFIX='群雄军略_'
RULES,SOURCE,REV,DIRTY=(PREFIX+x for x in ('属性规则','载体','版本','待刷新'))
BUSY,CLAIMED,INITIALIZED=(PREFIX+x for x in ('结算中','本局UR已领取','路线已初始化'))
PENDING,ENDING,FINAL=(PREFIX+x for x in ('待授予UR类型','待授予UR来源','最终UR类型'))
DONE=PREFIX+'完成套牌_'
STEP=PREFIX+'解锁阶段_'
FOLDER='global_trigger/function/new/群雄军略'
NAMES={**{i:n.replace('魏国','群雄') for i,n in w.NAMES.items() if i<=14},
 15:'15_选卡写表后检查群雄路线',16:'16_读取指定类型的有效实例',17:'17_初始化双路线首组',
 18:'18_检查本组组件实际集齐',19:'19_未达终局才解锁下一组',20:'20_结算一次套牌完成',
 21:'21_带来源授予指定表行',22:'22_授予本局唯一终局UR'}
FIDS={i:uuid.uuid5(uuid.NAMESPACE_URL,'project01/y3/qun/'+name).hex for i,name in NAMES.items()}
TID=2099906000
ROUTE,LEVEL='群雄路线','群雄阶段'
NORMAL_WEST,NORMAL_YELLOW,SPECIAL=134260219,134239109,134264238
UR=(NORMAL_WEST,NORMAL_YELLOW,SPECIAL)
# Design semantics only. Existing catalog remains the source of members and links.
DECKS=[('西凉新军','西凉',1,10,0,0),('西凉旧部','西凉',2,10,0,0),
 ('西凉骁将','西凉',3,15,15,0),('西凉谋臣','西凉',4,25,0,0),('西凉霸主','西凉',5,25,0,0),
 ('黄巾初起','黄巾',1,10,0,0),('黄巾渠帅','黄巾',2,10,0,0),
 ('黄巾骁将','黄巾',3,15,0,0),('黄巾统帅','黄巾',4,25,0,25),('黄巾霸主','黄巾',5,25,0,0)]
MECHANICS=['单卡群雄伤害','套牌群雄伤害','套牌骑兵伤害','套牌枪兵伤害','终极群雄伤害','终极骑兵伤害']
read=w.read
sha=w.sha
config=w.config
carrier=w.carrier
typename=w.typename
typekey=w.typekey

def integer(entity,key):return b.n(100002,'GET_INTEGER_KV',entity,b.text(key) if isinstance(key,str) else key)
def expr(i,kind,*args):return s.foreign(FIDS[i],kind,*args)
def call(e,i,*args):return s.external(e,FIDS[i],*args)
def boolean(p,key):return b.n(100001,'GET_BOOLEAN_KV',p,b.text(key) if isinstance(key,str) else key)
def strkv(p,key):return r.value(p,key,'STRING')
def step(p,route):return integer(p,r.join(b.text(STEP),route))
def complete(p,deck):return boolean(p,r.join(b.text(DONE),deck))
def log(e,*parts):
    return e.branch([e.yes(journal.enabled())],[journal.emit(e,'[群雄军略/v1] ',*parts)])

class Function(w.Function):
    def __init__(self,i,params,comment):
        # Build with an observed function schema; retain native var declarations.
        self.index=i;self.modifier=False;self.oid=TID+i;self.serial=self.oid*1000000
        self.obj=read('global_trigger/function/业务逻辑/功能执行/单位移除技能.json')
        self.obj.update(action=[],condition=[],event=[],func_id=FIDS[i],func_name=NAMES[i],trigger_name=NAMES[i],
          trigger_id=self.oid,group_id='qun_cards_20261027',func_comment=comment,
          func_des=NAMES[i]+'：'+ '，'.join(n+'{'+n+'}' for _,n in params),
          func_param_list=[r.tp([n,True]) for _,n in params],var_data=[{},{},[]])
        for key in ('func_return','func_rtv_name_list'):self.obj.pop(key,None)
        self.params=params
        for kind,name in params:self.var(kind,name)

def translated(x):
    if isinstance(x,list):return [translated(v) for v in x]
    if isinstance(x,dict):return {translated(k):translated(v) for k,v in x.items()}
    if isinstance(x,str):
        if x in w.FIDS.values():return FIDS[next(i for i,v in w.FIDS.items() if v==x)]
        return x.replace('魏国','群雄').replace('wei_cards_20261026','qun_cards_20261027')
    if isinstance(x,int) and not isinstance(x,bool):return {w.CONTROL:CONTROL,w.ARMY:ARMY,w.CHANGE:CHANGE}.get(x,x)
    return x

def specs_from_book():
    import openpyxl
    assert sha(s.BOOK.read_bytes())==s.BOOK_SHA,'Workbook changed: review before staging'
    book=openpyxl.load_workbook(s.BOOK,read_only=True,data_only=True);sheet=book['套牌'];sheet.reset_dimensions()
    src=list(sheet.iter_rows(min_row=90,max_row=132,max_col=9,values_only=True));book.close()
    language=read('zhlanguage.json');rows=read('tables/群雄temp.json')['table_data']['data'];specs={}
    byname={x[2]:(90+i,x) for i,x in enumerate(src)};assert len(byname)==43
    group_info={};group_members={}
    for row in rows[2:]:
        if row[5]=='true':continue
        aid=row[1];name=language[str(read(f'editor_table/abilityall/{aid}.json')['name'])]
        spec=dict(id=aid,name=name,params={},base=[],identity='起始载体',row=None,deck='base')
        if aid!=BASE:
            num,x=byname[name];spec.update(row=num,base=list(x[4:7]),special=x[7],deck=x[1],quality=x[3])
            spec['params']=b.parse_base(spec['base']);spec['identity']='终极UR' if aid in UR else '普通组件'
            if aid not in UR:
                route,stage=next((v[1],v[2]) for v in DECKS if v[0]==x[1])
                spec.update(route=route,stage=stage);group_info[row[6]]=x[1]
                group_members.setdefault(row[6],[]).append(aid)
            else:spec['params'].update(单卡群雄伤害=30.,终极群雄伤害=50.,终极骑兵伤害=40.)
        specs[aid]=spec
    for row in rows[2:]:
        if row[5]!='true':continue
        aid=row[1];deck=group_info[row[6]];_,route,stage,damage,cav,spear=next(v for v in DECKS if v[0]==deck)
        specs[aid]=dict(id=aid,name=language[str(read(f'editor_table/abilityall/{aid}.json')['name'])],
          params={k:float(v) for k,v in zip(MECHANICS[1:4],(damage,cav,spear)) if v},base=[],row=None,
          identity='套牌结果',deck=deck,route=route,stage=stage,oldset=row[6],members=group_members[row[6]])
    for aid,spec in specs.items():
        text=[v for v in spec['base'] if v not in (None,'','-')]
        if spec['identity']=='套牌结果':
            text=[spec['deck']+'（'+spec['name']+'）完成收益']
            text += [label+'+'+str(int(spec['params'][key]))+'%' for key,label in zip(MECHANICS[1:4],('群雄伤害','全军骑兵伤害','全军枪兵伤害')) if key in spec['params']]
            text.append('首次自然合成获得10～20声望；既有完成收益保留；取得UR后只收完当时所在组，不再解锁下一组')
        if aid==BASE:text=['群雄起始载体；西凉与黄巾两线逐组推进；声望30/60/90/120升级，最高5级；本局至多一张UR']
        if aid in UR:
            text.append('被动：群雄伤害+30%；共同终极：群雄伤害+50%、全军骑兵伤害+40%；与已完成套牌收益相加')
            condition='两线都已解锁最后一组时，先完成任意最后一组，替换原路线UR' if aid==SPECIAL else ('西凉' if aid==NORMAL_WEST else '黄巾')+'先完成最后一组，且另一线未解锁最后一组'
            text.append('取得条件：'+condition+'；自动授予，本局仅一张')
        spec['description']='；'.join(text)
    assert len(specs)==54 and sum(x['row'] is not None for x in specs.values())==43
    return specs

def make_rules(specs):
    rules=[]
    for key in sorted(set(MECHANICS)|{k for v in specs.values() for k in v['params']}):
        if key.startswith('属性_'):
            attr,mode=key[3:].rsplit('_ATTR_',1);mode='ATTR_'+mode;direct=attr!='extra_dmg'
        else:attr,mode,direct='strength','ATTR_BASE',False
        rules.append(dict(收益名称=key,参数键=key,单位属性=attr,属性计算方式=mode,直接写入面板=direct))
    return rules

def build_functions(rules):
    out={}
    for i in range(1,15):
        doc=translated(read(f'{w.FOLDER}/{w.NAMES[i]}.json'))
        if i==2:
            # Tighten the copied record guard: matching the stored owner alone
            # must not admit an ability actually owned by another unit.
            guard=next(n for n in b.walk(doc) if n.get('action_type')=='IF_THEN_ELSE' and any(
              c.get('condition_type')=='UNIT_COMPARE' and any(v.get('args_list')==['归属单位'] for v in b.walk(c))
              for c in n['args_list'][0]['args_list']))
            e=Function(2,[],'');a=b.n(100014,2,r.tp(['ABILITY','当前卡牌','local']));u=b.n(100006,11,r.tp(['UNIT_ENTITY','卡牌载体','local']))
            guard['args_list'][1]['args_list']=[e.branch([e.compare(b.n(100006,'GET_ABILITY_OWNER',a),'==',u,'UNIT_COMPARE')],guard['args_list'][1]['args_list'])]
        out[f'{FOLDER}/{NAMES[i]}.json']=w.reidentify(doc,TID+i)
    def save(e,actions):out[f'{FOLDER}/{NAMES[e.index]}.json']=e.finish(actions)
    e=Function(4,[('ABILITY','卡牌实例'),('MODIFIER_ENTITY','控制Buff'),('TABLE','属性规则表')],
      '实际持有提供单卡属性。套牌结果的收益仅在本玩家自然完成该组后累计；隐藏组件不删除。')
    a=e.var('ABILITY','卡牌实例');mod=e.var('MODIFIER_ENTITY','控制Buff');fields=e.var('TABLE','属性规则表')
    fr=e.var('INTEGER','参数行号');ok=e.var('BOOLEAN','可计入');key=r.get(fields,fr,'参数键')
    save(e,[e.set(ok,r.flag(True)),e.branch([e.compare(strkv(a,d.IDENTITY),'==',b.text('套牌结果'),'STRING_COMPARE')],[
      e.set(ok,complete(b.player(b.n(100006,'GET_ABILITY_OWNER',a)),strkv(a,'原所属set')))]),
      e.branch([e.yes(ok)],[r.loop(e,fr,fields,[e.branch([e.cond('HAS_KV_ANY',a,key)],[
        r.skv(e,mod,r.preview_key(key),b.math(r.value(mod,r.preview_key(key)),'+',r.value(a,key)))])])])])
    e=Function(9,[('UNIT_ENTITY','卡牌载体'),('UNIT_ENTITY','目标单位'),('UNIT_ENTITY','所属队长')],
      '以输出单位及所属队长判断群雄阵营；骑兵/枪兵直接按输出单位兵种判断，统一汇入extra_dmg。')
    u=e.var('UNIT_ENTITY','卡牌载体');target=e.var('UNIT_ENTITY','目标单位');cap=e.var('UNIT_ENTITY','所属队长');damage=e.var('FLOAT','合计增伤')
    def c(k):return r.value(u,PREFIX+k)
    def inc(v):return e.set(damage,b.math(damage,'+',v))
    save(e,[e.set(damage,c(b.field_key('extra_dmg','ATTR_BASE'))),r.section(e,'① 群雄输出：单卡、已完成套牌及终极收益相加',[
      e.branch([e.cond('OR',e.cond('UNIT_HAS_TAG',target,b.text('群雄')),e.cond('UNIT_HAS_TAG',cap,b.text('群雄')))],[
        inc(b.math(b.math(c('单卡群雄伤害'),'+',c('套牌群雄伤害')),'+',c('终极群雄伤害')))])]),
      r.section(e,'② 全军兵种收益：不限阵营',[e.branch([e.cond('UNIT_HAS_TAG',target,b.text('骑兵'))],[inc(b.math(c('套牌骑兵伤害'),'+',c('终极骑兵伤害')))]),
        e.branch([e.cond('UNIT_HAS_TAG',target,b.text('枪兵'))],[inc(c('套牌枪兵伤害'))])]),e.ret('FLOAT',damage)])
    e=Function(12,[('UNIT_ENTITY','卡牌载体')],'每载体只初始化一次属性语义表；实际数值只从各卡物编读取。')
    u=e.var('UNIT_ENTITY','卡牌载体');t=e.var('TABLE','属性规则表')
    rows=[call(e,13,t,b.text(x['收益名称']),b.text(x['参数键']),b.lit(100042,x['单位属性']),b.lit(100300,x['属性计算方式']),r.flag(x['直接写入面板'])) for x in rules]
    save(e,[e.set(t,b.n(100011,'GET_TABLE_KV',u,b.text(RULES))),e.branch([e.exists(t)],[],[
      e.set(t,b.n(100011,'GET_NEW_TABLE')),r.section(e,'首次创建属性映射，不维护第二份持卡名单',rows),e.setkv(u,RULES,t)]),e.ret('TABLE',t)])

    e=Function(16,[('PLAYER','执行玩家'),('ABILITY_NAME','指定卡牌类型')],'扫描真实持卡记录，先检查实例、记录归属和实际拥有者，再按类型匹配；不猜技能类别。')
    p=e.var('PLAYER','执行玩家');aid=e.var('ABILITY_NAME','指定卡牌类型');u=e.var('UNIT_ENTITY','卡牌载体');pool=e.var('TABLE','持卡记录');a=e.var('ABILITY','当前实例');found=e.var('ABILITY','有效实例');row=b.n(100002,'ITER_TABLE_KEY_INT')
    save(e,[e.set(found,b.n(100014,'NONE_ABILITY')),e.set(u,carrier(p)),e.branch([e.exists(u)],[e.set(pool,expr(11,'TABLE',u)),e.branch([e.exists(pool)],[
      w.traverse(e,pool,[e.set(a,d.val_table(pool,row,'技能')),journal.valid_card(e,a,u,pool,row,[
        e.branch([e.compare(b.n(100039,'ABILITY_NAME_OF_ABILITY',a),'==',aid,'ABILITY_COMPARE')],[e.set(found,a)])])])])]),e.ret('ABILITY',found)])
    e=Function(17,[('PLAYER','执行玩家')],'取得虎符后只初始化一次双线首组；重建控制器不重置玩家路线与UR账。')
    p=e.var('PLAYER','执行玩家');cfg=e.var('TABLE','卡牌配置');row=b.n(100002,'ITER_TABLE_KEY_INT')
    scan=w.traverse(e,cfg,[e.branch([e.compare(typename(cfg,row),'==',b.lit(100039,BASE),'ABILITY_COMPARE')],[
      s.external(e,w.UNLOCK,p,row)])])
    save(e,[e.branch([e.no(boolean(p,INITIALIZED))],[e.branch([e.exists(expr(16,'ABILITY',p,b.lit(100039,BASE)))],[
      e.set(cfg,config(p)),e.setkv(p,INITIALIZED,r.flag(True)),e.setkv(p,STEP+'西凉',r.i(1)),e.setkv(p,STEP+'黄巾',r.i(1)),scan,
      log(e,'双线初始化；玩家=',journal.idx(p),'；西凉阶段=1；黄巾阶段=1')])])])
    e=Function(18,[('PLAYER','执行玩家'),('STRING','所属set')],'从现有配置枚举本组普通组件，逐张核验实际实例。排除结果与子归类为无的三张终局，不依靠已抽取标记。')
    p=e.var('PLAYER','执行玩家');deck=e.var('STRING','所属set');cfg=e.var('TABLE','卡牌配置');expected=e.var('INTEGER','应有组件数');missing=e.var('INTEGER','缺少组件数');ok=e.var('BOOLEAN','本组已齐');row=b.n(100002,'ITER_TABLE_KEY_INT')
    scan=w.traverse(e,cfg,[e.branch([e.compare(r.get(cfg,row,'升级机制'),'==',b.text('群雄'),'STRING_COMPARE'),
      e.compare(r.get(cfg,row,'所属set'),'==',deck,'STRING_COMPARE'),e.no(r.get(cfg,row,'是否合成','BOOLEAN')),
      e.compare(r.get(cfg,row,'子归类'),'!=',b.text('无'),'STRING_COMPARE')],[e.set(expected,b.n(100002,'INT_PLUS_ONE',expected)),
        e.branch([e.exists(expr(16,'ABILITY',p,typename(cfg,row)))],[],[e.set(missing,b.n(100002,'INT_PLUS_ONE',missing))])])])
    save(e,[e.set(ok,r.flag(False)),e.set(cfg,config(p)),e.set(expected,r.i(0)),e.set(missing,r.i(0)),scan,
      e.branch([e.compare(expected,'>',r.i(0)),e.compare(missing,'==',r.i(0))],[e.set(ok,r.flag(True))]),e.ret('BOOLEAN',ok)])
    e=Function(19,[('PLAYER','执行玩家'),('INTEGER','结果表行'),('STRING','路线'),('INTEGER','完成阶段')],
      '终局确定后不再解锁新阶。按解锁set只开放群雄普通组件，排除结果、无子归类及三张终局UR；存在下一组组件才推进阶段。')
    p=e.var('PLAYER','执行玩家');row=e.var('INTEGER','结果表行');route=e.var('STRING','路线');stage=e.var('INTEGER','完成阶段')
    cfg=e.var('TABLE','卡牌配置');nextset=e.var('STRING','下一组');count=e.var('INTEGER','开放组件数');key=b.n(100002,'ITER_TABLE_KEY_INT')
    eligible=[e.compare(r.get(cfg,key,'升级机制'),'==',b.text('群雄'),'STRING_COMPARE'),
      e.compare(r.get(cfg,key,'所属set'),'==',nextset,'STRING_COMPARE'),e.no(r.get(cfg,key,'是否合成','BOOLEAN')),
      e.compare(r.get(cfg,key,'子归类'),'!=',b.text('无'),'STRING_COMPARE')]
    # Fixed terminal identities are a defensive boundary, not a second member list.
    eligible += [e.compare(typename(cfg,key),'!=',b.lit(100039,aid),'ABILITY_COMPARE') for aid in UR]
    unlock=w.traverse(e,cfg,[e.branch(eligible,[
      e.action('SET_TABLE_VALUE_ND',cfg,key,b.text('是否解锁'),r.flag(True)),
      e.set(count,b.n(100002,'INT_PLUS_ONE',count))])])
    save(e,[e.branch([e.no(boolean(p,CLAIMED)),e.compare(integer(p,PENDING),'==',r.i(0)),e.compare(stage,'<',r.i(5))],[
      e.set(cfg,config(p)),e.set(nextset,r.get(cfg,row,'解锁set')),e.set(count,r.i(0)),
      r.section(e,'① 下一组只开放普通组件；终局UR由函数22独立授予',[
        e.branch([e.compare(nextset,'!=',b.text('无'),'STRING_COMPARE'),e.compare(nextset,'!=',b.text(''),'STRING_COMPARE')],[unlock])]),
      r.section(e,'② 有效组件存在后推进路线阶段',[
        e.branch([e.compare(count,'>',r.i(0))],[r.skv(e,p,r.join(b.text(STEP),route),b.n(100002,'INT_PLUS_ONE',stage)),
          log(e,'解锁下一组；玩家=',journal.idx(p),'；路线=',route,'；阶段=',step(p,route),'；所属set=',nextset,'；开放组件数=',count)])])])])
    e=Function(21,[('PLAYER','执行玩家'),('INTEGER','授予表行'),('STRING','授予来源')],
      '复用原合成写表与UI，返回实际实例；日志来源按玩家保存/恢复并绑定目标类型。此处不触发路线完成或随机奖励。')
    p=e.var('PLAYER','执行玩家');row=e.var('INTEGER','授予表行');reason=e.var('STRING','授予来源');a=e.var('ABILITY','授予实例');oldctx=e.var('STRING','上级日志来源');oldbound=e.var('STRING','上级日志目标');aid=typename(config(p),row)
    save(e,[e.set(a,expr(16,'ABILITY',p,aid)),e.branch([e.exists(a)],[],[
      e.branch([e.yes(journal.enabled())],[e.set(oldctx,strkv(p,journal.CTX)),e.set(oldbound,strkv(p,journal.BOUND)),
        e.setkv(p,journal.CTX,reason),e.setkv(p,journal.BOUND,typekey(aid))]),
      e.set(a,s.foreign(w.MERGE,'ABILITY',p,row)),
      e.branch([e.yes(journal.enabled())],[e.setkv(p,journal.CTX,oldctx),e.setkv(p,journal.BOUND,oldbound)]),
      e.branch([e.exists(a)],[s.external(e,w.SHOW,p,a)])]),e.ret('ABILITY',a)])
    e=Function(22,[('PLAYER','执行玩家')],'待授予类型在首条终局完成时固定；实际成功才记本局UR领取，失败保留候选重试，不因另一线继续发展改奖励。')
    p=e.var('PLAYER','执行玩家');cfg=e.var('TABLE','卡牌配置');a=e.var('ABILITY','UR实例');row=b.n(100002,'ITER_TABLE_KEY_INT');target=integer(p,PENDING)
    # Compare the pending integer against the three fixed terminal resource types
    # through native typed ABILITY_NAME literals, never an invented conversion API.
    for_ur=[]
    for aid in UR:
        for_ur.append(e.branch([e.compare(target,'==',r.i(aid))],[w.traverse(e,cfg,[
          e.branch([e.compare(typename(cfg,row),'==',b.lit(100039,aid),'ABILITY_COMPARE')],[
            e.set(a,expr(21,'ABILITY',p,row,strkv(p,ENDING)))])])]))
    save(e,[e.branch([e.no(boolean(p,BUSY)),e.no(boolean(p,CLAIMED)),e.compare(target,'>',r.i(0))],[
      e.set(cfg,config(p)),e.set(a,b.n(100014,'NONE_ABILITY')),e.setkv(p,BUSY,r.flag(True)),
      r.section(e,'① 按已经确定的终局类型发放，失败不换结局',for_ur),
      e.branch([e.exists(a)],[e.setkv(p,CLAIMED,r.flag(True)),e.setkv(p,FINAL,target),e.setkv(p,PENDING,r.i(0)),
        log(e,'UR授予成功；玩家=',journal.idx(p),'；卡牌=',b.n(100039,'ABILITY_NAME_OF_ABILITY',a),'；来源=',strkv(p,ENDING),
          '；西凉当前阶段=',step(p,b.text('西凉')),'；黄巾当前阶段=',step(p,b.text('黄巾')),'；另一线收完当前组后停止')]),
      e.setkv(p,BUSY,r.flag(False)),call(e,14,carrier(p))])])
    e=Function(20,[('PLAYER','执行玩家'),('INTEGER','结果表行'),('STRING','路线'),('INTEGER','完成阶段')],
      '一次自然合成：实际结果成功后记录完成、折叠组件、加声望、决定终局或解锁下一组；嵌套回调不重复结算。')
    p=e.var('PLAYER','执行玩家');row=e.var('INTEGER','结果表行');route=e.var('STRING','路线');stage=e.var('INTEGER','完成阶段');cfg=e.var('TABLE','卡牌配置')
    a=e.var('ABILITY','套牌结果');base=e.var('ABILITY','虎符实例');gain=e.var('INTEGER','本次声望');promoted=e.var('BOOLEAN','虎符已升级');deck=r.get(cfg,row,'所属set')
    reason=journal.text('群雄自然合成；路线=',route,'；阶段=',stage)
    choose=[e.branch([e.compare(route,'==',b.text('西凉'),'STRING_COMPARE')],[e.setkv(p,PENDING,r.i(NORMAL_WEST))],[e.setkv(p,PENDING,r.i(NORMAL_YELLOW))]),
      e.setkv(p,ENDING,journal.text('群雄路线终局；路线=',route,'；西凉解锁阶段=',step(p,b.text('西凉')),'；黄巾解锁阶段=',step(p,b.text('黄巾')))),
      e.branch([e.compare(step(p,b.text('西凉')),'>=',r.i(5)),e.compare(step(p,b.text('黄巾')),'>=',r.i(5))],[
        e.setkv(p,PENDING,r.i(SPECIAL)),e.setkv(p,ENDING,journal.text('群雄双线特殊终局；先完成路线=',route,'；两线最后一组均已解锁'))])]
    save(e,[e.set(cfg,config(p)),e.branch([e.no(boolean(p,BUSY)),e.no(complete(p,deck))],[
      e.setkv(p,BUSY,r.flag(True)),e.set(a,expr(21,'ABILITY',p,row,reason)),e.branch([e.exists(a)],[
        r.section(e,'① 结果存在后才登记完成；原组件只折叠不删除',[r.skv(e,p,r.join(b.text(DONE),deck),r.flag(True)),
          s.external(e,'5ec39849b3e211f197f88b7bdf2d7282',p,deck)]),
        r.section(e,'② 本组声望沿用结果实例的原10～20随机值',[e.set(base,expr(16,'ABILITY',p,b.lit(100039,BASE))),e.branch([e.exists(base)],[
          e.set(gain,integer(a,'获得声望')),e.setkv(base,'声望累计',s.imath(integer(base,'声望累计'),'+',gain)),
          e.set(promoted,s.foreign('fba1b5a5a9a211f19b468d90bbbf35e2','BOOLEAN',base)),
          log(e,'声望结算；玩家=',journal.idx(p),'；完成set=',deck,'；获得声望=',gain,'；累计声望=',integer(base,'声望累计'),'；虎符等级=',s.level(base))])]),
        r.section(e,'③ 首个末组完成时固定奖励；先检查两线末组解锁状态',[e.branch([e.compare(stage,'==',r.i(5)),e.no(boolean(p,CLAIMED)),e.compare(integer(p,PENDING),'==',r.i(0))],choose)]),
        call(e,19,p,row,route,stage)]),e.setkv(p,BUSY,r.flag(False)),call(e,14,carrier(p)),call(e,22,p),
      s.external(e,journal.FIDS[2],p,b.text('群雄套牌结算结束'),r.flag(False))])])
    e=Function(15,[('PLAYER','执行玩家'),('ABILITY_NAME','变更卡牌类型')],
      '选卡实例记录写完后调用；群雄两线按当前已解锁阶段判断实际集齐，不依赖旧张角/董卓锁线变量。')
    p=e.var('PLAYER','执行玩家');aid=e.var('ABILITY_NAME','变更卡牌类型');a=e.var('ABILITY','实际选卡');cfg=e.var('TABLE','卡牌配置');deck=e.var('STRING','所属set');route=e.var('STRING','路线');stage=e.var('INTEGER','阶段');row=b.n(100002,'ITER_TABLE_KEY_INT')
    findset=w.traverse(e,cfg,[e.branch([e.compare(typename(cfg,row),'==',aid,'ABILITY_COMPARE')],[e.set(deck,r.get(cfg,row,'所属set'))])])
    findresult=w.traverse(e,cfg,[e.branch([e.compare(r.get(cfg,row,'升级机制'),'==',b.text('群雄'),'STRING_COMPARE'),
      e.compare(r.get(cfg,row,'所属set'),'==',deck,'STRING_COMPARE'),e.yes(r.get(cfg,row,'是否合成','BOOLEAN'))],[call(e,20,p,row,route,stage)])])
    save(e,[e.set(a,expr(16,'ABILITY',p,aid)),e.branch([e.exists(a)],[e.branch([e.cond('HAS_KV_ANY',a,b.text(d.FACTION))],[
      e.branch([e.compare(strkv(a,d.FACTION),'==',b.text('群雄'),'STRING_COMPARE'),e.no(boolean(p,BUSY))],[
        call(e,17,p),e.set(cfg,config(p)),e.branch([e.compare(strkv(a,d.IDENTITY),'==',b.text('普通组件'),'STRING_COMPARE')],[
          e.set(route,strkv(a,ROUTE)),e.set(stage,integer(a,LEVEL)),e.set(deck,b.text('')),findset,
          e.branch([e.compare(stage,'==',step(p,route)),e.no(complete(p,deck))],[e.branch([e.yes(expr(18,'BOOLEAN',p,deck))],[findresult])])]),
        call(e,22,p)])])])])
    return out

def build_embedded(specs):
    out={};b.TID=2099907000
    for aid in specs:
        e=b.Eca(aid);old=MAP/f'ability/{aid}.json';actions=[]
        if old.exists():
            ts=list(read(f'ability/{aid}.json')['trigger_dict'].values());assert len(ts)==1
            assert ts[0]['event'][0]['event_type']=='ABILITY_OBTAIN'
            actions=copy.deepcopy(ts[0]['action']) # retain the one original reputation draw
        e.trigger('获得卡牌：保留声望赋值并等待持卡记录写入','ABILITY_OBTAIN',actions+[call(e,1,b.unit('ABILITY_OWNER'),b.ability())])
        e.trigger('等级变化：读取当前技能拥有者后刷新','ABILITY_LEVEL_CHANGED',[call(e,14,b.n(100006,'GET_ABILITY_OWNER',b.ability()))])
        e.trigger('失去卡牌：标记刷新，由周期覆盖删除时序','ABILITY_LOSE',[call(e,14,b.unit('ABILITY_OWNER'))])
        out[f'ability/{aid}.json']=e.done()
    for oid,template in [(CONTROL,w.CONTROL),(ARMY,w.ARMY)]:
        doc=translated(read(f'modifier/{template}.json'))
        if oid==CONTROL:
            for tr in doc['trigger_dict'].values():
                event=tr['event'][0]['event_type']
                if event=='OBTAIN_MODIFIER':
                    # Keep the native change/phase child registrations, no Wei wave state.
                    tr['action']=[a for a in tr['action'] if isinstance(a,int) or a.get('action_type')=='SET_ENTITY_KV' and any(n.get('args_list') in ([r.APPLIED],[r.COUNT]) for n in b.walk(a))]
                elif event=='RECEIVE_CUSTOM_EVENT' and tr['event'][0]['args_list'][0]['args_list'][0]==b.PHASE:
                    e=b.Eca(oid,True);tr['action']=[call(e,2,b.owner(),b.buff(),r.flag(True))];tr['trigger_name']='开战：刷新全军收益'
                elif event=='MODIFIER_CYCLE_TRIGGER':
                    e=b.Eca(oid,True);tr['action']=[call(e,2,b.owner(),b.buff(),r.flag(False)),call(e,22,b.player(b.owner())),
                      e.branch([e.compare(r.value(b.buff(),r.COUNT),'==',b.f(0))],[e.action('REMOVE_BUFF_INS',b.buff())])]
                    tr['trigger_name']='周期兜底：失效持卡、补兵与待授予UR'
        # Reassign copied trigger identities, including child registration references.
        idmap={int(k):2099907300+(0 if oid==CONTROL else 100)+i for i,k in enumerate(doc['trigger_dict'])}
        def ids(x):
            if isinstance(x,list):return [ids(v) for v in x]
            if isinstance(x,dict):return {str(idmap[int(k)]) if str(k).isdigit() and int(k) in idmap else k:ids(v) for k,v in x.items()}
            if isinstance(x,int) and not isinstance(x,bool):return idmap.get(x,x)
            return x
        doc=ids(doc)
        for n in b.walk(doc['trigger_group_info']):
            if n.get('__tuple__') and str(n['items'][0]) in doc['trigger_dict']:n['items'][1]=doc['trigger_dict'][str(n['items'][0])]['trigger_name']
        serial=oid*1000000
        for n in b.walk(doc):
            if 'element_id' in n:serial+=1;n['element_id']=serial
        out[f'modifier/{oid}.json']=doc
    return out

def patch_shared():
    out={};rel=journal.SELECT;doc=read(rel);original=copy.deepcopy(doc)
    # Replace only the existing Qun storage box, keeping all other factions and logs.
    containers=[n for n in b.walk(doc) if n.get('action_type')=='STORAGE_BOX' and len(n['args_list'])>3 and n['args_list'][3].get('args_list')==['群雄 升级机制 判断处理']]
    assert len(containers)==1
    old=copy.deepcopy(containers[0]);e=Function(15,[],'')
    p=b.n(100025,'VARIABLE',r.tp(['PLAYER','执行玩家','local']));aid=b.n(100039,'VARIABLE',r.tp(['ABILITY_NAME','处理技能类型','local']))
    replacement=r.section(e,'群雄：双线递进、一次完成与首个终局判定',[call(e,15,p,aid)])
    containers[0].clear();containers[0].update(replacement)
    serial=max(n.get('element_id',0) for n in b.walk(original))+1000
    for n in b.walk(containers[0]):
        if 'element_id' in n:serial+=1;n['element_id']=serial
    out[rel]=doc
    # Existing merge writer already records result source; add only Qun refresh.
    rel2=journal.MERGE;merge=read(rel2);before2=copy.deepcopy(merge);e=Function(14,[],'')
    node=call(e,14,carrier(p));node['element_id']=max(n.get('element_id',0) for n in b.walk(merge))+1
    merge['action'].insert(len(merge['action'])-1,node);out[rel2]=merge
    return out,{rel:{'original':original,'removed_box':old,'replacement_id':containers[0]['element_id']},
      rel2:{'original':before2,'added_id':node['element_id']}}


if __name__=='__main__':
    raise SystemExit("Maintenance library only; original one-time staging/publication has been retired. Use the regression tests and review scoped changes against the current map.")
