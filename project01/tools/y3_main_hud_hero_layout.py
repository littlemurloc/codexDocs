"""Pure HUD reconstruction helpers for frozen-source regressions.

No staging or publication entry point. This historical core reconstruction
excludes the separately tested dynamic-hero registration extension. Accepted
HUD resources are also tested from fixed samples; never deploy this whole build.
"""
from __future__ import annotations
import copy,hashlib,json,uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAP=Path('D:/littl/testTempFile/ProjectMonster02/maps/map3')
HUD='ui/GameHUD.json'
U1='global_trigger/trigger/关卡初始化内容/universe01.json'
CREATE='global_trigger/function/new/功能执行/动态创建玩家新队长单位.json'
REBIND='global_trigger/function/new/镜像挑战/06_刷新队伍界面.json'
FN_DIR='global_trigger/function/new/UI'
FN1=FN_DIR+'/刷新主HUD英雄列表与详情.json'
FN2=FN_DIR+'/返回主HUD详情对应英雄.json'
TRIG='global_trigger/trigger/UI/主HUD英雄信息.json'
FI=FN_DIR+'/index.txt'; TI='global_trigger/trigger/UI/index.txt'
INPUTS=[HUD,U1,CREATE,REBIND,FI,TI]
PANEL='9640265b-a269-4e81-a844-0411dd08a982'
NS='project01/y3/main-hud-heroes/v1/'
uid=lambda x:str(uuid.uuid5(uuid.NAMESPACE_URL,NS+x))
FID1=uuid.uuid5(uuid.NAMESPACE_URL,NS+'refresh').hex
FID2=uuid.uuid5(uuid.NAMESPACE_URL,NS+'resolve').hex
TID=2099947400
SHELL=uid('shell');ROSTER=uid('roster')
SELECTED='主HUD_选中英雄';CACHE='主HUD_头像单位_';DEAD='主HUD_头像死亡_'
KIND={'PLAYER':(100025,'VARIABLE',0),'UNIT_ENTITY':(100006,11,0),
      'UI_COMP':(100070,'VARIABLE',''),'INTEGER':(100002,6,0),
      'BOOLEAN':(100001,'VARIABLE',False),'TABLE':(100011,'VARIABLE',0),
      'ABILITY':(100014,2,None),'ITEM_ENTITY':(100031,4,0)}
def load(p):return json.loads(p.read_bytes())
def encode(d):return (json.dumps(d,ensure_ascii=True,indent=4)+'\n').encode('utf8')
def sha(b):return hashlib.sha256(b).hexdigest()
def walk(n):
    if isinstance(n,dict):
        yield n
        for v in n.values():yield from walk(v)
    elif isinstance(n,list):
        for v in n:yield from walk(v)
def ex(t,s,*a,**kw):return dict(arg_type=t,sub_type=s,args_list=list(a),**kw)
def lit(t,v):return ex(t,1,v)
def txt(v):return lit(100003,v)
def integer(v):return lit(100002,v)
def flag(v):return lit(100001,v)
def ref(k,n):return ex(*KIND[k][:2],{'__tuple__':True,'items':[k,n,'local']})
def none():return ex(100006,'NONE_UNIT')
def join(a,b):return ex(100003,'STR_JOIN',txt(a)if isinstance(a,str)else a,b,
                        op_arg=[None]*8,op_arg_enable=[False]*8)
def numstr(v):return ex(100003,'INT_TO_STR',v)
def pindex(p):return ex(100002,'9384d061198e11ef967be8c829c05699',p,call_rt_index=0,op_arg=[],op_arg_enable=[])
def table(p):return ex(100011,'VARIABLE',{'__tuple__':True,'items':['TABLE','玩家队伍信息-表']},pindex(p))
def group(p):return ex(100026,14,{'__tuple__':True,'items':['UNIT_GROUP','玩家队伍']},pindex(p))
def row(k,t,i,col):return ex(KIND[k][0],{'UNIT_ENTITY':'GET_UNIT_ENTITY_TABLE_VAR_ND','UI_COMP':'GET_UI_COMP_TABLE_VAR_ND'}[k],t,i,txt(col))
def kv(k,obj,key):return ex(KIND[k][0],{'UNIT_ENTITY':'GET_UNIT_ENTITY_KV','BOOLEAN':'GET_BOOLEAN_KV'}[k],obj,txt(key)if isinstance(key,str)else key)
def ui(p,root,path):return ex(100070,'GET_UI_COMP_BY_PATH',p,lit(100070,root)if isinstance(root,str)else root,txt(path)if isinstance(path,str)else path)
def parent(p,c,count=1):
    for _ in range(count):c=ex(100070,'GET_UI_COMP_PARENT',p,c)
    return c
def foreign(fid,typ,*args):return ex(typ,fid,*args,call_rt_index=0,op_arg=[],op_arg_enable=[])

class Nodes:
    def __init__(self,start=TID*1000000):self.serial=start
    def node(self,field,name,*args,**kw):
        self.serial+=1
        d=dict(args_list=copy.deepcopy(list(args)),element_id=self.serial,enable=True,**kw);d[field]=name
        if field=='action_type':d['bp']=False
        return d
    def act(self,name,*a,**kw):return self.node('action_type',name,*a,**kw)
    def cond(self,name,*a):return self.node('condition_type',name,*a)
    def cmp(self,a,op,b,kind='ANY_COMPARE'):
        return self.cond(kind,a,lit(100015 if kind=='FLOAT_COMPARE'else 100035,op),b)
    def branch(self,cs,yes,no=()):return self.act('IF_THEN_ELSE',ex(100021,1,*cs),ex(100022,1,*yes),ex(100022,1,*no))
    def exists(self,o):return self.cond('TYPE_IS_EXIST',o)
    def has(self,o,k):return self.cond('HAS_KV_ANY',o,txt(k)if isinstance(k,str)else k)
    def set(self,o,v):return self.act('SET_VARIABLE',ex(100030,1,*o['args_list']),v)
    def put(self,o,k,v):return self.act('SET_ENTITY_KV',o,txt(k)if isinstance(k,str)else k,v)
    def call(self,fid,*args):return self.act('CALL_TRIGGER_FUNC',ex(100177,fid,*args,op_arg=[],op_arg_enable=[]),call_rt_arg_idxes=[])
    def box(self,title,body):return self.act('STORAGE_BOX',ex(100021,1),ex(100022,1,*body),ex(100022,1),txt(title))
    def traverse(self,t,body):return self.act('TRAVERSE_TABLE_NEW',t,ex(100022,1,*body),op_arg=[flag(True)],op_arg_enable=[True])
    def loop(self,i,body):return self.act('FOR_INT_DO_ACTION_NEW',i,integer(1),integer(10),ex(100022,1,*body),op_arg=[None],op_arg_enable=[False])
    def visible(self,p,c,v):
        return self.branch([self.cmp(ex(100001,'GET_UI_COMP_VISIBLE',p,c),'!=',v,'BOOL_COMPARE')],[self.act('SET_UI_COMP_VISIBLE',p,v,c)])

def declare(d,kind,name,array=False):
    d['var_data'][0].setdefault(kind,{})[name]=KIND.get(kind,(0,0,''))[2]
    d['var_data'][1][name]=10 if array else 0;d['var_data'][2].append(name)
    return ref(kind,name)if kind in KIND else None
def function(template,fid,tid,name,params,comment):
    d=copy.deepcopy(template)
    for k in ['func_return_list','func_return_type','return_type','sub_trigger']:d.pop(k,None)
    d.update(action=[],condition=[],event=[],var_data=[{},{},[]],func_id=fid,trigger_id=tid,
      func_name=name,trigger_name=name,func_comment=comment,group_id=template['group_id'],valid=True,
      func_param_list=[{'__tuple__':True,'items':[n,True]}for k,n in params],
      func_des=name+'：'+ '，'.join(n+'{'+n+'}'for k,n in params))
    for k,n in params:declare(d,k,n)
    return d

def fix_empty_ui_resource(d):
    """An unassigned native UI local is legal; an empty resource ID is not."""
    bad=[n for n in walk(d)if n.get('arg_type')==100070 and n.get('sub_type')==1 and n.get('args_list')==['']]
    assert len(bad)==2,'Review changed initialization before applying this repair'
    empty=declare(d,'UI_COMP','空详情引用')
    for n in bad:n.clear();n.update(copy.deepcopy(empty))
    return d

def register_hud_handlers(d,initializer):
    """Native child trigger definitions must be reachable from root startup."""
    assert not d['event']and not d['action']and len(d['sub_trigger'])==8
    event=copy.deepcopy(initializer['event'][0])
    assert event['event_type']=='RECEIVE_CUSTOM_EVENT'and event['args_list'][0]['args_list']==[1866239406]
    event['element_id']=TID*1000000+900001
    d['event']=[event]
    # Native child definitions are instantiated by integer nodes in action[].
    # Four-item tuples refer to another action block, not child registration.
    for s in d['sub_trigger'].values():s['enabled']=False
    d['action']=[s['trigger_id']for s in d['sub_trigger'].values()]
    return d

def repair_hud_registration_references(d):
    found=[]
    for index,action in enumerate(d['action']):
        if isinstance(action,list)and len(action)==4 and action[2:]==[TID,'action_type']:
            tid,name,_,_=action;s=d['sub_trigger'][str(tid)]
            assert s['trigger_name']==name and s['p_trigger_id']==TID
            d['action'][index]=tid;s['enabled']=False;found.append(tid)
    assert len(found)==8 and set(found)=={s['trigger_id']for s in d['sub_trigger'].values()}
    return d

def repair_roster_click_targets(hud):
    """Use a native button as the hit target; all avatar artwork is decorative."""
    roster=next(n for n in walk(hud)if n.get('uid')==ROSTER)
    for slot in roster['children']:
        if not slot['name'].isdigit():continue
        i=int(slot['name']);icon=child(slot,'头像')
        assert slot['type']==7 and icon['event_list']==[event(eventname(i,'选择'),30)]
        slot.update(type=1,swallow_touches=True,normal_picture=None,
          normal_color=tuple_(255,255,255,0),event_list=icon['event_list'])
        for decoration in slot['children']:decoration['swallow_touches']=False
        icon['event_list']=[]
    return hud

def repair_roster_click_handler(d):
    """Low-frequency native diagnostics, never called by the HUD refresh timer."""
    n=Nodes((TID+30)*1000000)
    def log(message):
        return n.act('PRINT_MESSAGE_ACTION_TO_DIALOG',lit(100175,3),txt(message)if isinstance(message,str)else message)
    p=ex(100025,'TRIGGER_PLAYER');c=ex(100070,'GET_UI_COMP_FROM_EVENT')
    s=d['sub_trigger'][str(TID+3)];i=ref('INTEGER','头像序号');u=ref('UNIT_ENTITY','请求英雄')
    key=join(CACHE,numstr(i));name=ex(100003,'GET_UI_COMP_NAME',p,c)
    s['action']=[log('[主HUD诊断/v2] 收到头像点击'),n.branch([n.exists(c)],[
      n.set(i,ex(100002,'STR_TO_INT',name)),log(join('[主HUD诊断/v2] 按钮序号=',numstr(i))),
      n.branch([n.has(p,key)],[n.set(u,kv('UNIT_ENTITY',p,key)),n.branch([n.exists(u)],[
        log(join('[主HUD诊断/v2] 请求切换=',ex(100003,'GET_UNIT_NAME',u))),n.call(FID1,p,u,flag(False))],
        [log('[主HUD诊断/v2] 忽略：头像对应单位已失效')])],
        [log('[主HUD诊断/v2] 忽略：未找到头像单位缓存')])],
      [log('[主HUD诊断/v2] 忽略：事件没有界面控件')])]
    d['action'].insert(0,log('[主HUD诊断/v2] 初始化：注册8类交互监听'))
    # Temporary instrumentation is retired after native acceptance. Keep node
    # identities of the non-log actions unchanged when generating the final HUD.
    return remove_hud_click_diagnostics(d)

def remove_hud_click_diagnostics(d):
    expected={2099947430000001,2099947430000004,2099947430000008,
      2099947430000010,2099947430000012,2099947430000014,2099947430000016}
    removed=set()
    def edit(value):
        if isinstance(value,list):
            kept=[]
            for item in value:
                if isinstance(item,dict)and item.get('element_id')in expected:
                    assert item.get('action_type')=='PRINT_MESSAGE_ACTION_TO_DIALOG'
                    assert '[主HUD诊断/v2]'in json.dumps(item,ensure_ascii=False)
                    removed.add(item['element_id'])
                else:edit(item);kept.append(item)
            value[:]=kept
        elif isinstance(value,dict):
            for child in value.values():edit(child)
    edit(d);assert removed==expected,('Review the exact registered diagnostic nodes before removing',removed)
    return d

def link_roster_world_selection(d):
    """An explicit valid roster click replaces world selection and focuses once."""
    sub=d['sub_trigger'][str(TID+3)]
    targets=[x for x in walk(sub['action'])if x.get('arg_type')==100022
      and len(x.get('args_list',[]))==1 and isinstance(x['args_list'][0],dict)
      and x['args_list'][0].get('action_type')=='CALL_TRIGGER_FUNC'
      and x['args_list'][0]['args_list'][0].get('sub_type')==FID1]
    assert len(targets)==1,'Review the accepted avatar refresh branch before patching'
    n=Nodes((TID+60)*1000000);p=ex(100025,'TRIGGER_PLAYER');u=ref('UNIT_ENTITY','请求英雄')
    focus=[n.act('SELECT_UNIT',p,none()),n.act('SELECT_UNIT',p,u),
      n.act('NEW_CAMERA_LINEAR_MOVE_TIME',p,ex(100004,'UNIT_ENTITY_POINT',u),lit(100000,0.0),lit(100217,0))]
    # Refresh validates owner/group membership. Only its accepted selection may
    # clear the old world selection; stale, foreign or removed cached units don't.
    targets[0]['args_list'].append(n.branch([n.has(p,SELECTED)],[
      n.branch([n.cmp(kv('UNIT_ENTITY',p,SELECTED),'==',u,'UNIT_COMPARE')],focus)]))
    return d

def gate_hud_battle_visibility(d):
    """The refresh timer must never reopen the hero shell during phase 2."""
    def shows_shell(node):
        return any(x.get('action_type')=='SET_UI_COMP_VISIBLE'
          and x['args_list'][1].get('args_list')==[True]
          and x['args_list'][2].get('args_list')==[SHELL]for x in walk(node))
    targets=[x for x in walk(d['action'])if x.get('arg_type')==100022
      and len(x.get('args_list',[]))==1 and isinstance(x['args_list'][0],dict)
      and x['args_list'][0].get('action_type')=='IF_THEN_ELSE'and shows_shell(x)]
    assert len(targets)==1,'Review shell visibility before applying the phase guard'
    n=Nodes((TID+70)*1000000);p=ref('PLAYER','执行玩家')
    phase=ex(100002,6,tuple_('INTEGER','当前游戏进程阶段'))
    old=targets[0]['args_list']
    targets[0]['args_list']=[n.branch([n.cmp(phase,'==',integer(2),'FLOAT_COMPARE')],
      [n.visible(p,lit(100070,SHELL),flag(False))],old)]
    return d

def build_refresh(template,stats):
    d=function(template,FID1,TID+1,'刷新主HUD英雄列表与详情',
      [('PLAYER','执行玩家'),('UNIT_ENTITY','请求英雄'),('BOOLEAN','强制重绘')],
      '读取现有队伍记录，最多两排各五名；保留当前选择，失效时回退第一名。只写HUD状态和显示，不改队伍、技能或装备。')
    n=Nodes((TID+1)*1000000)
    p=ref('PLAYER','执行玩家');request=ref('UNIT_ENTITY','请求英雄');force=ref('BOOLEAN','强制重绘')
    v={name:declare(d,k,name)for k,name in [('INTEGER','头像序号'),('INTEGER','有效数量'),('INTEGER','选中头像序号'),
      ('UNIT_ENTITY','当前英雄'),('UNIT_ENTITY','选中英雄'),('UNIT_ENTITY','旧选中英雄'),('UNIT_ENTITY','首名英雄'),
      ('UI_COMP','当前详情'),('UI_COMP','选中详情'),('UI_COMP','首名详情'),('UI_COMP','当前头像'),
      ('BOOLEAN','当前死亡'),('BOOLEAN','需要重绘头像'),('BOOLEAN','已有选择') ]}
    idx=ex(100002,'ITER_TABLE_KEY_INT');u=v['当前英雄'];pane=v['当前详情'];count=v['有效数量'];sel=v['选中英雄']
    first=v['首名英雄'];found=v['已有选择'];sp=v['选中详情'];fp=v['首名详情'];i=v['头像序号'];slot=v['当前头像']
    si=v['选中头像序号'];dead=v['当前死亡'];changed=v['需要重绘头像']
    root=lit(100070,SHELL)
    # Each guard is nested: no assumed short circuit before native dereferences.
    def valid(body):
        return n.branch([n.exists(u)],[n.branch([n.cond('UNIT_IN_GROUP',u,group(p))],[
          n.branch([n.cmp(ex(100025,'OWNER_PLAYER',u),'==',p,'PLAYER_COMPARE')],[
          n.branch([n.exists(pane)],[n.branch([n.cmp(count,'<',integer(10),'FLOAT_COMPARE')],body)])])])])
    inspect=[n.set(count,ex(100002,'INT_PLUS_ONE',count)),
      n.branch([n.cmp(count,'==',integer(1),'FLOAT_COMPARE')],[n.set(first,u),n.set(fp,pane)]),
      n.branch([n.cmp(u,'==',sel,'UNIT_COMPARE')],[n.set(found,flag(True)),n.set(sp,pane),n.set(si,count)]),
      n.branch([n.cmp(u,'==',request,'UNIT_COMPARE')],[n.set(sel,u),n.set(found,flag(True)),n.set(sp,pane),n.set(si,count)])]
    def read():return [n.set(u,row('UNIT_ENTITY',table(p),idx,'单位')),n.set(pane,row('UI_COMP',table(p),idx,'人物界面控件'))]
    cachekey=join(CACHE,numstr(count));deadkey=join(DEAD,numstr(count))
    child=lambda name:ui(p,slot,name)
    assign_cache=[n.put(p,cachekey,u),n.act('SET_UI_COMP_IMAGE_NEW',p,child('头像'),ex(100115,'GET_ICON',u)),
      n.act('SET_UI_COMP_TEXT',p,child('姓名'),ex(100003,'GET_UNIT_NAME',u))]
    paint=[n.act('SET_UI_IMAGE_COLOR_HEX',p,child('头像'),txt('#777777'),integer(100))]
    alivepaint=[n.act('SET_UI_IMAGE_COLOR_HEX',p,child('头像'),txt('#ffffff'),integer(100))]
    render=[n.set(count,ex(100002,'INT_PLUS_ONE',count)),n.set(slot,ui(p,ROSTER,numstr(count))),
      n.set(changed,force),n.branch([n.has(p,cachekey)],[n.branch([n.cmp(kv('UNIT_ENTITY',p,cachekey),'!=',u,'UNIT_COMPARE')],[n.set(changed,flag(True))])],[n.set(changed,flag(True))]),
      n.visible(p,slot,flag(True)),n.branch([n.cmp(changed,'==',flag(True),'BOOL_COMPARE')],assign_cache),
      n.set(dead,flag(False)),n.branch([n.cond('UNIT_HAS_TAG',u,txt('已死亡'))],[n.set(dead,flag(True))]),
      n.branch([n.has(p,deadkey)],[n.branch([n.cmp(kv('BOOLEAN',p,deadkey),'!=',dead,'BOOL_COMPARE')],[n.set(changed,flag(True))])],[n.set(changed,flag(True))]),
      n.branch([n.cmp(changed,'==',flag(True),'BOOL_COMPARE')],[n.branch([n.cmp(dead,'==',flag(True),'BOOL_COMPARE')],paint,alivepaint),n.put(p,deadkey,dead)]),
      n.branch([n.cmp(count,'==',si,'FLOAT_COMPARE')],[n.visible(p,child('选中框'),flag(True))],[n.visible(p,child('选中框'),flag(False))]),
      n.visible(p,child('阵亡'),dead)]
    metrics=copy.deepcopy(stats)
    for a in walk(metrics):
        if a.get('action_type')in ['SET_UI_COMP_TEXT','SET_UI_COMP_LOADINGBAR_CURRENT_VALUE','SET_UI_COMP_LOADINGBAR_MAX_VALUE']:
            a['args_list'][0]=copy.deepcopy(p)
            path=a['args_list'][1]['args_list'][2]
            a['args_list'][1]=ui(p,sp,copy.deepcopy(path))
        if a.get('sub_type')=='GET_UNIT_ENTITY_TABLE_VAR_ND':a.clear();a.update(copy.deepcopy(sel))
        elif a.get('sub_type')=='GET_CLIENT_ROLE':a.clear();a.update(copy.deepcopy(p))
        if 'element_id'in a:n.serial+=1;a['element_id']=n.serial
    chosen_updates=[*metrics,n.act('SET_CHECKBOX_SELECTED',p,ui(p,sp,'自动战斗'),kv('BOOLEAN',sel,'自动施法')),
      n.branch([n.cond('UNIT_HAS_TAG',sel,txt('已死亡'))],[n.visible(p,ui(p,sp,'自动战斗'),flag(False))],[n.visible(p,ui(p,sp,'自动战斗'),flag(True))])]
    each=ex(100070,'FOR_EACH_UI_COMP')
    detailvisibility=n.act('ITER_UI_COMP_DO',p,lit(100070,PANEL),ex(100022,1,
      n.branch([n.cmp(each,'==',sp)],[n.visible(p,each,flag(True))],[n.visible(p,each,flag(False))])))
    d['action']=[n.box('① 只读有效队伍，确认默认或请求选择',[
      n.set(count,integer(0)),n.set(si,integer(0)),n.set(sel,none()),n.set(first,none()),n.set(found,flag(False)),n.set(sp,lit(100070,'')),n.set(fp,lit(100070,'')),
      n.branch([n.has(p,SELECTED)],[n.set(sel,kv('UNIT_ENTITY',p,SELECTED))]),n.set(v['旧选中英雄'],sel),
      n.traverse(table(p),[*read(),valid(inspect)]),
      n.branch([n.cmp(found,'==',flag(False),'BOOL_COMPARE')],[n.set(sel,first),n.set(sp,fp),n.branch([n.cmp(count,'>',integer(0),'FLOAT_COMPARE')],[n.set(si,integer(1))])]),
      n.branch([n.cmp(sel,'!=',v['旧选中英雄'],'UNIT_COMPARE')],[n.call('49cfc821b67b11edb8aa00fff84eb1b1',p,flag(False))],
        [n.branch([n.cmp(force,'==',flag(True),'BOOL_COMPARE')],[n.call('49cfc821b67b11edb8aa00fff84eb1b1',p,flag(False))])]),
      n.branch([n.cmp(sel,'!=',v['旧选中英雄'],'UNIT_COMPARE')],[n.put(p,SELECTED,sel)])]),
      n.box('② 两排头像：变化时更新图像，单一高亮，保留阵亡英雄查看',[
        n.set(count,integer(0)),n.traverse(table(p),[*read(),valid(render)]),
        n.loop(i,[n.branch([n.cmp(i,'>',count,'FLOAT_COMPARE')],[n.visible(p,ui(p,ROSTER,numstr(i)),flag(False)),
          n.branch([n.has(p,join(CACHE,numstr(i)))],[n.branch([n.cmp(kv('UNIT_ENTITY',p,join(CACHE,numstr(i))),'!=',none(),'UNIT_COMPARE')],[n.put(p,join(CACHE,numstr(i)),none())])])])]),
        n.branch([n.cmp(count,'==',integer(0),'FLOAT_COMPARE')],[n.visible(p,root,flag(False))],[n.visible(p,root,flag(True))])]),
      n.box('③ 同一位置只展示选中详情，原生技能与装备绑定保持',[
        detailvisibility,n.branch([n.exists(sel)],[n.branch([n.exists(sp)],chosen_updates)])])]
    return gate_hud_battle_visibility(fix_empty_ui_resource(d))

def build_resolve(template):
    d=function(template,FID2,TID+2,'返回主HUD详情对应英雄',[('PLAYER','执行玩家'),('UI_COMP','详情控件')],
      '按人物界面控件反查有效本方队长；不读取旧事件字符串中的单位ID，避免换波重建后串绑。')
    # Same single-unit return declaration as native 工具库/ID转单位.
    d['func_return']=True
    d['func_rtv_name_list']=[{'__tuple__':True,'items':['返回值_英雄','UNIT_ENTITY']}]
    n=Nodes((TID+2)*1000000);p=ref('PLAYER','执行玩家');c=ref('UI_COMP','详情控件')
    result=declare(d,'UNIT_ENTITY','结果英雄');u=declare(d,'UNIT_ENTITY','记录英雄');idx=ex(100002,'ITER_TABLE_KEY_INT')
    pane=row('UI_COMP',table(p),idx,'人物界面控件')
    d['action']=[n.set(result,none()),n.branch([n.exists(c)],[n.traverse(table(p),[
      n.branch([n.cmp(pane,'==',c)],[n.set(u,row('UNIT_ENTITY',table(p),idx,'单位')),
        n.branch([n.exists(u)],[n.branch([n.cond('UNIT_IN_GROUP',u,group(p))],[
          n.branch([n.cmp(ex(100025,'OWNER_PLAYER',u),'==',p,'PLAYER_COMPARE')],[n.set(result,u),n.act('BREAK_LOOP')])])])])])]),
      n.act(400342,result)]
    return d

def tuple_(*items):return {'__tuple__':True,'items':list(items)}
def place(node,x,y,w,h,pw,ph,anchor=(.5,.5)):
    node.update(size=tuple_(w,h),pos_data=tuple_(x,y,x/pw*100,y/ph*100,0,0),anchor=tuple_(*anchor),
      open_adapter=False,adapter_option=[False]*4+[0.]*4)
    return node
def newnode(name,typ,path,x,y,w,h,pw,ph,**kw):
    return place(dict(name=name,type=typ,uid=uid(path),children=[],event_list=[],prefab_sub_key=None,scene_ui_name=None,**kw),x,y,w,h,pw,ph)
def event(name,typ):return dict(action_list=[],enabled=True,name=name,not_wait_network=False,sound_id=None,type=typ)
def eventname(slot,kind,index=0):return f'主HUD_{slot}_{kind}'+(f'_{index}'if index else '')
def child(node,name):return next(c for c in node['children']if c['name']==name)

def layout_equipment(pane):
    # Retain the native equipment slots, UIDs and binding child references.
    # This row sits above the old attribute/skill controls inside the detail.
    eq=child(pane,'equits');place(eq,125,250,136,60,250,600);eq['visible']=True
    assert len(eq['children'])==2
    for j,slot in enumerate(eq['children']):
        place(slot,34+68*j,30,60,60,136,60);slot['visible']=True
        child(slot,'equip_bg_img')['visible']=True

def repair_equipment_layout(hud):
    shell=next(n for n in walk(hud)if n.get('uid')==SHELL)
    roster=next(n for n in walk(hud)if n.get('uid')==ROSTER)
    shell['swallow_touches']=False;roster['swallow_touches']=False
    child(roster,'背景')['swallow_touches']=False
    child(roster,'标题')['swallow_touches']=False
    for slot in roster['children']:
        if slot['name'].isdigit():slot['swallow_touches']=False
    container=next(n for n in walk(hud)if n.get('uid')==PANEL)
    assert len(container['children'])==10
    for pane in container['children']:layout_equipment(pane)
    return hud

def skin_left_roster_b(hud):
    """Approved B skin for the left roster only; right details remain intact."""
    roster=next(n for n in walk(hud)if n.get('uid')==ROSTER)
    bg=child(roster,'背景');bg['image']=134238271;bg['cap_insets']=tuple_(28,28,28,28)
    plate=newnode('队伍标题底板',4,'skinB/title',225,207,275,32,450,220,
      image=134259669,cap_insets=tuple_(16,12,16,12),swallow_touches=False)
    title=child(roster,'标题');place(title,225,207,235,24,450,220)
    title['text']=tuple_('英雄队伍',False);title['font_color']=tuple_(234,216,174,255)
    assert not any(n.get('name')=='队伍标题底板'for n in roster['children'])
    roster['children'].insert(roster['children'].index(title),plate)
    for slot in roster['children']:
        if not slot['name'].isdigit():continue
        index=int(slot['name']);place(slot,57+84*((index-1)%5),142-88*((index-1)//5),78,86,450,220)
        icon=child(slot,'头像');place(icon,39,48,60,60,78,86)
        border=newnode('头像边框',4,f'skinB/portrait/{index}',39,48,72,76,78,86,
          image=134249861,swallow_touches=False)
        highlight=child(slot,'选中框');highlight['image']=134279866;place(highlight,39,48,78,82,78,86)
        label=child(slot,'姓名');place(label,39,7,78,18,78,86)
        label['font']=tuple_('HKSongW9',15);label['font_color']=tuple_(216,201,173,255)
        dead=child(slot,'阵亡')
        # Every decorative descendant passes input to the unchanged button.
        slot['children']=[icon,border,highlight,label,dead]
        for decoration in slot['children']:decoration['swallow_touches']=False
    return fix_roster_skin_bounds(hud)

def fix_roster_skin_bounds(hud):
    """Keep text and both portrait rows inside the existing 28px frame inset."""
    roster=next(n for n in walk(hud)if n.get('uid')==ROSTER)
    title=child(roster,'标题');plate=child(roster,'队伍标题底板')
    place(plate,225,210,275,28,450,220)
    place(title,225,210,235,22,450,220);title['alignment']=tuple_(2,8)
    for slot in roster['children']:
        if not slot['name'].isdigit():continue
        i=int(slot['name']);place(slot,75+75*((i-1)%5),151-83*((i-1)//5),74,82,450,220)
        place(child(slot,'头像'),37,50,48,48,74,82)
        place(child(slot,'头像边框'),37,50,56,60,74,82)
        place(child(slot,'选中框'),37,50,60,64,74,82)
        label=child(slot,'姓名');place(label,37,9,74,16,74,82)
        label['font']=tuple_('HKSongW9',14);label['alignment']=tuple_(2,8)
        dead=child(slot,'阵亡');place(dead,37,50,48,20,74,82)
        dead['font']=tuple_('HKSongW9',14);dead['alignment']=tuple_(2,8)
    return hud

def build_hud(original):
    d=copy.deepcopy(original);old=next(n for n in d['children']if n['uid']==PANEL)
    tenth=copy.deepcopy(old['children'][0]);mapping={n['uid']:uid('detail10/'+n['uid'])for n in walk(tenth)if 'uid'in n}
    def swap(x):
        if isinstance(x,str):return mapping.get(x,x)
        if isinstance(x,list):return [swap(v)for v in x]
        if isinstance(x,dict):return {k:swap(v)for k,v in x.items()}
        return x
    tenth=swap(tenth);tenth['name']='局内单位信息_10';old['children'].append(tenth)
    old.update(type=7,margin=0.,size_change_according_children=False)
    place(old,605,0,250,600,750,600,(.5,0))
    # Each existing view keeps all descendant identities and native binding paths.
    for index,pane in enumerate(old['children'],1):
        place(pane,125,0,250,600,250,600,(.5,0));pane['visible']=False
        bg=child(child(pane,'bgFrame'),'bg')
        bg['event_list']=[event(eventname(index,'头像点击'),30),event(eventname(index,'头像移入'),24),event(eventname(index,'头像移出'),25)]
        child(pane,'自动战斗')['event_list']=[event(eventname(index,'自动施法'),30)]
        child(pane,'sequence_animation_select')['visible']=False
        for j,btn in enumerate(child(pane,'skill')['children'],1):
            child(btn,'skill_icon_img')['event_list']=[event(eventname(index,'技能悬停',j),24),event(eventname(index,'技能离开',j),25)]
        for j,btn in enumerate(child(pane,'equits')['children'],1):
            child(btn,'equip_icon_img')['event_list']=[event(eventname(index,'装备悬停',j),24),event(eventname(index,'装备离开',j),25)]
    shell=newnode('英雄信息区',7,'shell',960,0,750,600,1920,1080,visible=False)
    shell['uid']=SHELL;place(shell,960,0,750,600,1920,1080,(.5,0))
    roster=newnode('英雄队伍头像',7,'roster',234,116,450,220,750,600)
    roster['uid']=ROSTER
    bg=newnode('背景',4,'roster-bg',225,110,450,220,450,220,image=904140,cap_insets=tuple_(20,20,20,20))
    roster['children'].append(bg)
    title=newnode('标题',3,'roster-title',225,198,410,24,450,220,
      font=tuple_('HKSongW9',18),font_color=tuple_(237,221,178,255),text=tuple_('英雄队伍 · 点击头像查看',False))
    roster['children'].append(title)
    # Stable names are the roster index. This is UI capacity, not deployment cap.
    for j in range(1,11):
        x=45+90*((j-1)%5);y=144-90*((j-1)//5)
        slot=newnode(str(j),7,f'roster/{j}',x,y,78,86,450,220,visible=False)
        icon=newnode('头像',4,f'roster/{j}/icon',39,48,64,64,78,86,image=999)
        icon['event_list']=[event(eventname(j,'选择'),30)]
        highlight=newnode('选中框',4,f'roster/{j}/selected',39,48,72,72,78,86,image=133783,visible=False)
        # Selection overlay must not intercept the portrait's click.
        highlight['swallow_touches']=False
        icon['swallow_touches']=True
        label=newnode('姓名',3,f'roster/{j}/name',39,7,84,18,78,86,font=tuple_('HKSongW9',14),font_color=tuple_(240,233,211,255),text=tuple_('',False))
        dead=newnode('阵亡',3,f'roster/{j}/dead',39,48,64,22,78,86,font=tuple_('HKSongW9',16),font_color=tuple_(255,200,190,255),text=tuple_('阵亡',False),visible=False)
        label['swallow_touches']=False;dead['swallow_touches']=False
        slot['children']=[highlight,icon,label,dead];roster['children'].append(slot)
    shell['children']=[roster,old]
    d['children'][d['children'].index(old)]=shell
    return skin_left_roster_b(repair_roster_click_targets(repair_equipment_layout(d)))

def remove_dynamic_registration(d):
    """Only HUD registration actions; preserve gameplay/item actions verbatim."""
    names={'单位信息展示skillTips','单位信息展示itemTips','hide_tips','单位头像鼠标移入','单位头像鼠标移出','单位头像鼠标点击','开关自动战斗'}
    removed=[]
    def edit(x):
        if isinstance(x,dict):
            for v in x.values():edit(v)
        elif isinstance(x,list):
            keep=[]
            for v in x:
                if isinstance(v,dict)and v.get('action_type')=='CREATE_UI_COMP_EVENT_EX_EX'and v['args_list'][2].get('args_list',[None])[0]in names:removed.append(copy.deepcopy(v))
                else:edit(v);keep.append(v)
            x[:]=keep
    edit(d);return removed

def build_bindings(original,kind,n):
    d=copy.deepcopy(original);removed=remove_dynamic_registration(d)
    assert len(removed)==8
    if kind=='create':
        p=ref('PLAYER','执行玩家');body=d['action'][10]['args_list'][1]['args_list']
        assert body[0]['action_type']=='ITER_UI_COMP_DO'
        # Invisible means unselected now, not unallocated. Row allocation remains
        # the current append-only team table's index, as in the existing creator.
        oldid=body[0]['element_id']
        body[0]=n.set(ref('UI_COMP','单位信息-控件'),ui(p,PANEL,join('局内单位信息_',numstr(ex(100002,'GET_TABLE_LENGTH',table(p))))))
        body[0]['element_id']=oldid
        d['action'].append(n.call(FID1,p,none(),flag(True)))
    else:
        p=ex(100025,'PICKED_PLAYER')
        d['action'][0]['args_list'][1]['args_list'].append(n.call(FID1,p,none(),flag(True)))
    return d,removed

def build_trigger(template,u1,n):
    d={k:copy.deepcopy(template[k])for k in ['call_enabled','condition','enabled','event','group_id','p_trigger_id','valid']}
    d.update(action=[],event=[],condition=[],trigger_id=TID,trigger_name='主HUD英雄信息',sub_trigger={},var_data=[{},{},[]],enabled=True,group_id=0)
    p=ex(100025,'TRIGGER_PLAYER');c=ex(100070,'GET_UI_COMP_FROM_EVENT')
    def sub(number,title,names):
        tid=TID+number
        s=dict(action=[],call_enabled=True,condition=[],enabled=True,event=[],group_id=0,is_conf=True,p_trigger_id=TID,
          trigger_id=tid,trigger_name=title,valid=True,var_data=[{},{},[]])
        for name in names:s['event'].append(n.node('event_type','TRIGGER_COMPONENT_EVENT',ex(100067,'STR_TO_UI_EVENT',txt(name))))
        d['sub_trigger'][str(tid)]=s;return s
    def names(kind,slots=1):return [eventname(i,kind,j if slots>1 else 0)for i in range(1,11)for j in range(1,slots+1)]
    def resolve(s,depth):
        u=declare(s,'UNIT_ENTITY','事件英雄')
        return u,n.set(u,foreign(FID2,100006,p,parent(p,c,depth)))
    roster=sub(3,'头像列表：选择英雄并刷新右侧',names('选择'))
    u=declare(roster,'UNIT_ENTITY','请求英雄');i=declare(roster,'INTEGER','头像序号')
    key=join(CACHE,numstr(i))
    roster['action']=[n.set(i,ex(100002,'STR_TO_INT',ex(100003,'GET_UI_COMP_NAME',p,parent(p,c)))),
      n.branch([n.has(p,key)],[n.set(u,kv('UNIT_ENTITY',p,key)),n.branch([n.exists(u)],[n.call(FID1,p,u,flag(False))])])]
    click=sub(4,'详情头像：沿用选择单位与镜头定位',names('头像点击'));u,read=resolve(click,2)
    original=copy.deepcopy(u1['sub_trigger']['878744228']['action'])
    camera=original[1:5]+original[6:]
    for node in walk(camera):
        if node.get('arg_type')==100006 and node.get('args_list')==[tuple_('UNIT_ENTITY','所选单位','local')]:node.clear();node.update(copy.deepcopy(u))
        if 'element_id'in node:n.serial+=1;node['element_id']=n.serial
    click['action']=[read,n.branch([n.exists(u)],[n.call(FID1,p,u,flag(False)),*camera])]
    auto=sub(5,'自动施法：只操作事件所属英雄',names('自动施法'));u,read=resolve(auto,1)
    body=copy.deepcopy(u1['sub_trigger']['1252070104']['action'][1:3])
    for node in walk(body):
        if node.get('arg_type')==100006 and node.get('args_list')==[tuple_('UNIT_ENTITY','所选单位','local')]:node.clear();node.update(copy.deepcopy(u))
        if 'element_id'in node:n.serial+=1;node['element_id']=n.serial
    auto['action']=[read,n.branch([n.exists(u)],[n.branch([n.cond('UNIT_HAS_TAG',u,txt('已死亡'))],[],[*body,n.call(FID1,p,none(),flag(False))])])]
    tipfid='49cfc821b67b11edb8aa00fff84eb1b1'
    for number,kind,num,typ,exprname,returnkind in [(6,'技能悬停',3,100014,'UNIT_ABILITY','ABILITY'),(7,'装备悬停',2,100031,'UNIT_SLOT_ITEM','ITEM_ENTITY')]:
        s=sub(number,kind+'：按当前详情绑定读取',names(kind,num));u,read=resolve(s,3)
        declare(s,'STRING','控件名称分段',True)
        entity=declare(s,returnkind,'提示对象')
        split=n.act('SET_VARIABLE_STR_LIST',ex(100167,1,tuple_('STRING','控件名称分段','local')),
          ex(100003,'GET_UI_COMP_NAME',p,parent(p,c)),txt('_'))
        index=ex(100002,'STR_TO_INT',ex(100003,2,tuple_('STRING','控件名称分段','local'),integer(2)))
        # Native UI buttons are skill_btn_N / equip_slot_N; string-array indices are zero based.
        get=ex(typ,exprname,u,lit(100182 if typ==100014 else 100135,3 if typ==100014 else 0),index)
        op=[None]*9;flags=[False]*9;which=0 if typ==100014 else 2
        op[which]=entity;flags[which]=True
        call=n.act('CALL_TRIGGER_FUNC',ex(100177,tipfid,p,flag(True),op_arg=op,op_arg_enable=flags),call_rt_arg_idxes=[])
        if typ==100014:
            # Retain the native hero-description-table switch from universe01's
            # former skill tip. Item tips don't enable that skill-only option.
            call['args_list'][0]['op_arg'][8]=flag(True);call['args_list'][0]['op_arg_enable'][8]=True
            tablecall=copy.deepcopy(call);tablecall['args_list'][0]['op_arg'][8]=flag(False)
            n.serial+=1;tablecall['element_id']=n.serial
            show=[n.branch([n.cond('UNIT_HAS_TAG',ex(100116,'GET_UNIT_KEY_OF_UNIT',u),txt('仆从伙伴'))],[tablecall],[call])]
        else:show=[call]
        s['action']=[read,n.call(tipfid,p,flag(False)),n.branch([n.exists(u)],[split,n.set(entity,get),n.branch([n.exists(entity)],show)])]
    hide=sub(8,'提示离开：沿用统一提示关闭',names('技能离开',3)+names('装备离开',2))
    hide['action']=[n.call(tipfid,p,flag(False))]
    for number,kind,oldid in [(9,'头像移入','1784713890'),(10,'头像移出','492868259')]:
        s=sub(number,kind+'：保留原头像反馈',names(kind));s['action']=copy.deepcopy(u1['sub_trigger'][oldid]['action'])
        for node in walk(s['action']):
            if 'element_id'in node:n.serial+=1;node['element_id']=n.serial
    return link_roster_world_selection(repair_roster_click_handler(register_hud_handlers(d,u1)))

def build(inputs,template):
    out={};n=Nodes((TID+20)*1000000)
    u1=copy.deepcopy(inputs[U1]);stats=u1['action'][2]['args_list'][1]['args_list'][1]['args_list'][2]['args_list'][0]['args_list'][1]['args_list']
    assert len(stats)==7
    out[FN1]=build_refresh(template,stats);out[FN2]=build_resolve(template)
    out[HUD]=build_hud(inputs[HUD])
    # Single existing UI timer, no new per-unit timer. Only selected detail metrics.
    timer=u1['action'][2]['args_list'][1]['args_list'][1]
    assert timer['action_type']=='RUN_LOOP_TIMER_NO_SAVE'
    timer['args_list'][0]=lit(100000,.1)
    timer['args_list'][2]['args_list']=[n.call(FID1,ex(100025,'GET_CLIENT_ROLE'),none(),flag(False))]
    visibility=[]
    for node in walk(u1):
        if node.get('action_type')=='SET_UI_COMP_VISIBLE'and node['args_list'][2].get('args_list')==[PANEL]:
            visibility.append(copy.deepcopy(node));node['args_list'][2]=lit(100070,SHELL)
    assert len(visibility)==2
    out[U1]=u1
    out[CREATE],removed1=build_bindings(inputs[CREATE],'create',n)
    out[REBIND],removed2=build_bindings(inputs[REBIND],'rebind',n)
    out[TRIG]=build_trigger(template,inputs[U1],n)
    for rel,added in [(FI,[Path(FN1).name,Path(FN2).name]),(TI,[Path(TRIG).name])]:
        index=copy.deepcopy(inputs[rel]);assert all(k not in index for k in added)
        for name in added:index[name]=max(index.values(),default=-1)+1
        out[rel]=index
    return out,dict(retired_dynamic_event_nodes=removed1+removed2,phase_visibility_before=visibility)


if __name__=='__main__':
    raise SystemExit('Historical publisher removed. Run test_y3_main_hud_hero_layout.py for read-only regression.')
