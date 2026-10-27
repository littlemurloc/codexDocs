"""Execute staged Qun ECA. Engine, persistence and visible UI remain separate.

Selections model the observed grant-before-record-write boundary. Merge,
route-unlock and component-folding functions execute their actual ECA. Only
unrelated faction refresh hooks and the card animation are explicit doubles.
"""
from __future__ import annotations
import contextlib,copy,json,re,unittest
import y3_card_test_fixtures as fixtures
import y3_qun_command_cards as q
import test_y3_command_card_journal as j
base=j.base
FIXTURE=fixtures.load('qun')
DATA=FIXTURE['data']
FUNCS={**j.FUNCS,**{v['func_id']:v for v in DATA.values() if isinstance(v,dict) and v.get('is_func')}}
for p in (q.MAP/'global_trigger/function').rglob('*.json'):
    obj=json.loads(p.read_text('utf8'))
    if obj.get('func_id') in (q.w.UNLOCK,'fba1b5a5a9a211f19b468d90bbbf35e2'):FUNCS[obj['func_id']]=obj
SPECS={int(k):v for k,v in FIXTURE['specs'].items()}
ROWS=FIXTURE['config']['table_data']['data']
CONFIG={int(x[0]):{k:True if v=='true' else False if v=='false' else v for k,v in zip(ROWS[0],x) if k} for x in ROWS[2:]}
ROW_BY_ID={v['技能类型']:k for k,v in CONFIG.items()}
RESULTS={(v['route'],v['stage']):aid for aid,v in SPECS.items() if v['identity']=='套牌结果'}
FOREIGN={q.w.FIDS[14],q.w.FIDS[20],q.w.s.FIDS[14],q.w.d.FIDS[14]}
Unit=base.Unit

def read(rel):return DATA[rel] if rel in DATA else q.read(rel)

class VM(j.VM):
    def execute(self,fid,args):
        if fid in FOREIGN:return
        if fid==q.w.SHOW:self.w.side_effects.append((fid,args));return
        if fid not in FUNCS:raise AssertionError('Unknown foreign function '+fid)
        doc=FUNCS[fid];vm=object.__new__(VM)
        vm.w,vm.owner,vm.oid,vm.modifier=self.w,self.owner,doc['trigger_id'],False
        vm.obj=doc;vm.kv={};vm.vars={};vm.contributions={};vm.registered=set();vm.selected=None;vm.params={};vm.handle=None;vm.iter_key=None;vm.result=None;vm.loop_index=None
        for values in doc['var_data'][0].values():vm.vars.update(copy.deepcopy(values))
        assert len(args)==len(doc['func_param_list']),(fid,len(args))
        for p,a in zip(doc['func_param_list'],args):vm.vars[p['items'][0]]=a
        self.w.function_calls[fid]=self.w.function_calls.get(fid,0)+1
        vm.run(doc['action']);return vm.result
    def ev(self,n):
        if not isinstance(n,dict):return n
        t=n.get('sub_type');a=n.get('args_list',[])
        if n.get('arg_type')==100003 and t==1 and any(isinstance(v,dict) for v in a):
            raise AssertionError('Runtime string expression wrapped as a STRING literal')
        if t in FUNCS or t in FOREIGN:return self.execute(t,[self.ev(x) for x in a])
        if t=='UNIT_ADD_ABILITY' and self.ev(a[2]) in self.w.fail_grants:return None
        if t=='MATH_OPERATION':
            x,op,y=[self.ev(x) for x in a];assert op=='+',op;return int(x+y)
        if t in (1,2,6,11,'VARIABLE') and a and isinstance(a[0],list) and len(a[0])==3 and a[0][2]=='local':
            value=self.vars[a[0][1]]
            return value[self.ev(a[1])-1] if len(a)>1 else value
        if t in (2,'VARIABLE') and len(a)==2 and isinstance(a[0],dict) and len(a[0].get('items',[]))==3:
            return self.vars[self.variable(n)][self.ev(a[1])-1]
        return super().ev(n)
    def run(self,actions):
        for n in actions:
            if isinstance(n,dict) and n.get('action_type')=='SET_VARIABLE_STR_LIST':
                a=n['args_list'];self.vars[self.variable(a[0])]=self.ev(a[1]).split(self.ev(a[2]))
            elif isinstance(n,dict) and n.get('action_type')=='SET_ABILITY_LEVEL':
                h,level=[self.ev(x) for x in n['args_list']];self.w.levels[h[0].name,h[1]]=level
                VM(self.w,h[0],h[1],False).fire('ABILITY_LEVEL_CHANGED')
            else:super().run([n])

class World(j.World):
    def __init__(self):super().__init__();self.fail_grants=set()
    def choose(self,u,aid,check_unlocked=True):
        self.carriers[u.player]=u;self.configs.setdefault(u.player,copy.deepcopy(CONFIG));pool=self.pools.setdefault(u.player,{})
        row=ROW_BY_ID[aid]
        if check_unlocked:assert self.configs[u.player][row]['是否解锁'],('Locked selection',aid)
        assert aid not in u.cards,('Already owned selection',aid)
        self.inject(u,aid)
        self.configs[u.player][row]['是否已抽取']=True
        vm=VM(self,u,q.BASE,False);vm.execute(q.FIDS[15],[u.player,aid]);vm.execute(q.FIDS[14],[u])
    def inject(self,u,aid):
        self.carriers[u.player]=u;self.configs.setdefault(u.player,copy.deepcopy(CONFIG));pool=self.pools.setdefault(u.player,{})
        self.serial+=1;h=(u,aid,self.serial);self.handles[u.name,aid]=h;u.cards.add(aid);u.card_categories[aid]=2
        VM(self,u,aid,False).fire('ABILITY_OBTAIN')
        pool[max(pool,default=0)+1]={'技能':h,'归属单位':u,'技能类型':aid,'是否已抽取':True}
    def card(self,u,aid,add=True,before_lose=False,source=0):
        if add:self.inject(u,aid);return
        if before_lose:VM(self,u,aid,False).fire('ABILITY_LOSE')
        u.cards.remove(aid);self.handles.pop((u.name,aid),None)
        if not before_lose:VM(self,u,aid,False).fire('ABILITY_LOSE')
    def tick(self):
        for oid in (q.CONTROL,q.ARMY):
            for vm in list(self.buffs.values()):
                if vm.oid==oid:vm.fire('MODIFIER_CYCLE_TRIGGER')
    def contribution(self,u,key,mode='ATTR_BASE'):
        vm=self.buffs.get((u.name,q.ARMY));return vm.contributions.get((key,mode),0.) if vm else 0.

@contextlib.contextmanager
def runtime():
    targets=[(base.old,'VM',VM),(base.old,'read',read),(base.v,'FUNCS',FUNCS),(base.v,'read',read),
      (base,'VM',VM),(base,'FUNCS',FUNCS),(base,'read',read),(base,'DATA',DATA),
      (j,'FUNCS',FUNCS),(j,'VM',VM)]
    before=[(obj,key,getattr(obj,key)) for obj,key,_ in targets]
    for obj,key,val in targets:setattr(obj,key,val)
    try:yield
    finally:
        for obj,key,val in reversed(before):setattr(obj,key,val)

def world():
    x=World();c=Unit('carrier');front=Unit('front',tags={'群雄','骑兵'},kv={'归属阵型编号':1})
    rear=Unit('rear',tags={'吴国','枪兵'},kv={'归属阵型编号':7});soldier=Unit('soldier',tags={'骑兵'},kv={'所属英雄':front})
    front.kv['带领小队']=[soldier];rear.kv['带领小队']=[]
    x.units=[c,front,rear,soldier];x.captains[1]=[front,rear]
    x.choose(c,q.BASE);return x,c,front,rear,soldier

def finish(x,c,route,stage):
    for aid in SPECS[RESULTS[route,stage]]['members']:
        if aid not in c.cards:x.choose(c,aid)

class QunCases(unittest.TestCase):
    def setUp(self):self.ctx=runtime();self.ctx.__enter__()
    def tearDown(self):self.ctx.__exit__(None,None,None)
    def test_initializes_both_chains_once_without_legacy_lock(self):
        x,c,*_=world();v=VM(x,c,q.BASE,False)
        for route in ('西凉','黄巾'):
            self.assertEqual(x.player_kv[1][q.STEP+route],1)
            for aid in SPECS[RESULTS[route,1]]['members']:self.assertTrue(x.configs[1][ROW_BY_ID[aid]]['是否解锁'])
        x.player_kv[1][q.STEP+'西凉']=3;v.execute(q.FIDS[17],[1]);self.assertEqual(x.player_kv[1][q.STEP+'西凉'],3)
    def test_west_normal_ur_other_chain_finishes_current_then_stops(self):
        x,c,*_=world();finish(x,c,'黄巾',1)
        for stage in range(1,6):finish(x,c,'西凉',stage)
        self.assertEqual(c.cards&set(q.UR),{q.NORMAL_WEST});self.assertTrue(x.player_kv[1][q.CLAIMED])
        finish(x,c,'黄巾',2);self.assertIn(RESULTS['黄巾',2],c.cards)
        self.assertEqual(x.player_kv[1][q.STEP+'黄巾'],2)
        self.assertFalse(x.configs[1][ROW_BY_ID[SPECS[RESULTS['黄巾',3]]['members'][0]]]['是否解锁'])
        self.assertEqual(sum(aid in q.UR for _,aid in x.grants),1)
    def test_yellow_normal_ur(self):
        x,c,*_=world()
        for stage in range(1,6):finish(x,c,'黄巾',stage)
        self.assertEqual(c.cards&set(q.UR),{q.NORMAL_YELLOW})
    def test_special_ur_requires_both_last_sets_unlocked_not_completed(self):
        for first in ('西凉','黄巾'):
            with self.subTest(first=first):
                x,c,*_=world()
                for stage in range(1,5):finish(x,c,'西凉',stage);finish(x,c,'黄巾',stage)
                self.assertFalse(c.cards&set(q.UR))
                finish(x,c,first,5);self.assertEqual(c.cards&set(q.UR),{q.SPECIAL})
                other='黄巾' if first=='西凉' else '西凉';self.assertNotIn(RESULTS[other,5],c.cards)
                finish(x,c,other,5);self.assertEqual(c.cards&set(q.UR),{q.SPECIAL})
                self.assertEqual(sum(aid in q.UR for _,aid in x.grants),1)
    def test_other_chain_at_stage_four_does_not_qualify_for_special(self):
        x,c,*_=world()
        for stage in range(1,4):finish(x,c,'黄巾',stage)
        for stage in range(1,6):finish(x,c,'西凉',stage)
        self.assertEqual(c.cards&set(q.UR),{q.NORMAL_WEST})
        finish(x,c,'黄巾',4);self.assertEqual(x.player_kv[1][q.STEP+'黄巾'],4)
    def test_completed_group_is_idempotent_reputation_only_once(self):
        x,c,*_=world();finish(x,c,'西凉',1);h=x.handles[c.name,q.BASE];key=(c.name,q.BASE,'声望累计');value=x.instance_kv[key]
        vm=VM(x,c,q.BASE,False);last=SPECS[RESULTS['西凉',1]]['members'][-1]
        for _ in range(4):vm.execute(q.FIDS[15],[1,last]);x.tick()
        self.assertEqual(x.instance_kv[key],value);self.assertEqual(len(x.grants),1)
        self.assertEqual(x.random_ranges,[(10,20)])
    def test_native_component_folding_is_preserved_without_deleting_cards(self):
        x,c,*_=world()
        for aid in SPECS[RESULTS['西凉',1]]['members']:x.configs[1][ROW_BY_ID[aid]]['是否格子展示']=True
        finish(x,c,'西凉',1)
        for aid in SPECS[RESULTS['西凉',1]]['members']:
            self.assertIn(aid,c.cards);self.assertFalse(x.configs[1][ROW_BY_ID[aid]]['是否格子展示'])
            self.assertTrue(x.configs[1][ROW_BY_ID[aid]]['是否已抽取'])
    def test_reputation_thresholds_can_cross_multiple_levels(self):
        x,c,*_=world();x.instance_kv[c.name,q.BASE,'声望累计']=115;x.levels[c.name,q.BASE]=1
        x.random=[10];finish(x,c,'西凉',1)
        self.assertEqual(x.instance_kv[c.name,q.BASE,'声望累计'],125);self.assertEqual(x.levels[c.name,q.BASE],5)
    def test_ur_loss_and_control_rebuild_do_not_allow_another(self):
        x,c,*_=world()
        for stage in range(1,6):finish(x,c,'西凉',stage)
        x.card(c,q.NORMAL_WEST,False);x.remove(x.buffs[c.name,q.CONTROL]);VM(x,c,q.BASE,False).execute(q.FIDS[1],[c,x.handles[c.name,q.BASE]])
        VM(x,c,q.BASE,False).execute(q.FIDS[22],[1]);finish(x,c,'黄巾',1)
        self.assertTrue(x.player_kv[1][q.CLAIMED]);self.assertEqual(sum(aid in q.UR for _,aid in x.grants),1)
    def test_failed_terminal_grant_keeps_chosen_ending_and_retries(self):
        x,c,*_=world();x.fail_grants.add(q.NORMAL_WEST)
        for stage in range(1,6):finish(x,c,'西凉',stage)
        self.assertFalse(x.player_kv[1].get(q.CLAIMED,False));self.assertEqual(x.player_kv[1][q.PENDING],q.NORMAL_WEST)
        oldrep=x.instance_kv[c.name,q.BASE,'声望累计'];x.fail_grants.clear();x.tick()
        self.assertTrue(x.player_kv[1][q.CLAIMED]);self.assertEqual(c.cards&set(q.UR),{q.NORMAL_WEST})
        self.assertEqual(oldrep,x.instance_kv[c.name,q.BASE,'声望累计'])
    def test_actual_records_not_stale_flags_decide_collection(self):
        x,c,*_=world();aids=SPECS[RESULTS['西凉',1]]['members']
        for aid in aids:x.configs[1][ROW_BY_ID[aid]]['是否已抽取']=True
        vm=VM(x,c,q.BASE,False);self.assertFalse(vm.execute(q.FIDS[18],[1,'乡勇营']))
        for aid in aids[:-1]:x.choose(c,aid)
        self.assertNotIn(RESULTS['西凉',1],c.cards)
        x.choose(c,aids[-1]);self.assertIn(RESULTS['西凉',1],c.cards)
    def test_sparse_duplicate_stale_and_wrong_owner_records(self):
        x,c,*_=world();aid=SPECS[RESULTS['西凉',1]]['members'][0];x.choose(c,aid);pool=x.pools[1];pool[90]=dict(pool[2]);pool[91]={'技能':None}
        other=Unit('other');h=(other,aid,999);x.handles[other.name,aid]=h;pool[92]={'技能':h,'归属单位':c}
        vm=VM(x,c,q.BASE,False);self.assertEqual(vm.execute(q.FIDS[16],[1,aid]),x.handles[c.name,aid])
        x.card(c,aid,False);self.assertIsNone(vm.execute(q.FIDS[16],[1,aid]))
        vm.execute(q.FIDS[14],[c]);x.tick()
        self.assertEqual(x.contribution(x.units[1],'intelligence'),0.)
    def test_runtime_string_keys_are_not_literal_objects(self):
        node=q.b.text(q.r.join(q.b.text('a'),q.b.text('b')))
        x,c,*_=world()
        with self.assertRaisesRegex(AssertionError,'STRING literal'):VM(x,c,q.BASE,False).ev(node)
    def test_all_82_source_attributes_reach_unit_contributions(self):
        mapping={'力量':('strength','ATTR_BASE'),'敏捷':('agility','ATTR_BASE'),'智力':('intelligence','ATTR_BASE'),
          '攻击力':('attack_phy','ATTR_BASE'),'生命值':('hp_max','ATTR_BASE'),'技能伤害':(q.b.SKILL_DAMAGE,'ATTR_BASE'),
          '所有伤害':('extra_dmg','ATTR_BASE'),'暴击伤害':('critical_dmg','ATTR_BASE'),'暴击率':('critical_chance','ATTR_BASE'),
          '速度':('ori_speed','ATTR_ALL_RATIO'),'攻速':('attack_speed','ATTR_BASE')}
        fields=0
        for aid,spec in SPECS.items():
            if spec['row'] is None:continue
            x,c,front,_,soldier=world();x.inject(c,aid);x.tick();expected={}
            for raw in spec['base']:
                if raw in (None,'','-'):continue
                fields+=1;name,value=raw.split('+');value=float(value.rstrip('%'))
                attrs=[('strength','ATTR_BASE'),('agility','ATTR_BASE'),('intelligence','ATTR_BASE')] if name=='全属性' else [mapping[name]]
                for key in attrs:expected[key]=expected.get(key,0)+value
            for (attr,mode),value in expected.items():
                for target in (front,soldier):
                    extra=80. if aid in q.UR and attr=='extra_dmg' else 0.
                    extra+=40. if aid in q.UR and attr=='extra_dmg' else 0.
                    self.assertAlmostEqual(x.contribution(target,attr,mode),value+extra,(aid,target.name,attr))
        self.assertEqual(fields,82)
    def test_all_three_ur_have_same_common_benefits(self):
        for aid in q.UR:
            x,c,front,rear,soldier=world();x.inject(c,aid);x.tick()
            own=SPECS[aid]['params'].get(q.b.field_key('extra_dmg','ATTR_BASE'),0.)
            self.assertEqual(x.contribution(front,'extra_dmg'),own+80+40)
            self.assertEqual(x.contribution(soldier,'extra_dmg'),own+80+40)
            self.assertEqual(x.contribution(rear,'extra_dmg'),own)
    def test_completed_sets_stack_and_refresh_does_not_heal_or_accumulate(self):
        x,c,front,rear,soldier=world()
        for stage in range(1,4):finish(x,c,'西凉',stage)
        x.tick();self.assertEqual(x.contribution(front,'extra_dmg'),35+15)
        front.hp=x.attr(front,'hp_max')*.4
        for _ in range(4):VM(x,c,q.BASE,False).execute(q.FIDS[14],[c]);x.tick()
        self.assertEqual(x.contribution(front,'extra_dmg'),50);self.assertAlmostEqual(front.hp/x.attr(front,'hp_max'),.4)
    def test_player_isolation(self):
        x,c,*_=world();other=Unit('p2',player=2);x.choose(other,q.BASE)
        for stage in range(1,6):finish(x,c,'西凉',stage)
        for stage in range(1,6):finish(x,other,'黄巾',stage)
        self.assertEqual(c.cards&set(q.UR),{q.NORMAL_WEST});self.assertEqual(other.cards&set(q.UR),{q.NORMAL_YELLOW})
    def test_source_logs_reputation_and_ur_and_original_rng_only(self):
        x,c,*_=world()
        for stage in range(1,6):finish(x,c,'西凉',stage)
        self.assertTrue(any('群雄路线终局' in m and '134260219' in m for m in x.messages))
        self.assertEqual(sum('声望结算' in m for m in x.messages),5)
        self.assertEqual(x.random_ranges,[(10,20)]*5)
        self.assertEqual(x.player_kv[1][q.journal.CTX],'');self.assertEqual(x.player_kv[1][q.journal.BOUND],'')
    def test_shared_hooks_preserve_other_factions_and_existing_journal(self):
        tracking=FIXTURE['shared_tracking']
        for rel,rec in tracking.items():
            after=copy.deepcopy(DATA[rel])
            if 'added_id' in rec:after['action']=[n for n in after['action'] if n.get('element_id')!=rec['added_id']]
            else:
                node=next(n for n in q.b.walk(after) if n.get('element_id')==rec['replacement_id']);node.clear();node.update(rec['removed_box'])
            self.assertEqual(after,rec['original'],rel)
    def test_ids_native_arguments_and_no_stale_faction_refs(self):
        tids=[]
        for rel,doc in DATA.items():
            if not rel.endswith('.json'):continue
            if rel.startswith((q.FOLDER+'/','ability/','modifier/')):
                tids.extend(n['trigger_id'] for n in q.b.walk(doc) if 'trigger_id' in n)
                self.assertFalse(set(n.get('sub_type') for n in q.b.walk(doc))&set(q.w.FIDS.values()),rel)
                ids=[n['element_id'] for n in q.b.walk(doc) if 'element_id' in n];self.assertEqual(len(ids),len(set(ids)),rel)
                for n in q.b.walk(doc):self.assertFalse(n.get('arg_type') in (100011,100003) and n.get('sub_type')==1 and any(isinstance(a,dict) for a in n.get('args_list',[])),rel)
        self.assertEqual(len(tids),len(set(tids)))
        self.assertEqual(len(SPECS),54);self.assertEqual(len([p for p in DATA if p.startswith('ability/')]),54)
        for aid in RESULTS.values():
            before=FIXTURE['legacy_result_actions'][str(aid)]
            after=list(DATA[f'ability/{aid}.json']['trigger_dict'].values())[0]['action'][0]
            def trim(n):
                for v in q.b.walk(n):v.pop('element_id',None)
                return n
            self.assertEqual(trim(copy.deepcopy(before)),trim(copy.deepcopy(after)))

if __name__=='__main__':unittest.main(verbosity=2)
