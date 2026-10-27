"""Maintain Wei native-ECA builders and shared transformation helpers.

Never writes the live map. Publication and real-engine acceptance are separate.
The four unmatched legacy objects receive names only, not KV or embedded ECA.
"""
from __future__ import annotations
import copy, hashlib, uuid
import y3_shu_command_cards as s
r,d,b=s.r,s.d,s.b
MAP=s.MAP
CONTROL,ARMY=134285201,134285202
CYCLE=.5
BASE=134255945
CHANGE=2099456210
PREFIX='魏国军略_'
RULES,SOURCE,REV,DIRTY=(PREFIX+x for x in ('属性规则','载体','版本','待刷新'))
BUSY,CLAIMED=PREFIX+'奖励授予中',PREFIX+'本局EX已领取'
THRESHOLD=PREFIX+'八虎骑门槛'
FOLDER='global_trigger/function/new/魏国军略'
PLACEHOLDERS={134222672:'许诸',134274349:'程昱',134224472:'刘烨',134227532:'八虎骑-曹修'}
RESULTS={134251374:(10,0,0,0),134235073:(15,15,0,0),134236770:(20,0,0,0),
         134236161:(25,0,25,0),134239953:(25,0,0,25)}
NAMES={**{i:n.replace('蜀国','魏国') for i,n in s.NAMES.items() if i<=14},
 15:'15_每波结算赠骑概率',16:'16_只累计贾诩的战斗时间',17:'17_逐卡结算指定奖励概率',
 18:'18_随机赠送未持有八虎骑',19:'19_检查门槛并授予唯一EX',
 20:'20_选卡或合成写表后结算',21:'21_隔离奖励来源并授予指定表行'}
FIDS={i:uuid.uuid5(uuid.NAMESPACE_URL,'project01/y3/wei/'+n).hex for i,n in NAMES.items()}
MERGE=s.MERGE
UNLOCK='af90a265b3d611f184b08b7bdf2d7282'
SHOW='674938acb11211f1a782517072b020be'
COUNT='a2cbf27fa80911f19d664f3f414a7497'
COMPLETED=PREFIX+'吞噬已完成_'
MECHANICS=['单卡魏国伤害','套牌魏国伤害','套牌盾兵伤害','套牌弓兵伤害','套牌后排伤害',
           '终极盾弓伤害','选卡获骑概率','合成获骑概率','每波获骑概率','战斗计时获骑概率']

read=s.read
sha=s.sha
value=s.value
def rule_table(u):return b.n(100011,'GET_TABLE_KV',u,b.text(RULES))
def expr(i,kind,*args):return s.foreign(FIDS[i],kind,*args)
def call(e,i,*args):return s.external(e,FIDS[i],*args)
def phase():return b.n(100002,6,r.tp(['INTEGER','当前游戏进程阶段']))
def threshold():return b.n(100002,6,r.tp(['INTEGER',THRESHOLD]))
def boolean(entity,key):return b.n(100001,'GET_BOOLEAN_KV',entity,b.text(key))
def integer(entity,key):return s.integer(entity,key)
def config(player):
    idx=s.foreign('9384d061198e11ef967be8c829c05699','INTEGER',player)
    return b.n(100011,'VARIABLE',r.tp(['TABLE','军令卡牌base-表']),idx)
def carrier(player):
    idx=s.foreign('9384d061198e11ef967be8c829c05699','INTEGER',player)
    return b.n(100006,11,r.tp(['UNIT_ENTITY','playerHeroList']),idx)
def has_type(u,aid):return b.n(100001,'CHECK_HAS_ABILITY_TYPE',u,aid)
def typename(t,row):return r.get(t,row,'技能类型','ABILITY_NAME')
def faction(e,t,row):return e.compare(r.get(t,row,'升级机制'),'==',b.text('魏国'),'STRING_COMPARE')
def typekey(aid):return b.n(100003,'ANY_VAR_TO_STR',aid)
def send(e,u):return e.action('SEND_CUSTOM_EVENT',b.lit(100238,CHANGE),u)
def traverse(e,t,actions):
    # Native Y3 save materializes this disabled optional argument. Keeping the
    # observed shape prevents a future generation from dropping its metadata.
    node=e.action('TRAVERSE_TABLE_NEW',t,b.n(100022,1,*actions))
    node.update(op_arg=[r.flag(True)],op_arg_enable=[False])
    return node

class Function(s.Function):
    def __init__(self,i,params,comment):
        self.index=i;self.modifier=False
        self.obj=read('global_trigger/function/业务逻辑/功能执行/单位移除技能.json')
        self.oid=2099872000+i;self.serial=self.oid*1000000
        self.obj.update(action=[],condition=[],event=[],func_id=FIDS[i],func_name=NAMES[i],trigger_name=NAMES[i],trigger_id=self.oid,
          group_id='wei_cards_20261026',func_comment=comment,func_des=NAMES[i]+'：'+ '，'.join(n+'{'+n+'}' for _,n in params),
          func_param_list=[r.tp([name,True]) for _,name in params],var_data=[{},{},[]])
        for key in ('func_return','func_rtv_name_list'):self.obj.pop(key,None)
        self.params=params
        for kind,name in params:self.var(kind,name)

def translated(node):
    ids={s.CONTROL:CONTROL,s.ARMY:ARMY,s.CHANGE:CHANGE}
    if isinstance(node,list):return [translated(x) for x in node]
    if isinstance(node,dict):return {translated(k):translated(v) for k,v in node.items()}
    if isinstance(node,str):
        for i,fid in s.FIDS.items():
            if node==fid:
                assert i<=14,'Unexpected Shu-specific dependency'
                return FIDS[i]
        return node.replace('蜀国','魏国').replace('shu_cards_20261018','wei_cards_20261026')
    if isinstance(node,int) and not isinstance(node,bool):return ids.get(node,node)
    return node

def reidentify(doc,tid):
    doc=copy.deepcopy(doc);doc['trigger_id']=tid;serial=tid*1000000
    for node in b.walk(doc):
        if 'element_id' in node:serial+=1;node['element_id']=serial
    return doc

def specs_from_book():
    import openpyxl
    assert sha(s.BOOK.read_bytes())==s.BOOK_SHA,'Workbook changed; re-audit first'
    book=openpyxl.load_workbook(s.BOOK,read_only=True,data_only=True)
    sheet=book['套牌'];sheet.reset_dimensions()
    rows=list(sheet.iter_rows(min_row=54,max_row=89,max_col=9,values_only=True));book.close()
    language=read('zhlanguage.json');pool=read('tables/魏国temp.json')['table_data']['data'];specs={}
    for row in pool[2:]:
        if not row or not isinstance(row[1],int):continue
        aid=row[1]
        if aid in PLACEHOLDERS:continue
        meta=read(f'editor_table/abilityall/{aid}.json');name=language[str(meta['name'])]
        short=name.removeprefix('八虎骑-')
        matches=[(54+i,x) for i,x in enumerate(rows) if x[2]==short]
        assert len(matches)==(0 if aid==BASE else 1),(aid,name,matches)
        spec=dict(id=aid,name=name,params={},base=[],row=None,identity='起始载体')
        if matches:
            num,x=matches[0];spec.update(row=num,base=list(x[4:7]),special=x[7],deck=x[1],quality=x[3])
            spec['params']=b.parse_base(spec['base'])
            spec['identity']='EX' if x[3]=='EX' else 'UR组件' if x[3]=='UR' else '普通组件'
            if x[3] in ('UR','EX'):spec['params']['单卡魏国伤害']=40. if short=='曹操' else 30. if x[3]=='EX' else 20.
        if aid in RESULTS:
            spec['params'].update({k:float(v) for k,v in zip(MECHANICS[1:5],RESULTS[aid]) if v})
        if spec['identity']=='EX':spec['params'].update(套牌魏国伤害=60.,终极盾弓伤害=40.)
        specs[aid]=spec
    for aid,values in {134252946:{'选卡获骑概率':10.,'合成获骑概率':10.},134264459:{'选卡获骑概率':20.},
      134231749:{'每波获骑概率':10.},134253995:{'每波获骑概率':20.},134260135:{'战斗计时获骑概率':40.}}.items():specs[aid]['params'].update(values)
    for aid,spec in specs.items():
        text=[x for x in spec['base'] if x not in (None,'','-')]
        if spec.get('special') not in (None,'','-'):text.append(spec['special'])
        if aid in RESULTS:
            a,shield,bow,rear=RESULTS[aid];text.append(f'完成套牌：魏国角色伤害+{a}%')
            text += [f'全军{label}伤害+{v}%' for label,v in [('盾兵',shield),('弓兵',bow),('后排',rear)] if v]
        if aid==BASE:text=['魏国起始军略；沿用现有五条套牌合成与解锁路线。八虎骑数量门槛读取公共变量，默认8；本局仅授予一张随机EX。']
        if spec['identity']=='EX':text.append('终极：魏国角色伤害+60%，全军盾兵或弓兵伤害+40%（交集只加一次），本卡单卡被动另计；已完成套牌收益保留。')
        if any(k.endswith('获骑概率') for k in spec['params']):text.append('赠送八虎骑不会再次触发选卡或合成概率奖励；只赠未持有类型。')
        if aid==134260135:text.append('两分钟仅累计波次战斗时间，备战暂停；失去贾诩清零。')
        spec['description']='；'.join(text)
    assert len(specs)==32
    return specs

def make_rules(specs):
    keys=sorted(set(MECHANICS)|{k for x in specs.values() for k in x['params']})
    rules=[]
    for key in keys:
        if key.startswith('属性_'):
            attr,mode=key[3:].rsplit('_ATTR_',1);mode='ATTR_'+mode;direct=attr!='extra_dmg'
            label=next((n for n,pair in b.FIELDS.items() if pair==(attr,mode)),('全属性比例' if mode=='ATTR_ALL_RATIO' else '属性')+':'+attr)
        else:attr,mode,direct,label='strength','ATTR_BASE',False,key
        rules.append({'收益名称':label,'参数键':key,'单位属性':attr,'属性计算方式':mode,'直接写入面板':direct})
    return rules

def build_functions(rules):
    out={}
    for i in (1,2,3,4,5,6,7,8,10,11,13,14):
        doc=read(f'{s.FOLDER}/{s.NAMES[i]}.json')
        if i==2:doc['action'][1]['args_list'][1]['args_list'].pop() # remove Shu terminal check
        doc=translated(doc)
        out[f'{FOLDER}/{NAMES[i]}.json']=reidentify(doc,2099872000+i)
    def save(e,actions):out[f'{FOLDER}/{NAMES[e.index]}.json']=e.finish(actions)
    e=Function(4,[('ABILITY','卡牌实例'),('MODIFIER_ENTITY','控制Buff'),('TABLE','属性规则表')],
      '卡牌自身属性始终按有效持有读取。UR所承载的套牌吞噬收益，仅在自然合成完成后计入；赠到UR不等于完成原套牌。')
    a=e.var('ABILITY','卡牌实例');m=e.var('MODIFIER_ENTITY','控制Buff');fields=e.var('TABLE','属性规则表')
    fr=e.var('INTEGER','参数行号');key=r.get(fields,fr,'参数键');allowed=e.var('BOOLEAN','本项可计入')
    source_unit=b.n(100006,'GET_ABILITY_OWNER',a)
    is_set_field=e.cond('OR',*[e.compare(key,'==',b.text(k),'STRING_COMPARE') for k in MECHANICS[1:5]])
    save(e,[r.loop(e,fr,fields,[e.set(allowed,r.flag(True)),e.branch([e.cond('HAS_KV_ANY',a,b.text(d.IDENTITY))],[
      e.branch([e.compare(r.value(a,d.IDENTITY,'STRING'),'==',b.text('UR组件'),'STRING_COMPARE'),is_set_field],[
        e.set(allowed,b.n(100001,'GET_BOOLEAN_KV',source_unit,r.join(b.text(COMPLETED),d.ability_key(a))))])]),
      e.branch([e.yes(allowed),e.cond('HAS_KV_ANY',a,key)],[r.skv(e,m,r.preview_key(key),b.math(r.value(m,r.preview_key(key)),'+',r.value(a,key)))])])])
    # Rebuild rule initialization with a guarded create block and one final return.
    e=Function(12,[('UNIT_ENTITY','卡牌载体')],'每载体仅创建一次规则；属性语义集中，数值只在各卡物编维护。末尾统一返回表。')
    u=e.var('UNIT_ENTITY','卡牌载体');t=e.var('TABLE','属性规则表')
    rows=[call(e,13,t,b.text(x['收益名称']),b.text(x['参数键']),b.lit(100042,x['单位属性']),b.lit(100300,x['属性计算方式']),r.flag(x['直接写入面板'])) for x in rules]
    save(e,[e.set(t,rule_table(u)),e.branch([e.exists(t)],[],[e.set(t,b.n(100011,'GET_NEW_TABLE')),
      r.section(e,'首次初始化：条件参数与面板属性的语义映射',rows),e.setkv(u,RULES,t)]),e.ret('TABLE',t)])
    e=Function(9,[('UNIT_ENTITY','卡牌载体'),('UNIT_ENTITY','目标单位'),('UNIT_ENTITY','所属队长')],
      '以输出单位判断阵营和兵种；排位继承所属队长。EX盾兵/弓兵取并集，一次写入extra_dmg。')
    u=e.var('UNIT_ENTITY','卡牌载体');target=e.var('UNIT_ENTITY','目标单位');cap=e.var('UNIT_ENTITY','所属队长')
    damage=e.var('FLOAT','合计增伤');pos=e.var('INTEGER','战前阵位')
    def c(key):return s.value(u,PREFIX+key)
    def inc(v):return e.set(damage,b.math(damage,'+',v))
    save(e,[r.section(e,'① 只读取有效队长的已有阵位',[e.set(pos,r.i(0)),e.branch([e.exists(cap)],[
      e.branch([e.cond('HAS_KV_ANY',cap,b.text('归属阵型编号'))],[e.set(pos,integer(cap,'归属阵型编号'))])])]),
      e.set(damage,c(b.field_key('extra_dmg','ATTR_BASE'))),
      r.section(e,'② 魏国输出：单卡与套牌收益相加',[e.branch([e.cond('OR',e.cond('UNIT_HAS_TAG',target,b.text('魏国')),
        e.cond('UNIT_HAS_TAG',cap,b.text('魏国')))],[inc(b.math(c('单卡魏国伤害'),'+',c('套牌魏国伤害')))])]),
      r.section(e,'③ 全军兵种与后排：分别读取各自收益',[
        e.branch([e.cond('UNIT_HAS_TAG',target,b.text('盾兵'))],[inc(c('套牌盾兵伤害'))]),
        e.branch([e.cond('UNIT_HAS_TAG',target,b.text('弓兵'))],[inc(c('套牌弓兵伤害'))]),
        e.branch([e.compare(pos,'>=',r.i(7)),e.compare(pos,'<=',r.i(9))],[inc(c('套牌后排伤害'))])]),
      r.section(e,'④ EX：盾兵或弓兵交集只加一次',[e.branch([e.cond('OR',e.cond('UNIT_HAS_TAG',target,b.text('盾兵')),
        e.cond('UNIT_HAS_TAG',target,b.text('弓兵')))],[inc(c('终极盾弓伤害'))])]),e.ret('FLOAT',damage)])
    # A new unit must be present, native-alive, and not a project pseudo-dead hero.
    e=Function(6,[('UNIT_ENTITY','卡牌载体'),('UNIT_ENTITY','目标单位')],'只为存活且未标记已死亡的单位建立本系统收益；重复通知不叠Buff。')
    u=e.var('UNIT_ENTITY','卡牌载体');target=e.var('UNIT_ENTITY','目标单位')
    save(e,[e.branch([e.exists(target)],[e.branch([e.alive(target)],[e.branch([e.cond('UNIT_HAS_TAG',target,b.text('已死亡'))],[],[
      e.setkv(target,SOURCE,u),e.branch([e.no(b.hasbuff(target,ARMY))],[e.addbuff(target,ARMY,u)])])])])])
    # Guard the optional captain KV read; keep the reviewed stat application path.
    obj=out[f'{FOLDER}/{NAMES[8]}.json'];pre=obj['action'][0]['args_list'][1]['args_list']
    e=Function(8,[], '')
    node=pre[-1];target=copy.deepcopy(node['args_list'][0]['args_list'][0]['args_list'][0]['args_list'][0])
    pre[-1]=e.branch([e.cond('HAS_KV_ANY',target,b.text('所属英雄'))],[node])
    out[f'{FOLDER}/{NAMES[8]}.json']=reidentify(obj,2099872008)

    e=Function(15,[('UNIT_ENTITY','卡牌载体'),('MODIFIER_ENTITY','控制Buff')],'真实波次编号去重；张辽10%和荀彧20%分别独立抽取，不追补途中获卡的当波。')
    u=e.var('UNIT_ENTITY','卡牌载体');m=e.var('MODIFIER_ENTITY','控制Buff')
    save(e,[e.branch([e.compare(s.wave(),'>',r.i(0)),e.compare(s.wave(),'>',integer(u,PREFIX+'已结算波次'))],[
      e.setkv(u,PREFIX+'已结算波次',s.wave()),call(e,2,u,m,r.flag(True)),call(e,17,u,b.text('每波获骑概率')),call(e,19,u)])])
    e=Function(16,[('UNIT_ENTITY','卡牌载体'),('MODIFIER_ENTITY','控制Buff')],'仅战斗阶段累计控制Buff周期时间，备战暂停；每满120战斗秒独立抽一次40%。失去贾诩清零。')
    u=e.var('UNIT_ENTITY','卡牌载体');m=e.var('MODIFIER_ENTITY','控制Buff');elapsed=s.value(m,'贾诩累计战斗秒')
    save(e,[e.branch([e.yes(b.hascard(u,134260135))],[e.branch([e.compare(phase(),'==',r.i(2))],[
      e.setkv(m,'贾诩累计战斗秒',b.math(elapsed,'+',b.f(CYCLE))),
      e.branch([e.compare(elapsed,'>=',b.f(120))],[e.setkv(m,'贾诩累计战斗秒',b.math(elapsed,'-',b.f(120))),call(e,17,u,b.text('战斗计时获骑概率')),call(e,19,u)])])],
      [e.setkv(m,'贾诩累计战斗秒',b.f(0))])])
    e=Function(17,[('UNIT_ENTITY','卡牌载体'),('STRING','概率参数键')],'依有效持卡逐张独立抽取，物编只配置自身概率；奖励授予中禁止再抽奖。')
    u=e.var('UNIT_ENTITY','卡牌载体');key=e.var('STRING','概率参数键');pool=e.var('TABLE','持卡记录');seen=e.var('TABLE','已抽取类型')
    a=e.var('ABILITY','当前卡牌');aid=e.var('STRING','当前类型');p=e.var('FLOAT','本卡概率');roll=e.var('INTEGER','本次掷骰');row=b.n(100002,'ITER_TABLE_KEY_INT')
    rolled=[e.set(roll,b.n(100002,'RANDOM_INT',r.i(1),r.i(100)))]
    rolled.append(e.action('PRINT_MESSAGE_ACTION_TO_DIALOG',b.lit(100175,3),message))
    rolled.append(e.branch([e.compare(roll,'<=',p)],[call(e,18,u)]))
    scan=traverse(e,pool,[e.set(a,d.val_table(pool,row,'技能')),e.branch([e.exists(a)],[
      e.branch([e.compare(d.val_table(pool,row,'归属单位','UNIT_ENTITY'),'==',u,'UNIT_COMPARE')],[
        e.branch([e.cond('HAS_KV_ANY',a,key)],[e.set(aid,d.ability_key(a)),e.branch([e.cond('TABLE_HAS_KEY',seen,aid)],[],[
          d.set_1d(e,seen,aid,r.flag(True)),e.set(p,r.value(a,key)),e.branch([e.compare(p,'>',b.f(0))],rolled)])])])])])
    save(e,[e.branch([e.no(boolean(u,BUSY))],[e.set(pool,expr(11,'TABLE',u)),e.branch([e.exists(pool)],[
      e.set(seen,b.n(100011,'GET_NEW_TABLE')),r.section(e,'逐卡独立概率：赠卡回调不会进入此段', [scan])])])])
    e=Function(18,[('UNIT_ENTITY','卡牌载体')],'从既有配置筛选本玩家未持有的八虎骑，等概率赠送一张；已集齐不再赠，不递归抽奖。')
    u=e.var('UNIT_ENTITY','卡牌载体');t=e.var('TABLE','既有卡牌配置');choices=e.var('TABLE','可赠送表行');n=e.var('INTEGER','候选数量');chosen=e.var('INTEGER','抽中序号');row=b.n(100002,'ITER_TABLE_KEY_INT')
    scan=traverse(e,t,[e.branch([faction(e,t,row),e.compare(r.get(t,row,'子归类'),'==',b.text('八虎骑'),'STRING_COMPARE')],[
      e.branch([e.no(has_type(u,typename(t,row)))],[e.set(n,b.n(100002,'INT_PLUS_ONE',n)),d.set_1d(e,choices,n,row)])])])
    getint=lambda t,k:b.n(100002,'GET_INTEGER_TABLE_VAR_1D',t,k)
    save(e,[e.branch([e.no(boolean(u,BUSY))],[e.set(t,config(b.player(u))),e.set(choices,b.n(100011,'GET_NEW_TABLE')),e.set(n,r.i(0)),scan,
      e.branch([e.compare(n,'>',r.i(0))],[e.set(chosen,b.n(100002,'RANDOM_INT',r.i(1),n)),call(e,21,u,getint(choices,chosen))])])])
    e=Function(19,[('UNIT_ENTITY','卡牌载体')],'门槛只读公共整数变量。集齐八虎骑后从原五张EX等概率授予一次；领取标记属于玩家，本局失卡不重置。')
    u=e.var('UNIT_ENTITY','卡牌载体');t=e.var('TABLE','既有卡牌配置');choices=e.var('TABLE','EX表行');n=e.var('INTEGER','候选数量');a=e.var('ABILITY','授予结果');row=b.n(100002,'ITER_TABLE_KEY_INT')
    ready=s.foreign(COUNT,'BOOLEAN',b.player(u),threshold())
    scan=traverse(e,t,[e.branch([faction(e,t,row),e.compare(r.get(t,row,'所属set'),'==',b.text('EX'),'STRING_COMPARE')],[
      e.set(n,b.n(100002,'INT_PLUS_ONE',n)),d.set_1d(e,choices,n,row)])])
    save(e,[e.branch([e.no(boolean(u,BUSY))],[e.branch([e.yes(ready)],[
      r.section(e,'① 从已有魏国卡牌配置获取EX候选',[e.set(t,config(b.player(u))),e.set(choices,b.n(100011,'GET_NEW_TABLE')),e.set(n,r.i(0)),scan]),
      r.section(e,'② 调用隔离授予；成功后永久登记本局领取',[e.branch([e.compare(n,'>',r.i(0))],[
        e.set(a,expr(21,'ABILITY',u,getint(choices,b.n(100002,'RANDOM_INT',r.i(1),n)))),
        e.branch([e.exists(a)],[e.setkv(b.player(u),CLAIMED,r.flag(True))])])])])])])
    e=Function(20,[('UNIT_ENTITY','卡牌载体'),('INTEGER','获得来源'),('ABILITY_NAME','变更卡牌类型')],
      '1=选卡，2=自然合成；自然合成先登记吞噬完成再刷新。赠卡的来源锁禁止完成登记和再次抽奖。已有UR的自然合成也由此结算一次。')
    u=e.var('UNIT_ENTITY','卡牌载体');source=e.var('INTEGER','获得来源');aid=e.var('ABILITY_NAME','变更卡牌类型');t=e.var('TABLE','既有卡牌配置');wei=e.var('BOOLEAN','本次为魏卡');result=e.var('BOOLEAN','本次是套牌结果');row=b.n(100002,'ITER_TABLE_KEY_INT')
    scan=traverse(e,t,[e.branch([faction(e,t,row),e.compare(typename(t,row),'==',aid,'ABILITY_COMPARE')],[e.set(wei,r.flag(True)),
      e.branch([e.yes(r.get(t,row,'是否合成','BOOLEAN')),e.compare(r.get(t,row,'子归类'),'==',b.text('八虎骑'),'STRING_COMPARE')],[e.set(result,r.flag(True))])])])
    save(e,[e.branch([e.exists(u)],[e.set(wei,r.flag(False)),e.set(result,r.flag(False)),e.branch([e.no(boolean(u,BUSY))],[
      e.set(t,config(b.player(u))),scan,e.branch([e.yes(result),e.compare(source,'==',r.i(2))],[
        r.skv(e,u,r.join(b.text(COMPLETED),typekey(aid)),r.flag(True))])]),call(e,14,u),
      e.branch([e.yes(wei),e.no(boolean(u,BUSY))],[r.section(e,'仅自然选卡或自动合成触发对应概率',[
        e.branch([e.compare(source,'==',r.i(1))],[call(e,17,u,b.text('选卡获骑概率'))]),
        e.branch([e.compare(source,'==',r.i(2))],[call(e,17,u,b.text('合成获骑概率'))])]),call(e,19,u)])])])
    e=Function(21,[('UNIT_ENTITY','卡牌载体'),('INTEGER','奖励表行号')],
      '复用原授予和解锁流程，锁住奖励来源；概率赠送不调用选卡处理、不吞噬组件。返回实际授予实例。')
    u=e.var('UNIT_ENTITY','卡牌载体');row=e.var('INTEGER','奖励表行号');t=e.var('TABLE','既有卡牌配置');a=e.var('ABILITY','授予结果')
    save(e,[e.set(a,b.n(100014,'NONE_ABILITY')),e.branch([e.no(boolean(u,BUSY))],[e.set(t,config(b.player(u))),
      e.branch([e.compare(row,'>',r.i(0))],[e.branch([faction(e,t,row),e.no(has_type(u,typename(t,row)))],[
        r.section(e,'① 先加来源锁，再通过既有合成函数写入实例记录',[e.setkv(u,BUSY,r.flag(True)),e.set(a,s.foreign(MERGE,'ABILITY',b.player(u),row))]),
        r.section(e,'② 成功才解锁后续路线与刷新卡牌UI',[e.branch([e.exists(a)],[s.external(e,UNLOCK,b.player(u),row),s.external(e,SHOW,b.player(u),a)])]),
        e.setkv(u,BUSY,r.flag(False)),call(e,14,u)])])]),e.ret('ABILITY',a)])
    return out

def count_helper():
    rel='global_trigger/function/new/条件判断/判断【8虎骑数量】是否满足指定数量.json'
    old=read(rel);e=Function(19,[('PLAYER','执行玩家'),('INTEGER','指定满足数量')],
      '按现有配置与实际持有类型去重计数；已存在或本局已领取EX则不再满足。门槛由调用方公共变量传入。')
    e.obj.update({k:copy.deepcopy(v) for k,v in old.items() if k not in ('action','condition','var_data','func_comment')})
    e.oid=old['trigger_id'];e.serial=e.oid*1000000;e.obj['var_data']=[{},{},[]]
    p=e.var('PLAYER','执行玩家');limit=e.var('INTEGER','指定满足数量');u=e.var('UNIT_ENTITY','卡牌载体');t=e.var('TABLE','既有卡牌配置');seen=e.var('TABLE','已计数类型')
    count=e.var('INTEGER','八虎骑数量');existing=e.var('BOOLEAN','已存在EX');ready=e.var('BOOLEAN','满足条件');row=b.n(100002,'ITER_TABLE_KEY_INT');aid=typename(t,row);key=typekey(aid)
    scan=traverse(e,t,[e.branch([faction(e,t,row),e.yes(has_type(u,aid))],[
      e.branch([e.compare(r.get(t,row,'所属set'),'==',b.text('EX'),'STRING_COMPARE')],[e.set(existing,r.flag(True)),e.setkv(p,CLAIMED,r.flag(True))]),
      e.branch([e.compare(r.get(t,row,'子归类'),'==',b.text('八虎骑'),'STRING_COMPARE')],[e.branch([e.cond('TABLE_HAS_KEY',seen,key)],[],[
        d.set_1d(e,seen,key,r.flag(True)),e.set(count,b.n(100002,'INT_PLUS_ONE',count))])])])])
    actions=[e.set(ready,r.flag(False)),e.set(count,r.i(0)),e.set(existing,r.flag(False)),e.set(u,carrier(p)),e.branch([e.exists(u)],[
      e.set(t,config(p)),e.set(seen,b.n(100011,'GET_NEW_TABLE')),scan,
      e.branch([e.compare(limit,'>',r.i(0)),e.compare(count,'>=',limit),e.no(existing),e.no(boolean(p,CLAIMED)),e.no(boolean(u,BUSY))],[e.set(ready,r.flag(True))])]),e.ret('BOOLEAN',ready)]
    e.obj['func_rtv_name_list']=old['func_rtv_name_list']
    obj=e.finish(actions);obj['func_rtv_name_list']=old['func_rtv_name_list']
    return rel,obj

def build_embedded(specs):
    out={};b.TID=2099882000
    for aid in specs:
        assert not (MAP/f'ability/{aid}.json').exists(),'Existing ECA: review before overwrite'
        e=b.Eca(aid);u=b.unit('ABILITY_OWNER')
        e.trigger('获得卡牌：初始化规则并等待持卡记录写入','ABILITY_OBTAIN',[call(e,1,u,b.ability())])
        e.trigger('等级变化：读取当前技能拥有者后标记刷新','ABILITY_LEVEL_CHANGED',[call(e,14,b.n(100006,'GET_ABILITY_OWNER',b.ability()))])
        e.trigger('失去卡牌：标记刷新，由周期校验覆盖删除时序','ABILITY_LOSE',[call(e,14,u)])
        out[f'ability/{aid}.json']=e.done()
    e=b.Eca(CONTROL,True);u=b.owner();m=b.buff()
    gain=e.trigger('获得控制：监听持卡与波次，等待记录写入','OBTAIN_MODIFIER')
    change=e.trigger('记录变化：刷新有效持卡与全军收益','RECEIVE_CUSTOM_EVENT',[call(e,2,u,m,r.flag(False))],args=[b.lit(100238,CHANGE)],
      conditions=[e.compare(b.n(100006,'GET_CUS_EVENT_PARAM',b.lit(100240,'载体单位')),'==',u,'UNIT_COMPARE')],parent=gain,handle='持卡变化监听')
    phase_event=e.trigger('开战：张辽和荀彧每波独立概率','RECEIVE_CUSTOM_EVENT',[call(e,15,u,m)],args=[b.lit(100238,b.PHASE)],
      conditions=[e.compare(b.n(100002,'GET_CUS_EVENT_PARAM',b.lit(100240,'阶段编号')),'==',r.i(2))],parent=gain,handle='开战监听')
    e.obj['trigger_dict'][str(gain)]['action']=[e.setkv(m,r.APPLIED,b.text('未初始化')),e.setkv(m,r.COUNT,b.f(-1)),e.setkv(m,'贾诩累计战斗秒',b.f(0)),
      e.branch([e.compare(phase(),'==',r.i(2))],[e.setkv(u,PREFIX+'已结算波次',s.wave())]),change,phase_event]
    e.trigger('周期兜底：删卡、补兵与贾诩战斗计时','MODIFIER_CYCLE_TRIGGER',[call(e,2,u,m,r.flag(False)),call(e,16,u,m),
      e.branch([e.compare(s.value(m,r.COUNT),'==',b.f(0))],[e.action('REMOVE_BUFF_INS',m)])])
    e.trigger('失去控制：注销监听，只清理本系统持续缓存','LOSS_MODIFIER',[e.unreg('持卡变化监听'),e.unreg('开战监听'),call(e,10,u)])
    out[f'modifier/{CONTROL}.json']=e.done()
    # Reuse the current stat Buff lifecycle, remove Shu's kill listener entirely.
    doc=read(f'modifier/{s.ARMY}.json')
    killids={int(k) for k,t in doc['trigger_dict'].items() if t['event'][0]['event_type']=='SPECIAL_UNIT_EVENT'}
    for k in killids:doc['trigger_dict'].pop(str(k));doc['local_variable'].pop(str(k),None)
    for t in doc['trigger_dict'].values():
        t['action']=[a for a in t['action'] if not (isinstance(a,int) and a in killids) and not any(n.get('items',[None,None])[1:2]==['本单位击杀监听'] for n in b.walk(a))]
        t['trigger_name']=t['trigger_name'].replace('与本单位击杀','').replace('两个','一个')
    for field in ('variable_dict',):
        for values in doc[field].values():values.pop('本单位击杀监听',None)
    doc['variable_length_dict'].pop('本单位击杀监听',None)
    doc['variable_group_info']=[x for x in doc['variable_group_info'] if x['items'][0]!='本单位击杀监听']
    doc['trigger_group_info']=[x for x in doc['trigger_group_info'] if not (x.get('__tuple__') and x['items'][0] in killids)]
    doc=translated(doc)
    idmap={int(k):2099882200+i for i,k in enumerate(doc['trigger_dict'])}
    def remap(node):
        if isinstance(node,list):return [remap(x) for x in node]
        if isinstance(node,dict):return {str(idmap[int(k)]) if str(k).isdigit() and int(k) in idmap else k:remap(v) for k,v in node.items()}
        if isinstance(node,int) and not isinstance(node,bool):return idmap.get(node,node)
        return node
    doc=remap(doc);serial=ARMY*1000000
    for n in b.walk(doc['trigger_group_info']):
        if n.get('__tuple__') and str(n['items'][0]) in doc['trigger_dict']:
            n['items'][1]=doc['trigger_dict'][str(n['items'][0])]['trigger_name']
    for n in b.walk(doc):
        if 'element_id' in n:serial+=1;n['element_id']=serial
    out[f'modifier/{ARMY}.json']=doc
    return out

def patch_shared():
    out={}
    for name,source in [('3选1军略卡牌处理',1),('军略3选1-处理合成的新卡牌',2)]:
        rel=f'global_trigger/function/new/功能执行/{name}.json';doc=read(rel)
        if source==1:
            removed=[]
            for node in b.walk(doc):
                if node.get('arg_type')==100022:
                    oldlen=len(node['args_list']);node['args_list']=[a for a in node['args_list'] if not(isinstance(a,dict) and a.get('element_id')==454042343001339)]
                    if len(node['args_list'])<oldlen:removed.append(True)
            assert len(removed)==1,'Old Wei EX branch not uniquely located'
            repair_wei_set_completion(doc)
        u=carrier(b.n(100025,'VARIABLE',r.tp(['PLAYER','执行玩家','local'])))
        e=Function(20,[], '')
        if source==1:aid=b.n(100039,'VARIABLE',r.tp(['ABILITY_NAME','处理技能类型','local']))
        else:aid=typename(config(b.n(100025,'VARIABLE',r.tp(['PLAYER','执行玩家','local']))),b.n(100002,6,r.tp(['INTEGER','合成的新卡牌Index','local'])))
        action=call(e,20,u,r.i(source),aid);action['element_id']=max(n.get('element_id',0) for n in b.walk(doc))+1
        at=len(doc['action'])-1 if doc['action'][-1].get('action_type')==400342 else len(doc['action'])
        doc['action'].insert(at,action);out[rel]=doc
    rel,obj=count_helper();out[rel]=obj
    return out

def repair_wei_set_completion(doc):
    """Do not use result ownership as the gate for consuming/hiding a full set.

    A probability gift can own the result before its component set is full.
    Keep native hide/unlock steps; grant and result animation only when absent.
    """
    wei=next(n for n in b.walk(doc) if n.get('element_id')==454042342999360)
    branch=wei['args_list'][1]['args_list'][1]['args_list'][1]['args_list'][0]['args_list'][1]['args_list'][0]
    assert branch['action_type']=='IF_THEN_ELSE'
    conditions=branch['args_list'][0]['args_list']
    removed=[n for n in conditions if any(x.get('args_list')==['是否解锁'] for x in b.walk(n))]
    assert len(removed)==1,'Wei completion ownership gate changed; review live ECA'
    branch['args_list'][0]['args_list']=[n for n in conditions if n not in removed]
    actions=branch['args_list'][1]['args_list']
    def original(fid):return copy.deepcopy(next(a for a in actions if a.get('action_type')=='CALL_TRIGGER_FUNC' and a['args_list'][0]['sub_type']==fid))
    grant=original(MERGE);hide=original('5ec39849b3e211f197f88b7bdf2d7282');unlock=original(UNLOCK);show=original(SHOW)
    p=copy.deepcopy(grant['args_list'][0]['args_list'][0]);row=copy.deepcopy(grant['args_list'][0]['args_list'][1]);u=carrier(p);aid=typename(config(p),row)
    e=Function(20,[],'');a=b.n(100014,2,r.tp(['ABILITY','新增主动合成军略技能','local']))
    branch['args_list'][1]['args_list']=[e.set(a,b.n(100014,'NONE_ABILITY')),
      r.section(e,'① 已有赠送UR时不重复发牌；自然合成仍须收尾',[
        e.branch([e.no(has_type(u,aid))],[e.set(a,s.foreign(MERGE,'ABILITY',p,row))])]),
      hide,unlock,
      r.section(e,'② 正常折叠组件；已有结果也结算一次自然合成',[
        e.branch([e.exists(a)],[show],[call(e,20,u,r.i(2),aid)])]),copy.deepcopy(actions[-1])]
    serial=max(n.get('element_id',0) for n in b.walk(doc))+1
    # Refresh identities only within the replaced result branch.
    for n in b.walk(branch):
        if 'element_id' in n:serial+=1;n['element_id']=serial
    return doc


if __name__=='__main__':
    raise SystemExit("Maintenance library only; original one-time staging/publication has been retired. Use the regression tests and review scoped changes against the current map.")
