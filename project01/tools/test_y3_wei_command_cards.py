"""Bounded execution of staged native ECA; not an actual Y3 engine test.

Grant/UI/route-unlock APIs are explicit test doubles. Return-value actions set
the result and continue; no invented early-exit semantics or table coercion.
"""
from __future__ import annotations
import contextlib,copy,json,unittest
import y3_card_test_fixtures as fixtures
import y3_wei_command_cards as s
import test_y3_wu_runtime_tables as v
old=v.old
Unit=old.Unit
FIXTURE=fixtures.load('wei')
DATA=FIXTURE['data']
FUNCS={d['func_id']:d for d in DATA.values() if isinstance(d,dict) and d.get('is_func')}
for name in ('军略3选1-屏蔽上一级主动卡牌','军略3选1-屏蔽已吞噬的卡牌'):
    doc=s.read('global_trigger/function/new/功能执行/'+name+'.json');FUNCS[doc['func_id']]=doc
SPECS={int(k):v for k,v in FIXTURE['specs'].items()}
ROWS=FIXTURE['config']['table_data']['data']
CONFIG={int(x[0]):{key:True if val=='true' else False if val=='false' else val for key,val in zip(ROWS[0],x) if key} for x in ROWS[2:] if x and isinstance(x[1],int)}
ROW_BY_ID={x['技能类型']:k for k,x in CONFIG.items()}
UR=[x['技能类型'] for x in CONFIG.values() if x['子归类']=='八虎骑']
EX=[x['技能类型'] for x in CONFIG.values() if x['所属set']=='EX']

def read(rel):return DATA[rel] if rel in DATA else s.read(rel)

class VM(v.VM):
    def execute(self,fid,args):
        if fid in (s.MERGE,s.UNLOCK,s.SHOW):
            if fid==s.MERGE:
                player,row=args;u=self.w.carriers[player];aid=self.w.configs[player][row]['技能类型']
                self.w.grants.append((player,aid));self.w.card(u,aid,source=2)
                return self.w.handles[u.name,aid]
            self.w.side_effects.append((fid,args));return
        doc=FUNCS[fid];vm=object.__new__(VM)
        vm.w,vm.owner,vm.oid,vm.modifier=self.w,self.owner,doc['trigger_id'],False
        vm.obj=doc;vm.kv={};vm.vars={};vm.contributions={};vm.registered=set();vm.selected=None;vm.params={};vm.handle=None;vm.iter_key=None;vm.result=None
        for values in doc['var_data'][0].values():vm.vars.update(copy.deepcopy(values))
        assert len(args)==len(doc['func_param_list']),(fid,len(args))
        for p,a in zip(doc['func_param_list'],args):vm.vars[p['items'][0]]=a
        self.w.function_calls[fid]=self.w.function_calls.get(fid,0)+1
        vm.run(doc['action']);return vm.result
    def ev(self,node):
        if not isinstance(node,dict):return node
        t=node.get('sub_type');a=node.get('args_list',[])
        if t in FUNCS or t in (s.MERGE,s.UNLOCK,s.SHOW):return self.execute(t,[self.ev(x) for x in a])
        if t=='NONE_ABILITY':return None
        if t=='GET_CLIENT_ROLE':return self.owner.player
        if t=='GET_ABILITY_BY_AID':
            unit,category,aid=[self.ev(x) for x in a]
            return self.w.handles.get((unit.name,aid)) if unit.card_categories.get(aid)==category else None
        if t=='GET_ABILITY_TYPE_CAST_TYPE':return read(f'editor_table/abilityall/{self.ev(a[0])}.json')['ability_cast_type']
        if a and isinstance(a[0],dict) and len(a[0].get('items',[]))==2:
            kind,name=a[0]['items']
            if kind=='INTEGER':return {s.THRESHOLD:self.w.threshold,'当前游戏进程阶段':self.w.phase,'当前进程所在波次编号':self.w.wave}[name]
            if name=='军令卡牌base-表':return self.w.configs[self.ev(a[1])]
            if name=='playerHeroList':return self.w.carriers.get(self.ev(a[1]))
        if t in ('GET_BOOLEAN_KV','GET_INTEGER_KV','GET_FLOAT_KV','GET_STRING_KV'):
            entity,key=[self.ev(x) for x in a]
            default='' if t=='GET_STRING_KV' else False if t=='GET_BOOLEAN_KV' else 0
            assert entity is not None,'Dereferenced absent entity'
            if isinstance(entity,int):return self.w.player_kv.setdefault(entity,{}).get(key,default)
            if isinstance(entity,tuple):return self.w.instance_kv.get((entity[0].name,entity[1],key),read(f'editor_table/abilityall/{entity[1]}.json')['kv'].get(key,{}).get('value',default))
            return entity.kv.get(key,default)
        if t=='RANDOM_INT':
            lo,hi=[int(self.ev(x)) for x in a];value=self.w.random.pop(0) if self.w.random else hi
            assert lo<=value<=hi,(lo,value,hi)
            self.w.random_ranges.append((lo,hi));return value
        if t=='GET_INTEGER_TABLE_VAR_1D':return self.ev(a[0])[self.ev(a[1])]
        if t=='STR_JOIN':
            extra=[x for x,on in zip(node.get('op_arg',[]),node.get('op_arg_enable',[])) if on]
            return ''.join(str(self.ev(x)) for x in a+extra)
        return super().ev(node)
    def cond(self,node):
        if not node.get('enable',True):return True
        if node['condition_type'] in ('ABILITY_COMPARE','ABILITY_CAST_TYPE_COMPARE'):
            x,op,y=[self.ev(n) for n in node['args_list']];return x==y if op=='==' else x!=y
        if node['condition_type']=='TYPE_IS_EXIST':
            arg=node['args_list'][0]
            assert arg.get('arg_type')!=100062,'MAP is not a supported instance type'
        return super().cond(node)
    def run(self,actions):
        for node in actions:
            if isinstance(node,int):super().run([node]);continue
            if not node.get('enable',True):continue
            t=node['action_type'];a=node['args_list']
            if t==400342:self.result=self.ev(a[0])
            elif t=='BREAK_LOOP':raise BreakLoop()
            elif t=='TRAVERSE_TABLE_NEW':
                table=self.ev(a[0]);previous=self.iter_key
                try:
                    for key in list(table):self.iter_key=key;self.run(a[1]['args_list'])
                except BreakLoop:pass
                finally:self.iter_key=previous
            elif t=='SET_ENTITY_KV' and isinstance(self.ev(a[0]),tuple):
                entity,key,value=[self.ev(x) for x in a];self.w.instance_kv[entity[0].name,entity[1],key]=value
            elif t=='SET_ENTITY_KV' and isinstance(self.ev(a[0]),int):
                entity,key,value=[self.ev(x) for x in a];self.w.player_kv.setdefault(entity,{})[key]=value
            elif t=='PRINT_MESSAGE_ACTION_TO_DIALOG':self.w.messages.append(self.ev(a[1]))
            else:super().run([node])

class World(v.World):
    def __init__(self):
        super().__init__();self.carriers={};self.configs={};self.phase=1;self.wave=0;self.threshold=8
        self.player_kv={};self.random=[];self.random_ranges=[];self.grants=[];self.side_effects=[];self.instance_kv={};self.messages=[]
    def card(self,u,aid,add=True,before_lose=False,source=0):
        self.carriers[u.player]=u;self.configs.setdefault(u.player,copy.deepcopy(CONFIG));self.pools.setdefault(u.player,{})
        row=ROW_BY_ID[aid]
        if add:
            self.serial+=1;handle=self.handles.setdefault((u.name,aid),(u,aid,self.serial));u.cards.add(aid)
            u.card_categories[aid]=3 if source==2 else 2
            if f'ability/{aid}.json' in DATA:VM(self,u,aid,False).fire('ABILITY_OBTAIN')
            self.prewrite_snapshots.append(dict(u.kv))
            self.pools[u.player][row]={'技能':handle,'归属单位':u,'技能类型':aid,'是否已抽取':True}
            self.configs[u.player][row]['是否已抽取']=True
        else:
            if before_lose and f'ability/{aid}.json' in DATA:VM(self,u,aid,False).fire('ABILITY_LOSE')
            u.cards.remove(aid);self.handles.pop((u.name,aid),None)
            if not before_lose and f'ability/{aid}.json' in DATA:VM(self,u,aid,False).fire('ABILITY_LOSE')
        vm=VM(self,u,s.BASE,False)
        vm.execute(s.FIDS[14],[u])
        if source:vm.execute(s.FIDS[20],[u,source,aid])
    def tick(self):
        for oid in (s.CONTROL,s.ARMY):
            for vm in list(self.buffs.values()):
                if vm.oid==oid:vm.fire('MODIFIER_CYCLE_TRIGGER')
    def contribution(self,u,key,mode='ATTR_BASE'):
        vm=self.buffs.get((u.name,s.ARMY));return vm.contributions.get((key,mode),0) if vm else 0
    def start(self,n):self.wave=n;self.phase=2;self.emit(s.b.PHASE,阶段编号=2)

class BreakLoop(Exception):pass

@contextlib.contextmanager
def runtime():
    prev=(old.VM,old.read,v.FUNCS,v.read)
    old.VM=VM;old.read=read;v.FUNCS=FUNCS;v.read=read
    try:yield
    finally:old.VM,old.read,v.FUNCS,v.read=prev

def world():
    w=World();c=Unit('carrier');front=Unit('front',tags={'魏国','盾兵'},kv={'归属阵型编号':1})
    rear=Unit('rear',tags={'吴国'},kv={'归属阵型编号':7});bow=Unit('bow',tags={'盾兵','弓兵'},kv={'所属英雄':front})
    soldier=Unit('soldier',tags={'刀兵'},kv={'所属英雄':rear})
    front.kv['带领小队']=[bow];rear.kv['带领小队']=[soldier]
    w.units=[c,front,rear,bow,soldier];w.captains[1]=[front,rear]
    return w,c,front,rear,bow,soldier

class WeiCases(unittest.TestCase):
    def setUp(self):self.ctx=runtime();self.ctx.__enter__()
    def tearDown(self):self.ctx.__exit__(None,None,None)
    def test_source_cardinality_and_placeholder_name_only(self):
        self.assertEqual(len(SPECS),32);self.assertEqual(len(UR),8);self.assertEqual(len(EX),5)
        for aid in s.PLACEHOLDERS:
            rel=f'editor_table/abilityall/{aid}.json';before=FIXTURE['legacy_placeholders'][rel];after=copy.deepcopy(DATA[rel])
            after['name']=before['name'];self.assertEqual(after,before)
            self.assertNotIn(f'ability/{aid}.json',DATA)
    def test_no_invalid_tables_no_stale_fids_unique_ids_and_event_declarations(self):
        tids=[];fids=[]
        for rel,doc in DATA.items():
            if rel.startswith(s.FOLDER) and rel.endswith('.json'):
                fids.append(doc['func_id']);tids.append(doc['trigger_id'])
                self.assertFalse(set(n.get('sub_type') for n in s.b.walk(doc))&set(s.s.FIDS.values()))
                if doc.get('func_return'):self.assertEqual(sum(n.get('action_type')==400342 for n in s.b.walk(doc)),1)
            if rel.startswith(('ability/','modifier/')):
                tids += [t['trigger_id'] for t in doc['trigger_dict'].values()]
                self.assertTrue(all(t.get('p_trigger_id') is None or str(t['p_trigger_id']) in doc['trigger_dict'] for t in doc['trigger_dict'].values()))
            if rel.startswith((s.FOLDER,'ability/','modifier/')):
                ids=[n['element_id'] for n in s.b.walk(doc) if 'element_id' in n];self.assertEqual(len(ids),len(set(ids)),rel)
                for n in s.b.walk(doc):
                    self.assertFalse(n.get('arg_type')==100011 and n.get('sub_type')==1 and any(isinstance(x,dict) for x in n.get('args_list',[])),rel)
        self.assertEqual(len(tids),len(set(tids)));self.assertEqual(len(fids),len(set(fids)))
        self.assertIn(str(s.CHANGE),DATA['customevent.json']['conf'])
        self.assertEqual(DATA['globaltriggervariable.json']['variable_dict']['INTEGER'][s.THRESHOLD],8)
    def test_all_basic_attributes_reach_engine_attribute_contributions(self):
        mapping={'力量':('strength','ATTR_BASE'),'敏捷':('agility','ATTR_BASE'),'智力':('intelligence','ATTR_BASE'),
          '生命值':('hp_max','ATTR_BASE'),'生命%':('hp_max','ATTR_ALL_RATIO'),'攻击力':('attack_phy','ATTR_BASE'),
          '速度':('ori_speed','ATTR_ALL_RATIO'),'攻速':('attack_speed','ATTR_BASE'),'技能伤害':(s.b.SKILL_DAMAGE,'ATTR_BASE'),
          '所有伤害':('extra_dmg','ATTR_BASE')}
        checked=0
        for aid,spec in SPECS.items():
            w,c,front,rear,*_=world();w.card(c,aid);w.tick()
            for raw in spec['base']:
                if raw in (None,'','-'):continue
                checked+=1;name,num=raw.split('+');amount=float(num.rstrip('%'))
                fields=[(key,'ATTR_ALL_RATIO' if name=='全属性%' else 'ATTR_BASE') for key in ('strength','agility','intelligence')] if name.startswith('全属性') else [mapping[name]]
                for key,mode in fields:self.assertEqual(w.contribution(rear,key,mode),amount,(aid,raw,key))
        self.assertEqual(checked,70)
    def test_set_gains_and_terminal_union_single_pass(self):
        w,c,f,rear,bow,soldier=world()
        for aid in s.RESULTS:w.card(c,aid,source=2)
        w.card(c,134247270);w.tick()
        self.assertEqual(w.contribution(f,'extra_dmg'),5*20+95+40+60+15+40)
        self.assertEqual(w.contribution(bow,'extra_dmg'),5*20+95+40+60+15+25+40)
        self.assertEqual(w.contribution(rear,'extra_dmg'),25)
        self.assertEqual(w.contribution(soldier,'extra_dmg'),25)
    def test_return_value_action_does_not_exit(self):
        w,c,*_=world();vm=VM(w,c,s.BASE,False);vm.result=None
        vm.run([{'action_type':400342,'args_list':[s.r.flag(True)]},{'action_type':400342,'args_list':[s.r.flag(False)]}])
        self.assertIs(vm.result,False)
    def test_rules_created_once_and_reused(self):
        w,c,*_=world();w.card(c,134229176);table=c.kv[s.RULES];calls=w.function_calls[s.FIDS[13]]
        w.card(c,134233398)
        for _ in range(5):w.tick()
        self.assertIs(table,c.kv[s.RULES]);self.assertEqual(calls,w.function_calls[s.FIDS[13]])
    def test_repeat_refresh_loss_reobtain_life_ratio(self):
        w,c,f,*_=world();f.hp=400;w.card(c,134251374);w.tick();expected=dict(w.buffs[f.name,s.ARMY].contributions)
        for _ in range(3):VM(w,c,134251374,False).fire('ABILITY_LEVEL_CHANGED');w.tick()
        self.assertEqual(w.buffs[f.name,s.ARMY].contributions,expected);self.assertAlmostEqual(f.hp/w.attr(f,'hp_max'),.4)
        w.card(c,134251374,False,True);w.tick();self.assertEqual(w.contribution(f,'hp_max'),0);self.assertAlmostEqual(f.hp/w.attr(f,'hp_max'),.4)
        w.card(c,134251374);w.tick();self.assertEqual(w.buffs[f.name,s.ARMY].contributions,expected)
    def test_sparse_duplicate_stale_wrong_owner_records(self):
        w,c,f,*_=world();w.card(c,134229176);pool=w.pools[1];row=ROW_BY_ID[134229176]
        pool[100]={};pool[101]={'技能':None};pool[102]=dict(pool[row]);other=Unit('other')
        w.handles[other.name,134229176]=(other,134229176,900);pool[103]={'技能':w.handles[other.name,134229176],'归属单位':other}
        w.tick();self.assertEqual(w.contribution(f,'intelligence'),5)
    def test_eight_required_once_even_if_ex_lost_or_controller_recreated(self):
        w,c,*_=world()
        for aid in UR[:7]:w.card(c,aid)
        vm=VM(w,c,s.BASE,False);vm.execute(s.FIDS[19],[c]);self.assertEqual(w.grants,[])
        w.card(c,UR[7]);vm.execute(s.FIDS[19],[c]);self.assertEqual(len(w.grants),1);ex=w.grants[0][1]
        self.assertIn(ex,EX);self.assertTrue(w.player_kv[1][s.CLAIMED])
        w.card(c,ex,False);vm.execute(s.FIDS[19],[c]);self.assertEqual(len(w.grants),1)
        w.remove(w.buffs[c.name,s.CONTROL]);w.card(c,s.BASE);vm.execute(s.FIDS[19],[c]);self.assertEqual(len(w.grants),1)
    def test_threshold_is_public_and_duplicate_type_not_counted(self):
        w,c,*_=world();w.threshold=3
        for aid in UR[:2]:w.card(c,aid)
        vm=VM(w,c,s.BASE,False);self.assertFalse(vm.execute(s.COUNT,[1,3]))
        w.card(c,UR[2]);vm.execute(s.FIDS[19],[c]);self.assertEqual(len(w.grants),1)
    def test_selection_and_merge_probabilities_and_gifts_do_not_recurse(self):
        w,c,*_=world();w.random=[1,1] # 温恢 succeeds, first eligible UR
        w.card(c,134252946,source=1)
        self.assertEqual(len(w.grants),1);self.assertIn(w.grants[0][1],UR)
        self.assertEqual(w.random_ranges,[(1,100),(1,8)])
        self.assertFalse(c.kv[s.BUSY]);self.assertTrue(any(fid==s.UNLOCK for fid,_ in w.side_effects))
        w.random=[1,1];w.card(c,134251374,source=2)
        self.assertEqual(len(w.grants),2)
    def test_probability_cards_roll_independently_and_only_for_wei_acquisition(self):
        w,c,*_=world();w.card(c,134252946);w.card(c,134264459)
        vm=VM(w,c,s.BASE,False);vm.execute(s.FIDS[20],[c,1,s.s.BASE]);self.assertEqual(w.random_ranges,[])
        w.random=[11,21];vm.execute(s.FIDS[20],[c,1,134229176]);self.assertEqual(w.random_ranges,[(1,100),(1,100)]);self.assertEqual(w.grants,[])
    def test_wave_once_and_no_catchup(self):
        w,c,*_=world();w.card(c,134231749);w.card(c,134253995);w.random=[11,21];w.start(1)
        self.assertEqual(w.random_ranges,[(1,100),(1,100)]);w.start(1);self.assertEqual(len(w.random_ranges),2)
        w2,c2,*_=world();w2.wave=2;w2.phase=2;w2.card(c2,134231749);w2.start(2);self.assertEqual(w2.random_ranges,[])
    def test_jiaxu_120_combat_seconds_pause_in_prep(self):
        w,c,*_=world();w.card(c,134260135)
        for _ in range(240):w.tick()
        self.assertEqual(w.random_ranges,[])
        w.start(1)
        for _ in range(120):w.tick()
        w.phase=1
        for _ in range(500):w.tick()
        self.assertEqual(w.random_ranges,[])
        w.start(2)
        for _ in range(120):w.tick()
        self.assertEqual(w.random_ranges,[(1,100)])
        self.assertEqual(w.buffs[c.name,s.CONTROL].kv['贾诩累计战斗秒'],0)
    def test_existing_ex_marks_player_claimed_and_is_not_rerolled(self):
        w,c,*_=world();w.card(c,EX[0]);vm=VM(w,c,s.BASE,False);vm.execute(s.FIDS[19],[c])
        self.assertTrue(w.player_kv[1][s.CLAIMED]);self.assertEqual(w.grants,[])
    def test_players_and_new_soldier_isolation(self):
        w,c,f,*_=world();other=Unit('carrier2',player=2);f2=Unit('front2',player=2,tags={'魏国'},kv={'带领小队':[]})
        w.captains[2]=[f2];w.card(c,134229176);w.card(other,134269449);w.tick()
        self.assertEqual(w.contribution(f,'intelligence'),5);self.assertEqual(w.contribution(f2,'intelligence'),0)
        new=Unit('new',kv={'所属英雄':f});f.kv['带领小队'].append(new);w.tick();self.assertEqual(w.contribution(new,'intelligence'),5)
    def test_level_event_uses_valid_current_owner_and_no_kill_or_damage_listener(self):
        for aid in SPECS:
            event=next(t for t in DATA[f'ability/{aid}.json']['trigger_dict'].values() if t['event'][0]['event_type']=='ABILITY_LEVEL_CHANGED')
            self.assertFalse(any(n.get('sub_type')=='ABILITY_OWNER' for n in s.b.walk(event)))
        for oid in (s.CONTROL,s.ARMY):
            self.assertFalse(any(n.get('event_type')=='SPECIAL_UNIT_EVENT' or n.get('action_type') in ('APPLY_DAMAGE','SET_CUR_DAMAGE') for n in s.b.walk(DATA[f'modifier/{oid}.json'])))
    def test_retained_fixtures_have_no_autogrant_or_temporary_probability_logs(self):
        serialized=json.dumps(DATA,ensure_ascii=False)
        self.assertNotIn('临时验证_魏国军略20261026',serialized)
        self.assertNotIn('[魏国概率核对/20261026]',serialized)
    def completion_branch(self,doc):
        wei=next(n for n in s.b.walk(doc) if n.get('element_id')==454042342999360)
        return wei['args_list'][1]['args_list'][1]['args_list'][1]['args_list'][0]['args_list'][1]['args_list'][0]
    def completion_world(self,preowned):
        w,c,*_=world();w.card(c,s.BASE)
        for aid in (134229176,134233398,134252946):w.card(c,aid)
        if preowned:w.card(c,134251374)
        for rec in w.configs[1].values():
            if rec['所属set']=='州郡能吏':rec['是否解锁']=rec['是否已抽取']=rec['是否格子展示']=True
        # A new result remains locked, as in the native pre-merge state.
        if not preowned:w.configs[1][ROW_BY_ID[134251374]].update(是否解锁=False,是否已抽取=False,是否格子展示=False)
        vm=VM(w,c,s.BASE,False);vm.vars.update(执行玩家=1,所属set='州郡能吏',新增主动合成军略技能=None);vm.iter_key=ROW_BY_ID[134251374]
        return w,c,vm
    def test_reproduces_old_preowned_result_leaves_components_visible(self):
        doc=FIXTURE['legacy_select']
        w,c,vm=self.completion_world(True);vm.run([self.completion_branch(doc)])
        self.assertTrue(w.configs[1][ROW_BY_ID[134252946]]['是否格子展示'])
    def test_preowned_result_folds_components_without_duplicate_result_and_rewards_once(self):
        doc=DATA['global_trigger/function/new/功能执行/3选1军略卡牌处理.json'];w,c,vm=self.completion_world(True)
        try:vm.run([self.completion_branch(doc)])
        except BreakLoop:pass
        self.assertFalse(w.configs[1][ROW_BY_ID[134252946]]['是否格子展示'])
        self.assertFalse(w.configs[1][ROW_BY_ID[134229176]]['是否格子展示'])
        self.assertEqual(w.grants,[]);self.assertTrue(c.kv[s.COMPLETED+str(134251374)])
        self.assertEqual(w.random_ranges,[(1,100)]) # one natural-merge probability, no extra grant callback
        self.assertEqual(c.kv[s.PREFIX+'套牌魏国伤害'],10)
    def test_normal_new_result_keeps_native_fold_and_only_one_merge_reward(self):
        doc=DATA['global_trigger/function/new/功能执行/3选1军略卡牌处理.json'];w,c,vm=self.completion_world(False)
        try:vm.run([self.completion_branch(doc)])
        except BreakLoop:pass
        self.assertEqual(w.grants,[(1,134251374)]);self.assertFalse(w.configs[1][ROW_BY_ID[134252946]]['是否格子展示'])
        self.assertEqual(w.random_ranges,[(1,100)])
    def test_gifted_ur_is_not_natural_set_completion(self):
        w,c,f,*_=world();w.card(c,s.BASE);vm=VM(w,c,s.BASE,False)
        vm.execute(s.FIDS[21],[c,ROW_BY_ID[134251374]])
        self.assertEqual(w.contribution(f,'strength'),60)
        self.assertEqual(c.kv[s.PREFIX+'套牌魏国伤害'],0)
        self.assertNotIn(s.COMPLETED+str(134251374),c.kv)
        vm.execute(s.FIDS[20],[c,2,134251374]);self.assertEqual(c.kv[s.PREFIX+'套牌魏国伤害'],10)
    def test_final_probability_path_rolls_once_without_temporary_trace(self):
        w,c,*_=world();w.card(c,134252946);w.random=[11]
        VM(w,c,s.BASE,False).execute(s.FIDS[20],[c,1,134229176])
        self.assertEqual(w.grants,[]);self.assertEqual(w.random_ranges,[(1,100)])
        self.assertFalse(any('[魏国概率核对/20261026]'in m for m in w.messages))
        self.assertEqual(read('editor_table/abilityall/134252946.json')['kv']['选卡获骑概率']['value'],10)

if __name__=='__main__':unittest.main(verbosity=2)
