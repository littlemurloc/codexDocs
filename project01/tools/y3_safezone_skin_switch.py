"""Build a scoped, hash-guarded Y3 safe-zone skin change; never publish on import.

All JSON round-trips use Python integers. `stage` only writes the workspace.
`publish` checks the reviewed manifest and every source hash before any write.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import uuid
from pathlib import Path
from safezone_ui_fixtures import retired_publish

ROOT = Path(__file__).resolve().parents[1]
PROJECT = Path('D:/littl/testTempFile/ProjectMonster02')
MAP = 'maps/map3/'
WORK = ROOT / 'tmp/safezone-skin-switch-20261119'
NS = 'project01/y3/safezone-skins/20261119/'
TID = 2101119000
TABLE_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, NS + 'directory'))
UI = MAP + 'ui/安全区主界面.json'
OLD = MAP + 'global_trigger/trigger/UI/安全区主界面.json'
TRIGGER = MAP + 'global_trigger/trigger/UI/安全区界面风格交互.json'
FN_DIR = MAP + 'global_trigger/function/new/UI/'
TI = MAP + 'global_trigger/trigger/UI/index.txt'
FI = FN_DIR + 'index.txt'
GLOBAL_VARS = MAP + 'globaltriggervariable.json'
TABLE = MAP + 'tables/安全区界面风格配置表.json'
TABLE_GROUP = MAP + 'editor/tableeditorgroupinfo.json'
SAFE_ROOT = '0ce5e53c-9ee4-4de7-a5bb-c5a8e2e06912'
OLD_PAGES = 'aa2908ee-092c-465d-99cc-5674c378117e'
PAGE_IDS = ['c01e93a1-5fdf-442a-819d-0d5b4958f7b8',
            '69119d4b-3a52-4db6-a895-e12d0d183425',
            '4109841c-f4fc-4985-b13a-3ac826d5b88f']
TROOP_PARENT = '9873c4ec-a034-487e-91b4-e638c7195a5e'
TROOP_PAGE = '7f98f0d6-f593-4109-bd4e-9386fc6b4577'
SLOT = 19
CURRENT = '安全区风格_当前'
PENDING = '安全区风格_待确认'
BUSY = '安全区风格_处理中'
READY = '安全区风格_已初始化'
REGISTERED = '安全区风格_监听已注册'
NAMES = ['清瓷地图', '朱印令牌', '墨刷浮层', '玄铁铜铆',
         '军务档案', '青玉璧环', '基础金边', '墨金战阵']
FUNCTION_NAMES = ['应用安全区界面风格', '刷新安全区营地摘要', '切换安全区外层导航',
                  '初始化安全区界面风格', '处理安全区风格选择']
FIDS = {n: uuid.uuid5(uuid.NAMESPACE_URL, NS + n).hex for n in FUNCTION_NAMES}
TYPES = {'PLAYER': (100025, 'VARIABLE', 0), 'INTEGER': (100002, 6, 0),
         'BOOLEAN': (100001, 'VARIABLE', False), 'UI_COMP': (100070, 'VARIABLE', ''),
         'UNIT_NAME': (100116, 2, 0), 'STRING': (100003, 'VARIABLE', '')}


def uid(name): return str(uuid.uuid5(uuid.NAMESPACE_URL, NS + name))
def sha(data): return hashlib.sha256(data).hexdigest()
def load(path): return json.loads(path.read_bytes())
def encode(data): return (json.dumps(data, ensure_ascii=True, indent=4) + '\n').encode('utf-8')
def tup(*items): return {'__tuple__': True, 'items': list(items)}
def ex(t, s, *args, **kwargs): return dict(arg_type=t, sub_type=s, args_list=list(args), **kwargs)
def lit(t, value): return ex(t, 1, value)
def text(value): return lit(100003, value)
def integer(value): return lit(100002, value)
def boolean(value): return lit(100001, value)
def ref(kind, name): return ex(*TYPES[kind][:2], tup(kind, name, 'local'))
def foreign(fid, typ, *args, index=0):
    return ex(typ, fid, *args, call_rt_index=index, op_arg=[], op_arg_enable=[])
def ui(p, key): return lit(100070, key)
def path(p, root, name):
    return ex(100070, 'GET_UI_COMP_BY_PATH', p, ui(p, root), text(name) if isinstance(name, str) else name)
def kv(p, key, kind='INTEGER'):
    return ex(TYPES[kind][0], 'GET_' + kind + '_KV', p, text(key))
def has(p, key): return {'condition_type': 'HAS_KV_ANY', 'args_list': [p, text(key)]}
def getcol(kind, index, col):
    return ex({'STRING': 100003, 'INTEGER': 100002, 'FLOAT':100000}[kind], 'GET_' + kind + '_TABLE_VAR_ND',
              lit(100011, TABLE_ID), index, text(col))
def join(a, b):
    return ex(100003, 'STR_JOIN', text(a) if isinstance(a, str) else a,
              text(b) if isinstance(b, str) else b, op_arg=[None]*8, op_arg_enable=[False]*8)
def intstr(value): return ex(100003, 'INT_TO_STR', value, op_arg=[integer(0)], op_arg_enable=[False])
def getslot(p): return ex(100002, 'GET_PLAYER_SAVE_DATA_INT_VALUE', p, lit(100230, SLOT))


class Nodes:
    def __init__(self, number): self.serial = number * 1000000
    def node(self, field, typ, *args, **kw):
        self.serial += 1
        out = dict(args_list=copy.deepcopy(list(args)), element_id=self.serial, enable=True, **kw)
        out[field] = typ
        if field == 'action_type': out['bp'] = False
        return out
    def act(self, typ, *args, **kw): return self.node('action_type', typ, *args, **kw)
    def cond(self, typ, *args): return self.node('condition_type', typ, *args)
    def cmp(self, a, op, b, typ='FLOAT_COMPARE'):
        return self.cond(typ, a, lit(100015 if typ == 'FLOAT_COMPARE' else 100035, op), b)
    def branch(self, conds, yes, no=()):
        return self.act('IF_THEN_ELSE', ex(100021, 1, *conds), ex(100022, 1, *yes), ex(100022, 1, *no))
    def exists(self, obj): return self.cond('TYPE_IS_EXIST', obj)
    def set(self, var, value): return self.act('SET_VARIABLE', ex(100030, 1, *var['args_list']), value)
    def put(self, p, key, value): return self.act('SET_ENTITY_KV', p, text(key), value)
    def vis(self, p, key, value):
        return self.act('SET_UI_COMP_VISIBLE', p, boolean(value) if isinstance(value, bool) else value,
                        ui(p, key) if isinstance(key, str) else key)
    def label(self, p, key, value):
        return self.act('SET_UI_COMP_TEXT', p, ui(p, key), text(value) if isinstance(value, str) else value)
    def call(self, name, *args):
        return self.act('CALL_TRIGGER_FUNC', ex(100177, FIDS.get(name, name), *args,
                        op_arg=[], op_arg_enable=[]), call_rt_arg_idxes=[])
    def notify(self, p, value):
        return self.act('CALL_TRIGGER_FUNC', ex(100177, 'c38cdfb8fb6011efbbdf456182e68a34',
                        p, text('green'), text(value), op_arg=[None], op_arg_enable=[False]), call_rt_arg_idxes=[])
    def event(self, p, comp, name):
        return self.act('TRIGGER_UI_EVENT', p, ui(p, comp), text(name),
                        op_arg=[boolean(False)], op_arg_enable=[False])


def declare(doc, kind, name):
    doc['var_data'][0].setdefault(kind, {})[name] = TYPES[kind][2]
    doc['var_data'][1][name] = 0
    doc['var_data'][2].append(name)
    return ref(kind, name)


def function(template, name, number, params, comment, returns=None):
    d = {k: copy.deepcopy(template[k]) for k in ['func_category', 'group_id']}
    d.update(action=[], condition=[], event=[], var_data=[{}, {}, []], enabled=True, call_enabled=True,
             func_id=FIDS[name], func_name=name, trigger_name=name, trigger_id=number,
             is_func=True, is_official_func=False, p_trigger_id=None, valid=True,
             func_comment=comment, func_param_list=[tup(n, True) for k, n in params],
             func_des=name + '：' + '，'.join(n+'{'+n+'}' for k, n in params))
    for kind, param in params: declare(d, kind, param)
    if returns:
        d['func_return'] = True
        d['func_rtv_name_list'] = [tup('返回值', returns)]
    return d


def walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values(): yield from walk(v)
    elif isinstance(node, list):
        for v in node: yield from walk(v)


def place(node, x, y, w, h, pw=1920, ph=1080):
    node.update(pos_data=tup(x, y, x/pw*100, y/ph*100, 0, 0), size=tup(w, h),
                anchor=tup(.5, .5), open_adapter=False, adapter_option=[False]*4+[0.0]*4)
    return node


def node(name, typ, key, x, y, w, h, **kw):
    return place(dict(name=name, type=typ, uid=uid(key), children=[], event_list=[],
                      prefab_sub_key=None, scene_ui_name=None, swallow_touches=False, **kw), x,y,w,h)


def label(name, key, value, x, y, w, h, size=24, color=(38,44,34,255)):
    return node(name, 3, key, x,y,w,h, font=tup('HKSongW9',size),
                font_color=tup(*color), alignment=tup(2,8), text=tup(value,False))


def image(name, key, texture, x,y,w,h, cap=(0,0,0,0), **kw):
    return node(name,4,key,x,y,w,h,image=texture,cap_insets=tup(*cap),
                is_scale9_enable=any(cap), **kw)


def event(name):
    return dict(action_list=[], enabled=True, name=name, type=30,
                not_wait_network=False, sound_id=None)


def button(name,key,value,x,y,w,h,normal,disabled,cap,color,size=24,evt=None):
    out=node(name,1,key,x,y,w,h)
    out.update(font=tup('HKSongW9',size), touch_scale=tup(.98,.98), swallow_touches=True,
               pressed_status_added=True, suspend_status_added=True, disabled_status_added=True)
    for state, tint in [('normal',(255,255,255,255)),('suspend',(255,249,229,255)),
                        ('press',(205,205,205,255)),('disabled',(160,160,160,255))]:
        out[state+'_picture']=disabled if state=='disabled' else normal
        out[state+'_cap_insets']=tup(*cap)
        out[state+'_color']=tup(*tint)
        out[state+'_font_color']=tup(*(color if state!='disabled' else (142,142,142,255)))
        out[state+'_text']=tup(value,False)
    if evt: out['event_list']=[event(evt)]
    return out


def palette():
    a=[(134239526,134268850,134236635,134277606,134219894),
       (134232491,134231653,134233071,134259262,134274442),
       (134260939,134247293,134223700,134263272,134222067),
       (134218862,134265133,134221179,134227590,134256993),
       (134259391,134221070,134280067,134279629,134269381),
       (134232249,134237694,134273889,134224724,134271555),
       (134241711,134234721,134258243,134270376,134224710),
       (134236422,134266696,134259669,134270376,134249861)]
    return [dict(id=i+1,name=NAMES[i],window=t[0],title=t[1],button=t[2],disabled=t[3],circle=t[4],
                 window_cap=(88,58,88,58) if i<6 else ((64,76,64,52)if i==6 else(70,58,70,58)),
                 title_cap=(86,22,86,22)if i<6 else(65,25,65,25),
                 button_cap=(42,18,42,18)if i<6 else(55,22,55,22),
                 ink=(241,230,204,255)if i in [2,3]else(43,41,32,255),
                 title_ink=(241,230,204,255)if i in[2,3,6,7]else(43,41,32,255),
                 button_ink=(241,230,204,255)if i in[1,2,3,6,7]else(43,41,32,255)) for i,t in enumerate(a)]


def build_table():
    headers=['key','名称','模板路径','开放','默认','文字R','文字G','文字B','菜单顺序']
    rows=[headers,['int','string','string','int','int','float','float','float','int']]
    for s in palette(): rows.append([str(s['id']),s['name'],'皮肤'+str(s['id']),'1',
                                     '1'if s['id']==6 else'0',*map(str,s['ink'][:3]),str(s['id'])])
    return dict(column_width={},table_type=0,tid=TABLE_ID,
                table_data=dict(column_desc={'4':'1=开放；ID不可随排序更改','5':'新档未选时使用，恰好一行=1'},
                                data=rows,key=[0]))


def build_ui(original, gamehud):
    d=copy.deepcopy(original)
    by={n['uid']:n for n in walk(d)if 'uid'in n}
    assert uid('appearance')not in by, 'Already installed: use a targeted maintenance patch'
    # Retain the original root, background, chat/announcement branches and all page identities.
    root=by[SAFE_ROOT]
    appearances=node('风格外观模板',7,'appearance',960,540,1920,1080)
    for s in palette():
        i=s['id']; k='skin/'+str(i); ink=s['ink']; titleink=s['title_ink']; btnink=s['button_ink']
        skin=node('皮肤'+str(i),7,k,960,540,1920,1080,visible=False)
        header=image('顶部条',k+'/header',s['title'],960,1038,1880,76,s['title_cap'])
        header['children']=[label('游戏名',k+'/game','三国斗阵',170,38,280,48,32,titleink)]
        skin['children']=[header,
            image('阵容底板',k+'/party',s['window'],600,360,1040,470,s['window_cap']),
            image('挑战底板',k+'/challenge',s['window'],1490,465,660,680,s['window_cap']),
            image('补给底条',k+'/supply-bg',s['title'],390,70,620,64,s['title_cap'])]
        # A fixed, separate title strip covers kit01's integrated empty title cartouche.
        for role,value,x,y,w in [('party-title','当前出战阵容',600 if i==7 else 300,580,660 if i==7 else 340),
                                 ('challenge-title','当前挑战',1490 if i==7 else 1380,770,440 if i==7 else 300)]:
            bar=image(value,k+'/'+role,s['title'],x,y,w,58,s['title_cap'])
            bar['children']=[label('文字',k+'/'+role+'/text',value,w/2,29,w-60,40,27,titleink)]
            skin['children'].append(bar)
        for j in range(1,6):
            skin['children'].append(image('头像装饰'+str(j),k+'/portrait/'+str(j),s['circle'],
                                           190+(j-1)*204,416,148,148*(104/94 if i==7 else 271/261 if i==8 else 1)))
        skin['children'] += [
            button('阵容入口',k+'/roster-btn','武将阵容',350,211,310,72,s['button'],s['disabled'],s['button_cap'],btnink,28,'安全区新外层_阵容'),
            label('阵容说明',k+'/roster-hint','布阵 · 武将升星 · 兵种养成',795,211,530,38,22,ink),
            button('补给入口',k+'/supply-btn','在线补给',225,70,230,56,s['button'],s['disabled'],s['button_cap'],btnink,23,'安全区新外层_补给'),
            label('补给说明',k+'/supply-hint','在线累计 · 材料补给',485,70,280,38,20,titleink)]
        if i==8:
            # 317x303 fixed-uniform seal, never a nine-slice stretched rectangle.
            skin['children'].append(button('开战入口',k+'/start','开始\n挑战',1490,244,190,190*303/317,
                                          134258582,134258582,(0,0,0,0),btnink,30,'安全区新外层_挑战'))
        else:
            skin['children'].append(button('开战入口',k+'/start','开始挑战',1490,220,500,88,
                                          s['button'],s['disabled'],s['button_cap'],btnink,34,'安全区新外层_挑战'))
        # One shared event handler per action; only the active skin is visible.
        for role,value,x,w,evt in [('back','返回营地',540,150,'安全区新外层_返回'),
                                 ('troop','兵种养成',710,160,'安全区新外层_兵种'),
                                 ('style','界面风格 ▾',1440,230,'安全区风格_展开')]:
            skin['children'].append(button(value,k+'/'+role,value,x,1038,w,52,s['button'],s['disabled'],s['button_cap'],btnink,21,evt))
        settings=button('设置',k+'/settings','设置',1645,1038,135,52,s['button'],s['disabled'],s['button_cap'],btnink,21,'安全区新外层_设置')
        skin['children'].append(settings)
        exitbtn=button('退出',k+'/exit','退出',1795,1038,135,52,s['button'],s['disabled'],s['button_cap'],btnink,21)
        exitbtn['event_list']=copy.deepcopy(by['9d37fe32-7669-4447-9335-bead5e8a79c1']['event_list'])
        for e in exitbtn['event_list']:
            e['name']='安全区新外层_退出'
            for a in e['action_list']: a['comp']=exitbtn['uid']
        skin['children'].append(exitbtn)
        appearances['children'].append(skin)
    # Common live data is above the decorative templates, never copied eight ways.
    summary=node('营地实时内容',7,'summary',960,540,1920,1080,visible=False)
    summary['children']=[label('营地标题','intro/title','营地总览',270,910,380,70,44,(242,233,210,255)),
                          label('营地副题','intro/subtitle','整备队伍，再赴战场',300,845,440,46,25,(242,233,210,255)),
                          label('章节标题','chapter/title','选择章节',1490,680,500,68,42),
                          image('章节预览','chapter/image',134271105,1490,510,530,230),
                          label('章节说明','chapter/hint','进入后选择章节与挑战难度',1490,350,570,44,23),
                          label('阵容统计','party/count','正在读取出战阵容',600,300,900,40,21)]
    for j in range(1,6):
        c=node('英雄'+str(j),7,'hero/'+str(j),190+(j-1)*204,414,120,130,visible=False)
        mask=node('圆形裁切',7,'hero/'+str(j)+'/mask',60,67,108,108,
                  clip_enabled=True,clipping_type=0,mask_image=134271555)
        mask['children']=[image('头像','hero/'+str(j)+'/icon',None,54,54,108,108)]
        c['children']=[mask,label('姓名','hero/'+str(j)+'/name','',60,-30,180,38,25)]
        summary['children'].append(c)
    # A dedicated passive appearance root and common summary are toggled per route.
    root['children'].extend([appearances,summary])
    # Fixed neutral selector overlays, deliberately not themselves dynamically skinned.
    menu=node('界面风格菜单',7,'menu',960,540,1920,1080,visible=False)
    close=button('菜单外部关闭','menu/outside','',960,540,1920,1080,None,None,(0,0,0,0),(0,0,0,0),evt='安全区风格_取消')
    for state in ['normal','suspend','press','disabled']: close[state+'_color']=tup(0,0,0,0)
    menu['children'].append(close)
    panel=image('下拉底板','menu/panel',134232249,1440,667,390,616,(88,58,88,58))
    panel['swallow_touches']=True
    panel['children']=[label('标题','menu/title','界面风格',195,570,330,48,27),
                       label('提示','menu/footer','选择后确认切换',195,39,340,32,20)]
    for j,s in enumerate(palette(),1):
        row=button(str(j),'menu/row/'+str(j),'',195,516-(j-1)*59,340,53,
                   134273889,134224724,(42,18,42,18),(38,44,34,255),23,'安全区风格_选择')
        row['children']=[label('风格名称','menu/name/'+str(j),s['name'],132,27,220,34,23),
                         label('当前标记','menu/current/'+str(j),'✓ 使用中',280,27,100,30,16)]
        row['children'][1]['visible']=False
        panel['children'].append(row)
    menu['children'].append(panel)
    confirm=node('界面风格确认层',7,'confirm',960,540,1920,1080,visible=False)
    dim=button('确认遮罩','confirm/dim','',960,540,1920,1080,134269414,134269414,(0,0,0,0),(0,0,0,0))
    for state in ['normal','suspend','press','disabled']:dim[state+'_color']=tup(255,255,255,90)
    box=image('确认底板','confirm/panel',134239526,960,540,800,440,(88,58,88,58))
    box['swallow_touches']=True
    box['children']=[label('标题','confirm/title','切换界面风格？',400,360,690,60,34),
                     label('切换说明','confirm/change','',400,262,700,56,29),
                     label('范围说明','confirm/hint','仅调整安全区外层界面\n可随时再次切换',400,179,700,74,23),
                     button('取消','confirm/cancel','取消',222,81,256,68,134236635,134277606,(42,18,42,18),(43,41,32,255),27,'安全区风格_取消'),
                     button('确认切换','confirm/apply','确认切换',576,81,270,68,134258243,134270376,(60,30,60,30),(241,230,204,255),27,'安全区风格_确认'),
                     button('关闭','confirm/close','×',742,387,45,45,None,None,(0,0,0,0),(90,69,38,255),30,'安全区风格_取消')]
    confirm['children']=[dim,box]
    settings=copy.deepcopy(next(n for n in walk(gamehud)if n.get('name')=='setting_panel'))
    settings['uid']=uid('settings-panel');settings['name']='营地设置';settings['visible']=False
    place(settings,960,540,900,700)
    root['children'].extend([menu,confirm,settings])
    # Withdraw only the two explicitly deferred entrances, retain their definitions and data.
    by['1d9b244d-2452-49e3-9880-c4f831ae921d']['visible']=False
    by['407a99f4-b253-4e12-b5e0-2fe174b52f84']['visible']=False
    # New header owns outer navigation; retain hidden native tabs as event targets.
    for comp in ['13a75c64-4def-4296-9ad6-b5b6879ed941','6143daa6-d5c5-4728-adef-046b751d98f3',
                 'f1a0dcd1-b813-495c-81f8-13a9fc6bffd9','e8969f05-d6ce-4c7e-9c29-68b91ecbc2e1']:
        by[comp]['visible']=False
    def normalize(parent):
        pw,ph=parent.get('size',tup(1920,1080))['items']
        for child in parent.get('children',[]):
            if child['uid']not in by:
                if 'pos_data'in child:
                    pos=child['pos_data']['items'];pos[2]=pos[0]/pw*100;pos[3]=pos[1]/ph*100
                for e in child.get('event_list',[]):
                    if e['name'].startswith(('安全区新外层_','安全区风格_')):
                        e['name']+='__'+child['uid'][:8]
                normalize(child)
    normalize(root)
    return d


def valid(n, skin):
    return [n.cmp(skin,'>=',integer(1)),n.cmp(skin,'<=',integer(8))]


def build_functions(template):
    docs={}
    def start(name,number,params,comment,returns=None):
        d=function(template,name,number,params,comment,returns); docs[name]=d; return d,Nodes(number)
    p=ref('PLAYER','执行玩家');skin=ref('INTEGER','风格编号')
    d,n=start(FUNCTION_NAMES[0],TID+1,[('PLAYER','执行玩家'),('INTEGER','风格编号')],
              '仅切换安全区实例的预设外观；模板校验成功后更新当前ID，不修改业务启用状态及玩家存档。','BOOLEAN')
    ok=declare(d,'BOOLEAN','应用成功');target=declare(d,'UI_COMP','目标模板')
    body=[n.set(target,path(p,uid('appearance'),getcol('STRING',skin,'模板路径')))]
    switch=[]
    for i in range(1,9):
        switch.append(n.branch([n.cmp(skin,'==',integer(i))],[n.vis(p,uid('skin/'+str(i)),True)],
                               [n.vis(p,uid('skin/'+str(i)),False)]))
        switch.append(n.branch([n.cmp(skin,'==',integer(i))],[n.vis(p,uid('menu/current/'+str(i)),True)],
                               [n.vis(p,uid('menu/current/'+str(i)),False)]))
        switch.append(n.label(p,uid('menu/name/'+str(i)),getcol('STRING',integer(i),'名称')))
        switch.append(n.branch([n.cmp(getcol('INTEGER',integer(i),'开放'),'==',integer(1))],[
            n.act('SET_UI_COMP_ENABLE',p,ui(p,uid('menu/row/'+str(i))),boolean(True))],[
            n.act('SET_UI_COMP_ENABLE',p,ui(p,uid('menu/row/'+str(i))),boolean(False))]))
    for key in ['chapter/title','chapter/hint','party/count']+['hero/'+str(i)+'/name'for i in range(1,6)]:
        switch.append(n.act('SET_UI_COMP_FONT_COLOR_NORM',p,ui(p,uid(key)),
                             *[getcol('FLOAT',skin,'文字'+c)for c in 'RGB'],lit(100000,100.0)))
    switch += [n.put(p,CURRENT,skin),n.set(ok,boolean(True))]
    body.append(n.branch([n.exists(target)],switch))
    d['action']=[n.set(ok,boolean(False)),n.branch(valid(n,skin),[
        n.branch([n.cmp(getcol('INTEGER',skin,'开放'),'==',integer(1))],body)]),n.act(400342,ok)]

    d,n=start(FUNCTION_NAMES[1],TID+2,[('PLAYER','执行玩家')],
              '摘要只读玩家16槽阵型与单位类型；最多展示前五位，其余保持真实上阵上限及完整阵容页。')
    count=declare(d,'INTEGER','上阵数量');unit=declare(d,'UNIT_NAME','队长类型');pos=declare(d,'INTEGER','阵位')
    idx=ex(100002,'ITER_TABLE_KEY_INT')
    save=ex(100011,'GET_PLAYER_SAVE_DATA_TABLE_VALUE',p,lit(100247,16))
    def savecol(sub,typ,col):return ex(typ,sub,p,lit(100247,16),idx,op_arg=[text(col),None],op_arg_enable=[True,False])
    body=[n.set(count,integer(0))]+[n.vis(p,uid('hero/'+str(i)),False)for i in range(1,6)]
    row=[n.set(pos,savecol('GET_PLAYER_SAVE_TABLE_VALUE_INTEGER',100002,'上阵9宫格')),
         n.branch([n.cmp(pos,'>',integer(0)),n.cmp(pos,'<=',integer(9))],[
          n.set(unit,savecol('GET_PLAYER_SAVE_TABLE_VALUE_UNIT_NAME',100116,'单位类型')),
          n.branch([n.cmp(unit,'!=',ex(100116,'NONE_UNIT_KEY'),'ANY_COMPARE')],[
           n.set(count,ex(100002,'MATH_OPERATION',count,lit(100016,'+'),integer(1))),
           *[n.branch([n.cmp(count,'==',integer(i))],[
              n.act('SET_UI_COMP_IMAGE_NEW',p,ui(p,uid('hero/'+str(i)+'/icon')),ex(100115,'GET_ICON_BY_UNIT_TYPE',unit)),
              n.label(p,uid('hero/'+str(i)+'/name'),ex(100003,'GET_UNIT_NAME_BY_TYPE',unit)),
              n.vis(p,uid('hero/'+str(i)),True)])for i in range(1,6)]])])]
    body += [n.act('TRAVERSE_TABLE_NEW',save,ex(100022,1,*row),op_arg=[boolean(True)],op_arg_enable=[True]),
             n.label(p,uid('party/count'),join(join('已上阵 ',intstr(count)),' 位 · 查看完整阵容')),
             n.branch([n.cmp(count,'==',integer(0))],[n.label(p,uid('party/count'),'尚未配置出战阵容，请先进入武将阵容')])]
    d['action']=body

    d,n=start(FUNCTION_NAMES[2],TID+3,[('PLAYER','执行玩家'),('INTEGER','页面编号')],
              '0营地、1原选关、2原阵容、3原兵种；既有页面UID、选关占位及数据调用保持。')
    page=ref('INTEGER','页面编号')
    cleanup=[n.vis(p,uid('menu'),False),n.vis(p,uid('confirm'),False),n.put(p,PENDING,integer(0))]
    landing=[n.vis(p,OLD_PAGES,False),n.vis(p,uid('summary'),True),n.call(FUNCTION_NAMES[1],p)]
    for i in range(1,9): landing += [n.vis(p,uid('skin/'+str(i)+'/party'),True),n.vis(p,uid('skin/'+str(i)+'/challenge'),True),
        n.vis(p,uid('skin/'+str(i)+'/supply-bg'),True),n.vis(p,uid('skin/'+str(i)+'/party-title'),True),
        n.vis(p,uid('skin/'+str(i)+'/challenge-title'),True),n.vis(p,uid('skin/'+str(i)+'/roster-btn'),True),
        n.vis(p,uid('skin/'+str(i)+'/roster-hint'),True),n.vis(p,uid('skin/'+str(i)+'/supply-btn'),True),
        n.vis(p,uid('skin/'+str(i)+'/supply-hint'),True),n.vis(p,uid('skin/'+str(i)+'/start'),True),
        *[n.vis(p,uid('skin/'+str(i)+'/portrait/'+str(j)),True)for j in range(1,6)]]
    feature=[n.vis(p,uid('summary'),False),n.vis(p,OLD_PAGES,True)]
    for i in range(1,9):
        for key in ['party','challenge','supply-bg','party-title','challenge-title','roster-btn','roster-hint','supply-btn','supply-hint','start']+['portrait/'+str(j)for j in range(1,6)]:
            feature.append(n.vis(p,uid('skin/'+str(i)+'/'+key),False))
    # Old pages are navigated by the new common header. Their business handlers remain.
    for i,comp in enumerate(PAGE_IDS,1):
        feature.append(n.branch([n.cmp(page,'==',integer(i))],[n.vis(p,comp,True)],[n.vis(p,comp,False)]))
    for comp in ['9d22b89c-3942-4968-9a15-e83b8abeae91','41f3c388-7aa1-4699-b6c2-53444a2a8d8b']:
        feature.append(n.vis(p,comp,False))
    feature += [n.branch([n.cmp(page,'==',integer(1))],[n.event(p,'13a75c64-4def-4296-9ad6-b5b6879ed941','切页1按钮_0')]),
                n.branch([n.cmp(page,'==',integer(2))],[n.event(p,'6143daa6-d5c5-4728-adef-046b751d98f3','切页3按钮_0')]),
                n.branch([n.cmp(page,'==',integer(3))],[
                    *[n.vis(p,c,False)for c in ['09e7cd36-0bf4-4170-b163-d2d279b5c9d3',
                      'f49b43b5-64fa-4da0-8ac0-7a120cd32f5f','61d1f417-d163-4b2a-ae99-d7875ec6c562']],
                    n.vis(p,TROOP_PAGE,True),n.event(p,'2eb04a77-b368-42ee-8e66-95ef279afb5a','副切页兵种养成按钮')])]
    d['action']=cleanup+[n.branch([n.cmp(page,'==',integer(0))],landing,feature)]

    d,n=start(FUNCTION_NAMES[3],TID+4,[('PLAYER','执行玩家')],
              '安全区原初始化末尾调用；旧档0值按目录默认项回退，不自动写档。初始化不改聊天占位和测试工具。')
    chosen=declare(d,'INTEGER','当前选择')
    body=[n.set(chosen,getslot(p)),n.put(p,PENDING,integer(0)),n.put(p,BUSY,boolean(False))]
    # Invalid/missing/disabled saved choices fall back to the configured default.
    good=declare(d,'BOOLEAN','选择合法')
    body += [n.set(good,boolean(False)),n.branch(valid(n,chosen),[
        n.branch([n.cmp(getcol('INTEGER',chosen,'开放'),'==',integer(1))],[n.set(good,boolean(True))])]),
        n.branch([n.cmp(good,'==',boolean(False),'BOOL_COMPARE')],[
            n.set(chosen,integer(0)),*[n.branch([n.cmp(getcol('INTEGER',integer(i),'默认'),'==',integer(1)),
                n.cmp(getcol('INTEGER',integer(i),'开放'),'==',integer(1))],[n.set(chosen,integer(i))])for i in range(1,9)]])]
    applied=declare(d,'BOOLEAN','已应用')
    body += [n.set(applied,foreign(FIDS[FUNCTION_NAMES[0]],100001,p,chosen)),
             n.branch([n.cmp(applied,'==',boolean(True),'BOOL_COMPARE')],[
                 n.put(p,READY,boolean(True)),n.call(FUNCTION_NAMES[2],p,integer(0))])]
    d['action']=[n.branch([n.cmp(ex(900002,'GET_CURRENT_LEVEL'),'==',lit(900002,'f8f41509-b607-11ef-a1a4-1132d41864c6'),'ANY_COMPARE')],body)]

    d,n=start(FUNCTION_NAMES[4],TID+5,[('PLAYER','执行玩家'),('INTEGER','操作'),('INTEGER','风格编号')],
              '0取消；1展开；2候选；3确认。候选不换肤不写档；确认仅应用成功后写19槽并请求上传。')
    op=ref('INTEGER','操作');selected=declare(d,'INTEGER','候选编号');applied=declare(d,'BOOLEAN','切换成功')
    previous=declare(d,'INTEGER','上次风格')
    cancel=[n.vis(p,uid('menu'),False),n.vis(p,uid('confirm'),False),n.put(p,PENDING,integer(0))]
    openmenu=[n.put(p,PENDING,integer(0)),n.vis(p,uid('confirm'),False),
              n.branch([n.cmp(ex(100001,'GET_UI_COMP_VISIBLE',p,ui(p,uid('menu'))),'==',boolean(True),'BOOL_COMPARE')],
                       [n.vis(p,uid('menu'),False)],[n.vis(p,uid('menu'),True)])]
    choose=[n.branch(valid(n,skin),[n.branch([n.cmp(getcol('INTEGER',skin,'开放'),'==',integer(1))],[
        n.vis(p,uid('menu'),False),n.branch([n.cmp(skin,'!=',kv(p,CURRENT))],[n.put(p,PENDING,skin),
        n.label(p,uid('confirm/change'),join(join(getcol('STRING',kv(p,CURRENT),'名称'),' → '),getcol('STRING',skin,'名称'))),
        n.vis(p,uid('confirm'),True)],cancel)])])]
    confirms=[n.set(selected,kv(p,PENDING)),n.set(previous,kv(p,CURRENT)),n.branch(valid(n,selected),[
        n.branch([n.cmp(selected,'!=',kv(p,CURRENT)),n.cmp(getcol('INTEGER',selected,'开放'),'==',integer(1))],[
            n.set(applied,foreign(FIDS[FUNCTION_NAMES[0]],100001,p,selected)),
            n.branch([n.cmp(applied,'==',boolean(True),'BOOL_COMPARE')],[
                n.act('SET_SAVE_DATA',p,lit(100230,SLOT),selected),
                n.branch([n.cmp(getslot(p),'==',selected)],[
                    n.act('UPLOAD_SAVE_DATA',p,op_arg=[boolean(True)],op_arg_enable=[False])],
                    [n.call(FUNCTION_NAMES[0],p,previous),n.notify(p,'偏好写入失败，已保留原风格，请重试')]),*cancel],
                [n.notify(p,'外观模板尚未准备好，请保留当前风格并重试')])])])]
    operations=[n.branch([n.cmp(op,'==',integer(0))],cancel),n.branch([n.cmp(op,'==',integer(1))],openmenu),
                n.branch([n.cmp(op,'==',integer(2))],choose),n.branch([n.cmp(op,'==',integer(3))],confirms)]
    # This marker is always initialized before READY. Guard synchronous re-entry.
    d['action']=[n.branch([n.cond('HAS_KV_ANY',p,text(READY))],[
        n.branch([n.cmp(kv(p,READY,'BOOLEAN'),'==',boolean(True),'BOOL_COMPARE')],[
         n.branch([n.cmp(kv(p,BUSY,'BOOLEAN'),'==',boolean(False),'BOOL_COMPARE')],[
            n.put(p,BUSY,boolean(True)),*operations,n.put(p,BUSY,boolean(False))])])])]
    # Reused branch fragments must not duplicate editor element identities.
    for doc in docs.values():
        serial=doc['trigger_id']*1000000
        for part in walk(doc):
            if 'element_id'in part:
                serial+=1;part['element_id']=serial
    return {FN_DIR+name+'.json':d for name,d in docs.items()}


def build_trigger(initializer,ui_doc):
    d={k:copy.deepcopy(initializer[k])for k in ['group_id']}
    d.update(action=[],condition=[],enabled=True,call_enabled=True,valid=True,p_trigger_id=None,
             trigger_id=TID,trigger_name='安全区界面风格交互',var_data=[{},{},[]],sub_trigger={})
    n=Nodes(TID);p=ex(100025,'TRIGGER_PLAYER')
    d['event']=[n.node('event_type','INIT_FINISHED')]
    reg=ex(100001,'VARIABLE',tup('BOOLEAN',REGISTERED))
    def sub(offset,name,actions,eventname=None,keyboard=False):
        number=TID+100+offset;nn=Nodes(number)
        if keyboard:events=[nn.node('event_type','KEYBOARD_KEY_UP_EVENT',lit(200220,1))]
        else:
            matches=[e['name']for c in walk(ui_doc)if'uid'in c for e in c.get('event_list',[])if e['name'].startswith(eventname+'__')]
            assert matches and len(matches)==len(set(matches)),eventname
            events=[nn.node('event_type','TRIGGER_COMPONENT_EVENT',lit(100067,e))for e in matches]
        s=dict(action=actions(nn),condition=[nn.cmp(ex(900002,'GET_CURRENT_LEVEL'),'==',lit(900002,'f8f41509-b607-11ef-a1a4-1132d41864c6'),'ANY_COMPARE')],
               enabled=False,call_enabled=True,valid=True,is_conf=True,p_trigger_id=TID,
               trigger_id=number,trigger_name=name,group_id=0,var_data=[{},{},[]],event=events)
        d['sub_trigger'][str(number)]=s
        return number
    def choice(nn):return [nn.call(FUNCTION_NAMES[4],p,integer(2),ex(100002,'STR_TO_INT',ex(100003,'GET_UI_COMP_NAME',p,ex(100070,'GET_UI_COMP_FROM_EVENT'))))]
    registered=[sub(1,'展开风格菜单',lambda nn:[nn.call(FUNCTION_NAMES[4],p,integer(1),integer(0))],'安全区风格_展开'),
                sub(2,'选择风格候选',choice,'安全区风格_选择'),
                sub(3,'确认切换风格',lambda nn:[nn.call(FUNCTION_NAMES[4],p,integer(3),integer(0))],'安全区风格_确认'),
                sub(4,'取消风格切换',lambda nn:[nn.call(FUNCTION_NAMES[4],p,integer(0),integer(0))],'安全区风格_取消'),
                sub(5,'Esc关闭风格选择',lambda nn:[nn.branch([nn.cond('HAS_KV_ANY',p,text(READY))],[nn.call(FUNCTION_NAMES[4],p,integer(0),integer(0))])],keyboard=True)]
    for offset,name,route in [(6,'返回',0),(7,'挑战',1),(8,'阵容',2),(9,'兵种',3)]:
        registered.append(sub(offset,'安全区导航-'+name,lambda nn,route=route:[nn.call(FUNCTION_NAMES[2],p,integer(route))],'安全区新外层_'+name))
    registered.append(sub(10,'打开原在线补给确认',lambda nn:[nn.call(FUNCTION_NAMES[4],p,integer(0),integer(0)),
        nn.event(p,'157a4bb1-a1be-4ee1-950c-64c9370ba956','挂机模式按钮_0')],'安全区新外层_补给'))
    registered.append(sub(11,'打开营地原生设置',lambda nn:[nn.call(FUNCTION_NAMES[4],p,integer(0),integer(0)),
        nn.vis(p,uid('settings-panel'),True)],'安全区新外层_设置'))
    d['action']=[n.branch([n.cmp(reg,'==',boolean(False),'BOOL_COMPARE')],[n.set(reg,boolean(True)),*registered])]
    return d


def build(source):
    read=lambda name:load(source/name)
    old=read(OLD); ui_old=read(UI)
    template=read(FN_DIR+'刷新主HUD英雄列表与详情.json')
    out=build_functions(template)
    out[UI]=build_ui(ui_old,read(MAP+'ui/GameHUD.json'));out[TRIGGER]=build_trigger(old,out[UI])
    old['action'].append(Nodes(TID+6).call(FUNCTION_NAMES[3],ex(100025,'GET_CLIENT_ROLE')))
    out[OLD]=old
    for key,names in [(FI,[n+'.json'for n in FUNCTION_NAMES]),(TI,['安全区界面风格交互.json'])]:
        d=read(key)
        for name in names:
            assert name not in d
            d[name]=max(d.values(),default=-1)+1
        out[key]=d
    out[TABLE]=build_table()
    groups=read(TABLE_GROUP);group=next(g for g in groups if g.get('name')=='new')
    group['group'].append(tup(TABLE_ID,'安全区界面风格配置表'));out[TABLE_GROUP]=groups
    for key in ['archive/archive.json',MAP+'archive.json']:
        d=read(key);assert str(SLOT)not in d['archive_slots']
        slot=copy.deepcopy(d['archive_slots']['10'])
        slot.update(key=SLOT,name='playerUiSkin',desc='安全区界面风格ID；0=尚未选择，按皮肤目录默认项；1至8为稳定ID',value=0)
        d['archive_slots'][str(SLOT)]=slot;out[key]=d
    variables=read(GLOBAL_VARS)
    assert REGISTERED not in variables['variable_dict']['BOOLEAN']
    variables['variable_dict']['BOOLEAN'][REGISTERED]=False
    variables['variable_length_dict'][REGISTERED]=0
    variables['variable_group_info'].append(tup(REGISTERED,'安全区换肤交互监听注册去重'))
    out[GLOBAL_VARS]=variables
    return out


INPUTS=[UI,OLD,FI,TI,TABLE_GROUP,GLOBAL_VARS,'archive/archive.json',MAP+'archive.json',
        FN_DIR+'刷新主HUD英雄列表与详情.json',MAP+'ui/GameHUD.json']


def stage(refresh=False):
    """Retired after closeout; never publish a historical stage again."""
    retired_publish()


def publish():
    """Retired after closeout; never publish a historical stage again."""
    retired_publish()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['stage','refresh','publish']);a=p.parse_args()
    stage(a.mode=='refresh')if a.mode!='publish'else publish()
