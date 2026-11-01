"""Strict bounded ECA execution checks; not native UI/rendering acceptance."""
import argparse,copy,gzip,json,sys,unittest
from dataclasses import dataclass,field
from pathlib import Path
import y3_main_hud_hero_layout as h

FROZEN=(h.ROOT/'tests/fixtures/y3-main-hud-heroes/source.json.gz').read_bytes()
assert h.sha(FROZEN)=='fba88bb6a35546325e53c875e5894bde3e3ef0f45616c6abc249e8df749e596b','Frozen source changed; inspect provenance before accepting new input'
SOURCE=json.loads(gzip.decompress(FROZEN))
PUBLISHED_BYTES=(h.ROOT/'tests/fixtures/y3-main-hud-heroes/published-v1.json.gz').read_bytes()
assert h.sha(PUBLISHED_BYTES)=='7aa3b8abbfd7b8f8ae2357f2d63db523d59aa2b0ac5b3e04faf2c255b90687cb','Published failure sample changed'
PUBLISHED=json.loads(gzip.decompress(PUBLISHED_BYTES))
OUT,CHANGES=h.build(SOURCE['inputs'],SOURCE['template'])
ACCEPTED_BYTES=(h.ROOT/'tests/fixtures/y3-main-hud-heroes/accepted-hud.json.gz').read_bytes()
assert h.sha(ACCEPTED_BYTES)=='1311df80abe004f77d04f52c9ed1a34dcdc27dd02baebbab9b01a525fd95b79f','Accepted sample changed; inspect provenance first'
OUT.update(json.loads(gzip.decompress(ACCEPTED_BYTES)))
_parser=argparse.ArgumentParser(add_help=False);_parser.add_argument('--candidate-dir')
_options,_remaining=_parser.parse_known_args();sys.argv=[sys.argv[0],*_remaining]
if _options.candidate_dir:
    for _rel in [h.FN1,h.TRIG,h.HUD,h.U1]:
        _path=Path(_options.candidate_dir)/_rel
        if _rel==h.U1 and not _path.is_file():continue
        OUT[_rel]=h.load(_path)
FUNCTIONS={d['func_id']:d for d in OUT.values()if isinstance(d,dict)and d.get('is_func')}

@dataclass(eq=False)
class Obj:
    name:str
    kv:dict=field(default_factory=dict)
    valid:bool=True
    owner:object=None
    tags:set=field(default_factory=set)
    attrs:dict=field(default_factory=lambda:dict(attack_phy=100,defense_phy=20,attack_speed=110,ori_speed=300,hp_max=1000))
    skills:dict=field(default_factory=dict)
    items:dict=field(default_factory=dict)
    icon:int=1
    hp:int=800

class Break(Exception):pass
class World:
    def __init__(self,count=5):
        self.p=Obj('p1');self.p2=Obj('p2');self.tables={self.p:{},self.p2:{}};self.groups={self.p:set(),self.p2:set()};self.cards={self.p:{},self.p2:{}}
        self.ui={};self.parent={};self.calls=[];self.event=None;self.listeners={}
        self.world_selection={self.p:set(),self.p2:set()};self.camera={self.p:None,self.p2:None}
        self.phase=1
        def nodes(n,p=None):
            if 'uid'in n:
                self.ui[n['uid']]={'name':n.get('name'), 'visible':n.get('visible',True),'source':copy.deepcopy(n),'state':{}}
                self.parent[n['uid']]=p;p=n['uid']
            for c in n.get('children',[]):nodes(c,p)
        nodes(OUT[h.HUD]);self.units=[]
        for i in range(1,count+1):self.add(i)
        self.initialize()
    def initialize(self,doc=None):
        self.listeners.clear();doc=doc or OUT[h.TRIG]
        # Model the project's existing 1866239406 startup event. Definitions
        # alone don't register a child trigger; run its native root closures.
        if any(e['event_type']=='RECEIVE_CUSTOM_EVENT'and e['args_list'][0]['args_list']==[1866239406]for e in doc['event']):VM(self).run(doc,[])
    def add(self,i,row=None,pane=None,owner=None):
        p=owner or self.p;u=Obj('hero'+str(i),owner=p,kv={'自动施法':True},icon=100+i)
        u.skills={j:Obj(f'{u.name}-skill{j}')for j in range(1,4)};u.items={j:Obj(f'{u.name}-item{j}')for j in range(1,3)}
        self.groups[p].add(u);self.units.append(u)
        key=row if row is not None else len(self.tables[p])+1
        panel=self.path(h.PANEL,'局内单位信息_'+str(pane or i))
        self.tables[p][key]={'单位':u,'人物界面控件':panel,'归属玩家':p}
        self.cards[p][key]={'归属单位':u,'是否上锁':True};return u
    def path(self,root,path):
        if root is None:raise AssertionError('Dereference missing UI root')
        for name in str(path).split('.'):
            matches=[k for k,v in self.ui.items()if self.parent[k]==root and v['name']==name]
            if len(matches)!=1:raise AssertionError(('Unknown/ambiguous UI path',root,path))
            root=matches[0]
        return root
    def refresh(self,request=None,force=False,p=None):return VM(self).run(OUT[h.FN1],[p or self.p,request,force])
    def visible_panes(self):return [k for k,v in self.ui.items()if self.parent[k]==h.PANEL and v['visible']]
    def roster(self,i,path=None):
        c=self.path(h.ROSTER,str(i));return self.path(c,path)if path else c
    def emit(self,name,comp,p=None):
        # Dispatch only an event actually declared on this exact component.
        # This is still not native hit testing or native event generation.
        if comp is not None and not any(e['name']==name and e.get('enabled',True)for e in self.ui[comp]['source'].get('event_list',[])):return False
        self.event=comp
        matches=[s for s in self.listeners.values()if any(e['args_list'][0]['args_list'][0]['args_list']==[name]for e in s['event'])]
        if not matches:return False
        assert len(matches)==1,name
        VM(self,p or self.p).run(matches[0],[])
        return True

class VM:
    def __init__(self,w,trigger_player=None):self.w=w;self.trigger_player=trigger_player;self.vars={};self.key=None;self.each=None;self.ret=None
    def run(self,doc,args):
        self.doc=doc
        for kind,items in doc['var_data'][0].items():
            for name,value in items.items():self.vars[(kind,name)]=[]if doc['var_data'][1][name]==10 else (None if kind=='UI_COMP'and value==''else copy.deepcopy(value))
        for spec,value in zip(doc.get('func_param_list',[]),args):
            name=spec['items'][0];keys=[k for k in self.vars if k[1]==name];assert len(keys)==1;self.vars[keys[0]]=value
        self.actions(doc['action']);return self.ret
    def identity(self,n):
        a=n['args_list'][0];v=a['items']if isinstance(a,dict)else a
        return tuple(v[:2])
    def expr(self,n):
        if not isinstance(n,dict):raise AssertionError(('Non-expression',n))
        t=n['arg_type'];s=n['sub_type'];raw=n.get('args_list',[])
        if s==1:
            assert len(raw)==1 and not isinstance(raw[0],dict),('Malformed literal',n)
            if t==100070:
                assert raw[0]!='','Empty UI resource ID is invalid; use an unassigned native UI local'
                assert raw[0]in self.w.ui,('Unknown UI',raw[0])
            return raw[0]
        if s in [6,11,14,2,4,'VARIABLE'] and raw and (isinstance(raw[0],dict)and '__tuple__'in raw[0]):
            key=self.identity(n)
            if key==('INTEGER','当前游戏进程阶段'):return self.w.phase
            if key==('TABLE','玩家队伍信息-表'):return self.w.tables[self.expr(raw[1])]
            if key==('TABLE','卡牌技能池-表'):return self.w.cards[self.expr(raw[1])]
            if key==('UNIT_GROUP','玩家队伍'):return self.w.groups[self.expr(raw[1])]
            if key not in self.vars:raise AssertionError(('Undeclared variable',key))
            value=self.vars[key]
            return value[self.expr(raw[1])]if len(raw)==2 else value
        if s=='NONE_UNIT':return None
        if s=='ITER_TABLE_KEY_INT':return self.key
        if s=='FOR_EACH_UI_COMP':return self.each
        if s=='TRIGGER_PLAYER':return self.trigger_player
        if s=='GET_UI_COMP_FROM_EVENT':return self.w.event
        if s in [h.FID1,h.FID2]:return VM(self.w,self.trigger_player).run(FUNCTIONS[s],[self.expr(v)for v in raw])
        a=[self.expr(x)for x in raw]
        if s=='9384d061198e11ef967be8c829c05699':return a[0]
        if s=='GET_UI_COMP_BY_PATH':return self.w.path(a[1],a[2])
        if s=='GET_UI_COMP_PARENT':return self.w.parent[a[1]]
        if s=='GET_UI_COMP_NAME':return self.w.ui[a[1]]['name']
        if s=='GET_UI_COMP_VISIBLE':return self.w.ui[a[1]]['visible']
        if s in ['GET_UNIT_ENTITY_TABLE_VAR_ND','GET_UI_COMP_TABLE_VAR_ND']:
            if a[2]not in a[0][a[1]]:raise AssertionError(('Missing table field',a[1:]))
            return a[0][a[1]][a[2]]
        if s in ['GET_UNIT_ENTITY_KV','GET_BOOLEAN_KV']:
            assert a[0]is not None and a[0].valid,'Invalid KV owner'
            assert a[1]in a[0].kv,('Missing KV',a[1])
            return a[0].kv[a[1]]
        if s=='GET_UNIT_NAME':assert a[0].valid;return a[0].name
        if s=='GET_UNIT_KEY_OF_UNIT':assert a[0].valid;return a[0]
        if s=='GET_ICON':assert a[0].valid;return a[0].icon
        if s=='OWNER_PLAYER':assert a[0].valid;return a[0].owner
        if s=='INT_PLUS_ONE':return a[0]+1
        if s in ['INT_TO_STR','ANY_VAR_TO_STR']:return str(a[0])
        if s=='STR_TO_INT':return int(a[0])
        if s=='F2I':return int(a[0])
        if s=='FLOAT_TO_STR_NEW':return str(round(a[0],a[1]))if a[1]else str(round(a[0]))
        if s=='STR_JOIN':
            return ''.join(map(str,a+[self.expr(v)for v,on in zip(n.get('op_arg',[]),n.get('op_arg_enable',[]))if on]))
        if s=='GET_UNIT_ATTR':assert a[0].valid;return a[0].attrs[a[2]]
        if s=='GET_HP_CUR':assert a[0].valid;return a[0].hp
        if s=='UNIT_CUR_EXP':assert a[0].valid;return 10
        if s=='UNIT_CUR_UPGRADE_EXP':assert a[0].valid;return 100
        if s=='UNIT_ABILITY':assert a[0].valid;return a[0].skills.get(a[2])
        if s=='UNIT_SLOT_ITEM':assert a[0].valid;return a[0].items.get(a[2])
        if s=='UNIT_ENTITY_POINT':assert a[0].valid;return ('unit_point',a[0])
        if s=='BOOL_NOT':return not a[0]
        raise AssertionError(('Unsupported expression',s,n))
    def condition(self,n):
        typ=n['condition_type'];a=[self.expr(x)for x in n['args_list']]
        if typ=='TYPE_IS_EXIST':return a[0]is not None and (not isinstance(a[0],Obj)or a[0].valid)
        if typ=='HAS_KV_ANY':return a[1]in a[0].kv
        if typ=='UNIT_IN_GROUP':assert a[0].valid;return a[0]in a[1]
        if typ=='UNIT_HAS_TAG':assert a[0].valid;return a[1]in a[0].tags
        if typ.endswith('_COMPARE'):
            x,op,y=a
            if op=='==':return x==y
            if op=='!=':return x!=y
            if op=='<':return x<y
            if op=='>':return x>y
            if op=='<=':return x<=y
            if op=='>=':return x>=y
            raise AssertionError(op)
        raise AssertionError(typ)
    def actions(self,acts):
        for n in acts:
            if isinstance(n,list):
                raise AssertionError(('Action-block reference is not a child registration node',n))
            if isinstance(n,int):
                sub=self.doc['sub_trigger'][str(n)]
                assert sub['p_trigger_id']==self.doc['trigger_id'] and sub['is_conf']is True
                assert sub['enabled']is False,'Native configured child uses enabled=False; runtime registration is the integer node'
                assert n not in self.w.listeners,'Repeated child registration'
                self.w.listeners[n]=sub;continue
            if not n.get('enable',True):continue
            typ=n['action_type'];raw=n['args_list']
            if typ=='STORAGE_BOX':self.actions(raw[1]['args_list']);continue
            if typ=='IF_THEN_ELSE':
                cs=[self.condition(c)for c in raw[0]['args_list']] # evaluate all, no assumed short circuit
                self.actions(raw[1 if all(cs)else 2]['args_list']);continue
            if typ=='SET_VARIABLE':self.vars[self.identity(raw[0])]=self.expr(raw[1]);continue
            if typ=='SET_VARIABLE_STR_LIST':self.vars[self.identity(raw[0])]=self.expr(raw[1]).split(self.expr(raw[2]));continue
            if typ=='FOR_INT_DO_ACTION_NEW':
                for i in range(self.expr(raw[1]),self.expr(raw[2])+1):
                    self.vars[self.identity(raw[0])]=i
                    try:self.actions(raw[3]['args_list'])
                    except Break:break
                continue
            if typ=='TRAVERSE_TABLE_NEW':
                assert n.get('op_arg_enable')==[True] and self.expr(n['op_arg'][0])is True
                old=self.key
                for key in list(self.expr(raw[0])):
                    self.key=key
                    try:self.actions(raw[1]['args_list'])
                    except Break:break
                self.key=old;continue
            if typ=='ITER_UI_COMP_DO':
                root=self.expr(raw[1]);old=self.each
                for k in [k for k in self.w.ui if self.w.parent[k]==root]:
                    self.each=k
                    try:self.actions(raw[2]['args_list'])
                    except Break:break
                self.each=old;continue
            if typ=='BREAK_LOOP':raise Break()
            if typ==400342:self.ret=self.expr(raw[0]);continue # assigning a return value is not early exit
            if typ=='CALL_TRIGGER_FUNC':
                f=raw[0];fid=f['sub_type'];args=[self.expr(v)for v in f['args_list']]
                if fid in FUNCTIONS:VM(self.w,self.trigger_player).run(FUNCTIONS[fid],args)
                elif fid=='49cfc821b67b11edb8aa00fff84eb1b1':
                    optional=[self.expr(v)if on else None for v,on in zip(f.get('op_arg',[]),f.get('op_arg_enable',[]))]
                    self.w.calls.append(('tooltip',args,optional))
                else:raise AssertionError(('Unknown function',fid))
                continue
            a=[self.expr(x)for x in raw]
            if typ=='PRINT_MESSAGE_ACTION_TO_DIALOG':self.w.calls.append(('diagnostic',a));continue
            if typ=='SET_ENTITY_KV':a[0].kv[a[1]]=a[2];continue
            if typ=='SET_TABLE_VALUE_ND':a[0][a[1]][a[2]]=a[3];continue
            if typ=='SET_UI_COMP_VISIBLE':self.w.ui[a[2]]['visible']=a[1]
            elif typ in ['SET_UI_COMP_TEXT','SET_UI_COMP_IMAGE_NEW','SET_CHECKBOX_SELECTED','SET_UI_COMP_LOADINGBAR_CURRENT_VALUE','SET_UI_COMP_LOADINGBAR_MAX_VALUE']:
                assert a[1]in self.w.ui;self.w.ui[a[1]]['state'][typ]=a[2]
            elif typ=='SET_UI_IMAGE_COLOR_HEX':self.w.ui[a[1]]['state'][typ]=a[2:]
            elif typ=='SELECT_UNIT':
                if a[1]is None:self.w.world_selection[a[0]].clear()
                else:
                    assert a[1].valid;self.w.world_selection[a[0]].add(a[1])
            elif typ=='NEW_CAMERA_LINEAR_MOVE_TIME':
                assert a[1][0]=='unit_point'and a[2]==0.0
                self.w.camera[a[0]]=a[1][1]
            elif typ in ['NEW_CAMERA_SET_FOLLOW_UNIT','NEW_CAMERA_CANCEL_FOLLOW_UNIT','SET_CAMERA_MOUSE_MODE','SET_UI_COMP_ANIM_SCALE']:pass
            else:raise AssertionError(('Unsupported action',typ))
            self.w.calls.append((typ,a))

class TestHUD(unittest.TestCase):
    def test_01_empty(self):
        w=World(0);w.refresh();w.calls.clear();w.refresh()
        self.assertFalse(w.ui[h.SHELL]['visible']);self.assertEqual(w.visible_panes(),[]);self.assertEqual(w.calls,[])
    def test_02_counts_default_and_single_selection(self):
        for count in range(1,11):
            w=World(count);w.refresh()
            self.assertIs(w.p.kv[h.SELECTED],w.units[0]);self.assertEqual(len(w.visible_panes()),1)
            self.assertEqual(sum(w.ui[w.roster(i)]['visible']for i in range(1,11)),count)
            self.assertEqual(sum(w.ui[w.roster(i,'选中框')]['visible']for i in range(1,count+1)),1)
    def test_03_click_each_avatar_all_ten(self):
        w=World(10);w.refresh()
        for i in [10,1,6,5,2,9,3,8,4,7]:
            w.emit(h.eventname(i,'选择'),w.roster(i))
            self.assertIs(w.p.kv[h.SELECTED],w.units[i-1]);self.assertEqual(w.visible_panes(),[w.path(h.PANEL,'局内单位信息_'+str(i))])
    def test_04_selection_survives_refresh_and_new_member(self):
        w=World(4);w.refresh(w.units[2]);w.add(5);w.refresh(force=True)
        self.assertIs(w.p.kv[h.SELECTED],w.units[2]);w.refresh();self.assertEqual(len(w.visible_panes()),1)
    def test_05_removed_selected_falls_back(self):
        w=World();u=w.units[3];w.refresh(u);w.groups[w.p].remove(u);w.refresh()
        self.assertIs(w.p.kv[h.SELECTED],w.units[0]);self.assertFalse(w.ui[w.roster(5)]['visible'])
    def test_06_invalid_and_foreign_requests_ignored(self):
        w=World();w.refresh(w.units[2]);dead=Obj('removed',valid=False)
        for req in [dead,Obj('foreign',owner=w.p2),None]:
            w.refresh(req);self.assertIs(w.p.kv[h.SELECTED],w.units[2])
    def test_07_sparse_rows_and_different_panel_order(self):
        w=World(0);a=w.add(1,row=3,pane=7);b=w.add(2,row=30,pane=2);w.refresh(b)
        self.assertEqual(w.visible_panes(),[w.path(h.PANEL,'局内单位信息_2')])
        self.assertIs(VM(w).run(OUT[h.FN2],[w.p,w.path(h.PANEL,'局内单位信息_7')]),a)
    def test_08_pseudo_dead_is_inspectable_but_auto_hidden(self):
        w=World();u=w.units[1];u.tags.add('已死亡');w.refresh(u)
        self.assertIs(w.p.kv[h.SELECTED],u);self.assertTrue(w.ui[w.roster(2,'阵亡')]['visible'])
        self.assertFalse(w.ui[w.path(w.visible_panes()[0],'自动战斗')]['visible'])
        u.tags.clear();w.refresh();self.assertFalse(w.ui[w.roster(2,'阵亡')]['visible'])
    def test_09_invalid_record_not_dereferenced(self):
        w=World();w.units[0].valid=False;w.refresh();self.assertIs(w.p.kv[h.SELECTED],w.units[1])
    def test_10_no_repeat_avatar_writes_or_event_registration(self):
        w=World(10);w.refresh();w.calls.clear();w.refresh()
        self.assertFalse(any(c[0]in ['SET_UI_COMP_IMAGE_NEW','SET_UI_COMP_VISIBLE','SET_UI_IMAGE_COLOR_HEX']for c in w.calls))
        self.assertEqual(sum(c[0]=='SET_UI_COMP_TEXT'for c in w.calls),5)
        self.assertFalse(any(n.get('action_type')=='CREATE_UI_COMP_EVENT_EX_EX'for n in h.walk(OUT[h.FN1])))
    def test_11_skill_and_equipment_tips_follow_event_panel(self):
        w=World();w.refresh(w.units[3]);pane=w.visible_panes()[0]
        for j in range(1,4):
            w.emit(h.eventname(4,'技能悬停',j),w.path(pane,f'skill.skill_btn_{j}.skill_icon_img'))
            self.assertIs(w.calls[-1][2][0],w.units[3].skills[j])
        for j in range(1,3):
            w.emit(h.eventname(4,'装备悬停',j),w.path(pane,f'equits.equip_slot_{j}.equip_icon_img'))
            self.assertIs(w.calls[-1][2][2],w.units[3].items[j])
    def test_12_missing_slot_does_not_show_stale_tip(self):
        w=World();w.refresh();w.units[0].skills.clear();w.units[0].items.clear();w.calls.clear();pane=w.visible_panes()[0]
        w.emit(h.eventname(1,'技能悬停',1),w.path(pane,'skill.skill_btn_1.skill_icon_img'))
        w.emit(h.eventname(1,'装备悬停',1),w.path(pane,'equits.equip_slot_1.equip_icon_img'))
        self.assertEqual([c[1][1]for c in w.calls if c[0]=='tooltip'],[False,False])
    def test_13_rebound_instances_resolve_new_unit(self):
        w=World();old=w.units[0];w.refresh(old);w.groups[w.p].remove(old);w.tables[w.p].pop(1)
        new=w.add(8,row=41,pane=1);w.refresh(force=True)
        self.assertIs(VM(w).run(OUT[h.FN2],[w.p,w.path(h.PANEL,'局内单位信息_1')]),new)
    def test_14_player_and_group_isolation(self):
        w=World();u=w.add(8,row=9,pane=8,owner=w.p2);w.refresh();w.refresh(p=w.p2)
        self.assertIs(w.p.kv[h.SELECTED],w.units[0]);self.assertIs(w.p2.kv[h.SELECTED],u)
        self.assertIsNone(VM(w).run(OUT[h.FN2],[w.p,w.path(h.PANEL,'局内单位信息_8')]))
    def test_15_native_structure_and_ids(self):
        sys.path.insert(0,'C:/Users/littl/.codex/plugins/cache/y3-local/y3-eca/0.1.0')
        from eca_core import validate_structure
        for rel,d in OUT.items():
            if rel.endswith('.json')and rel!=h.HUD:
                result=validate_structure(d);self.assertTrue(result['structure_valid'],(rel,result))
                if rel!=h.U1:self.assertEqual(result['warning_count'],0,(rel,result))
        roots=[d['trigger_id']for d in OUT.values()if 'trigger_id'in d];self.assertEqual(len(roots),len(set(roots)))
        for rel in [h.FN1,h.FN2,h.TRIG]:
            ids=[n['element_id']for n in h.walk(OUT[rel])if 'element_id'in n];self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(OUT[h.FN2]['func_rtv_name_list'][0]['items'][1],'UNIT_ENTITY')
        self.assertEqual(OUT[h.FN2]['action'][-1]['action_type'],400342)
    def test_16_static_event_bindings_are_unique_and_resolved(self):
        declared=[e['name']for n in h.walk(OUT[h.HUD])for e in n.get('event_list',[])if e['name'].startswith('主HUD_')]
        listened=[e['args_list'][0]['args_list'][0]['args_list'][0]for s in OUT[h.TRIG]['sub_trigger'].values()for e in s['event']]
        self.assertEqual(len(declared),150);self.assertEqual(len(declared),len(set(declared)));self.assertCountEqual(declared,listened)
        self.assertEqual(len(CHANGES['retired_dynamic_event_nodes']),16)
        for rel in [h.CREATE,h.REBIND]:self.assertFalse(any(n.get('action_type')=='CREATE_UI_COMP_EVENT_EX_EX'for n in h.walk(OUT[rel])))
    def test_17_layout_and_original_identity(self):
        orig=next(n for n in SOURCE['inputs'][h.HUD]['children']if n['uid']==h.PANEL)
        now=next(n for n in h.walk(OUT[h.HUD])if n.get('uid')==h.PANEL)
        self.assertEqual(len(now['children']),10)
        for a,b in zip(orig['children'],now['children']):
            self.assertEqual(a['uid'],b['uid']);self.assertEqual([n['uid']for n in h.walk(a)if 'uid'in n],[n['uid']for n in h.walk(b)if 'uid'in n])
        ids=[n['uid']for n in h.walk(OUT[h.HUD])if 'uid'in n];self.assertEqual(len(ids),len(set(ids)))
        w=World(0);pos=[w.ui[w.roster(i)]['source']['pos_data']['items'][:2]for i in range(1,11)]
        self.assertEqual(len(set(p[1]for p in pos)),2)
        for y in set(p[1]for p in pos):self.assertEqual(sum(p[1]==y for p in pos),5)
    def test_18_gameplay_actions_and_original_handlers_preserved(self):
        gameplay={'UNIT_ADD_ITEM','GROUP_ADD_UNIT','UNIT_REMOVE_ABILITY','UNIT_ADD_ABILITY','SET_TABLE_VALUE_ND','SET_ENTITY_KV','CALL_TRIGGER_FUNC'}
        for rel in [h.CREATE,h.REBIND]:
            before=[n for n in h.walk(SOURCE['inputs'][rel])if n.get('action_type')in gameplay]
            after=[n for n in h.walk(OUT[rel])if n.get('action_type')in gameplay and not(n.get('action_type')=='CALL_TRIGGER_FUNC'and n['args_list'][0]['sub_type']==h.FID1)]
            self.assertEqual(before,after)
            for k in ['func_id','trigger_id','func_param_list']:self.assertEqual(SOURCE['inputs'][rel].get(k),OUT[rel].get(k))
        before=copy.deepcopy(SOURCE['inputs'][h.U1]);after=copy.deepcopy(OUT[h.U1]);before['action'].pop(2);after['action'].pop(2)
        for d in [before,after]:
            for n in h.walk(d):
                if n.get('action_type')=='SET_UI_COMP_VISIBLE'and n.get('element_id')in [v['element_id']for v in CHANGES['phase_visibility_before']]:n.clear()
        self.assertEqual(before,after)
    def test_19_model_rejects_unknown_and_malformed(self):
        vm=VM(World())
        with self.assertRaises(AssertionError):vm.expr(h.ex(100006,'UNKNOWN_UNIT_API'))
        with self.assertRaises(AssertionError):vm.expr(h.lit(100011,h.ex(100011,'VARIABLE')))

    def test_20_auto_toggle_only_event_hero_and_its_cards(self):
        w=World();w.refresh(w.units[3]);pane=w.visible_panes()[0]
        w.emit(h.eventname(4,'自动施法'),w.path(pane,'自动战斗'))
        self.assertEqual([u.kv['自动施法']for u in w.units],[True,True,True,False,True])
        self.assertEqual([r['是否上锁']for r in w.cards[w.p].values()],[True,True,True,False,True])
        w.units[3].tags.add('已死亡');w.emit(h.eventname(4,'自动施法'),w.path(pane,'自动战斗'))
        self.assertFalse(w.units[3].kv['自动施法'])

    def test_21_skill_description_table_switch_preserved(self):
        w=World();u=w.units[0];u.tags.add('仆从伙伴');w.refresh();pane=w.visible_panes()[0]
        w.emit(h.eventname(1,'技能悬停',1),w.path(pane,'skill.skill_btn_1.skill_icon_img'))
        self.assertIs(w.calls[-1][2][8],False)

    def test_22_selection_change_closes_old_tooltip(self):
        w=World();w.refresh();w.calls.clear();w.refresh(w.units[1])
        self.assertEqual([c[1][1]for c in w.calls if c[0]=='tooltip'],[False])

    def test_23_refresh_and_roster_click_do_not_mutate_combat(self):
        w=World(10)
        def snapshot():return [(u.name,dict(u.kv),dict(u.attrs),u.hp,set(u.tags),dict(u.skills),dict(u.items))for u in w.units],{p:{k:dict(v)for k,v in t.items()}for p,t in w.cards.items()},{p:set(g)for p,g in w.groups.items()}
        before=snapshot();w.refresh()
        for i in [7,1,10,4]:w.emit(h.eventname(i,'选择'),w.roster(i));w.refresh()
        self.assertEqual(before,snapshot())

    def test_24_missing_startup_registration_reproduced(self):
        w=World();bad=copy.deepcopy(PUBLISHED[h.TRIG]);self.assertEqual(bad['event'],[]);self.assertEqual(bad['action'],[]);w.initialize(bad);w.refresh()
        self.assertFalse(w.emit(h.eventname(4,'选择'),w.roster(4)))
        self.assertIs(w.p.kv[h.SELECTED],w.units[0])
        w.initialize();self.assertEqual(len(w.listeners),8)
        self.assertTrue(w.emit(h.eventname(4,'选择'),w.roster(4)))
        self.assertIs(w.p.kv[h.SELECTED],w.units[3])

    def test_25_empty_resource_rejected_and_unassigned_ui_local_used(self):
        old=[n for n in h.walk(PUBLISHED[h.FN1])if n.get('arg_type')==100070 and n.get('sub_type')==1 and n.get('args_list')==['']]
        self.assertEqual(len(old),2)
        for node in old:
            with self.assertRaises(AssertionError):VM(World()).expr(node)
        d=OUT[h.FN1];self.assertEqual(d['var_data'][0]['UI_COMP']['空详情引用'],'')
        self.assertFalse(any(n.get('arg_type')==100070 and n.get('sub_type')==1 and n.get('args_list')==['']for n in h.walk(d)))
        w=World(0);w.refresh();self.assertEqual(w.visible_panes(),[])

    def test_26_equipment_row_is_fixed_visible_and_preserves_bindings(self):
        now=next(n for n in h.walk(OUT[h.HUD])if n.get('uid')==h.PANEL)
        old=next(n for n in h.walk(SOURCE['inputs'][h.HUD])if n.get('uid')==h.PANEL)
        for index,pane in enumerate(now['children']):
            eq=h.child(pane,'equits');self.assertTrue(eq['visible']);self.assertFalse(eq['open_adapter'])
            self.assertEqual(eq['size']['items'],[136,60]);self.assertEqual(eq['pos_data']['items'][:2],[125,250])
            for slot in eq['children']:self.assertTrue(slot['visible']);self.assertFalse(slot['open_adapter'])
            if index<9:
                orig=h.child(old['children'][index],'equits')
                self.assertEqual(eq['uid'],orig['uid'])
                for a,b in zip(eq['children'],orig['children']):
                    for key in ['uid','type','equip_icon_img','equip_bg_img','equip_cd_progress','equip_charge_label','equip_stack_label','equip_disabled_img']:self.assertEqual(a[key],b[key])

    def test_27_click_belongs_to_button_and_decorations_do_not_intercept(self):
        w=World(10);w.refresh()
        for i in range(1,11):
            button=w.ui[w.roster(i)]['source'];self.assertEqual(button['type'],1)
            self.assertTrue(button['swallow_touches'])
            self.assertEqual(button['event_list'],[h.event(h.eventname(i,'选择'),30)])
            for decoration in button['children']:self.assertFalse(decoration['swallow_touches'])
            self.assertFalse(w.emit(h.eventname(i,'选择'),w.roster(i,'头像')))
            self.assertTrue(w.emit(h.eventname(i,'选择'),w.roster(i)))
            self.assertIs(w.p.kv[h.SELECTED],w.units[i-1])

    def test_28_missing_cache_does_not_change_selection(self):
        w=World();w.refresh();old=w.p.kv[h.SELECTED];w.p.kv.pop(h.CACHE+'2')
        self.assertTrue(w.emit(h.eventname(2,'选择'),w.roster(2)))
        self.assertIs(w.p.kv[h.SELECTED],old)
        self.assertFalse(any(c[0]=='diagnostic'for c in w.calls))

    def test_29_diagnostics_are_not_in_periodic_refresh(self):
        w=World();w.refresh();w.calls.clear()
        for _ in range(100):w.refresh()
        self.assertFalse(any(c[0]=='diagnostic'for c in w.calls))
        s=OUT[h.TRIG]['sub_trigger'][str(h.TID+3)]
        count=len(w.calls)
        w.event=None;VM(w,w.p).run(s,[])
        self.assertEqual(len(w.calls),count)

    def test_30_action_references_are_not_child_registration(self):
        w=World();bad=copy.deepcopy(OUT[h.TRIG])
        bad['action']=[[s['trigger_id'],s['trigger_name'],h.TID,'action_type']for s in bad['sub_trigger'].values()]
        with self.assertRaisesRegex(AssertionError,'not a child registration'):w.initialize(bad)
        w.initialize();w.refresh()
        self.assertTrue(w.emit(h.eventname(2,'选择'),w.roster(2)))
        self.assertIs(w.p.kv[h.SELECTED],w.units[1])

    def test_31_avatar_replaces_existing_world_selection_and_focuses(self):
        w=World();w.refresh();w.world_selection[w.p]={w.units[0],w.units[2]};w.calls.clear()
        w.emit(h.eventname(2,'选择'),w.roster(2))
        self.assertEqual(w.world_selection[w.p],{w.units[1]});self.assertIs(w.camera[w.p],w.units[1])
        acts=[c for c in w.calls if c[0]in ['SELECT_UNIT','NEW_CAMERA_LINEAR_MOVE_TIME']]
        self.assertEqual([a[0]for a in acts],['SELECT_UNIT','SELECT_UNIT','NEW_CAMERA_LINEAR_MOVE_TIME'])
        self.assertIsNone(acts[0][1][1]);self.assertIs(acts[1][1][1],w.units[1])
        w.calls.clear();w.refresh();self.assertFalse(any(c[0]=='NEW_CAMERA_LINEAR_MOVE_TIME'for c in w.calls))

    def test_32_stale_foreign_cache_does_not_clear_selection_or_focus(self):
        w=World();w.refresh();w.world_selection[w.p]={w.units[0]}
        for cached in [Obj('foreign',owner=w.p2),Obj('removed',valid=False),None]:
            w.p.kv[h.CACHE+'2']=cached;w.calls.clear();w.emit(h.eventname(2,'选择'),w.roster(2))
            self.assertEqual(w.world_selection[w.p],{w.units[0]});self.assertIsNone(w.camera[w.p])
            self.assertFalse(any(c[0]in ['SELECT_UNIT','NEW_CAMERA_LINEAR_MOVE_TIME']for c in w.calls))

    def test_33_focus_uses_only_clicking_player(self):
        w=World();u=w.add(8,row=8,pane=8,owner=w.p2);w.refresh();w.refresh(p=w.p2)
        w.world_selection[w.p]={w.units[0]};w.world_selection[w.p2]={Obj('old')}
        w.emit(h.eventname(1,'选择'),w.roster(1),p=w.p2)
        self.assertEqual(w.world_selection[w.p],{w.units[0]});self.assertIsNone(w.camera[w.p])
        self.assertEqual(w.world_selection[w.p2],{u});self.assertIs(w.camera[w.p2],u)

    def test_34_battle_hides_shell_and_refresh_cannot_reopen_it(self):
        w=World();w.refresh(w.units[1]);self.assertTrue(w.ui[h.SHELL]['visible'])
        w.phase=2
        for _ in range(12):w.refresh(force=True)
        self.assertFalse(w.ui[h.SHELL]['visible']);self.assertIs(w.p.kv[h.SELECTED],w.units[1])
        w.add(6);w.refresh(force=True);self.assertFalse(w.ui[h.SHELL]['visible'])
        w.phase=1;w.refresh();self.assertTrue(w.ui[h.SHELL]['visible'])
        self.assertIs(w.p.kv[h.SELECTED],w.units[1])
        visible={n['element_id']:n for n in h.walk(OUT[h.U1])if n.get('action_type')=='SET_UI_COMP_VISIBLE'}
        self.assertEqual(visible[1252758182990210]['args_list'][1]['args_list'],[True])
        self.assertEqual(visible[1252758182990276]['args_list'][1]['args_list'],[False])

if __name__=='__main__':unittest.main(verbosity=2)
