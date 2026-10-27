"""Execute journal ECA offline; grant/UI foreign hooks remain explicit doubles."""
from __future__ import annotations
import copy,json,contextlib,unittest
import y3_card_test_fixtures as fixtures
import y3_command_card_journal as j
import test_y3_wei_command_cards as base
w=j.w
FIXTURE=fixtures.load('journal')
DATA=FIXTURE['data']
FUNCS={**base.FUNCS,**{o['func_id']:o for o in DATA.values() if isinstance(o,dict) and o.get('is_func')}}
ORIGINAL=base.VM

class VM(ORIGINAL):
    def execute(self,fid,args):
        if fid in (w.s.FIDS[14],w.d.FIDS[14]):return # foreign faction refresh hook: no matching Buff in these fixtures
        if fid not in FUNCS:return super().execute(fid,args)
        doc=FUNCS[fid];vm=object.__new__(VM)
        vm.w,vm.owner,vm.oid,vm.modifier=self.w,self.owner,doc['trigger_id'],False
        vm.obj=doc;vm.kv={};vm.vars={};vm.contributions={};vm.registered=set();vm.selected=None;vm.params={};vm.handle=None;vm.iter_key=None;vm.result=None;vm.loop_index=None
        for values in doc['var_data'][0].values():vm.vars.update(copy.deepcopy(values))
        assert len(args)==len(doc['func_param_list']),(fid,len(args))
        for p,a in zip(doc['func_param_list'],args):vm.vars[p['items'][0]]=a
        self.w.function_calls[fid]=self.w.function_calls.get(fid,0)+1
        vm.run(doc['action']);return vm.result
    def ev(self,node):
        if not isinstance(node,dict):return node
        t=node.get('sub_type');a=node.get('args_list',[])
        if t in FUNCS:return self.execute(t,[self.ev(x) for x in a])
        if a and isinstance(a[0],dict) and a[0].get('items')==['BOOLEAN',j.FLAG]:return self.w.journal_enabled
        if a and isinstance(a[0],dict) and a[0].get('items')==['PLAYER','playersDetail']:
            players=sorted(self.w.carriers)
            return players[self.ev(a[1])-1] if len(a)>1 else players
        if t=='GET_LOOP_LIST_INDEX':return self.loop_index
        if t=='GET_UNIT_NAME':return self.ev(a[0]).name
        if t=='GET_ABILITY_INT_ATTR':
            handle,attribute=[self.ev(x) for x in a]
            assert attribute=='ability_level',attribute
            return self.w.levels.get((handle[0].name,handle[1]),1)
        if t=='UNIT_ADD_ABILITY':
            unit,category,aid=[self.ev(x) for x in a]
            if node.get('op_arg_enable',[False,False])[1]:self.assert_level_one(node['op_arg'][1])
            self.w.serial+=1;handle=self.w.handles.setdefault((unit.name,aid),(unit,aid,self.w.serial));unit.cards.add(aid);unit.card_categories[aid]=category
            if f'ability/{aid}.json' in base.DATA:VM(self.w,unit,aid,False).fire('ABILITY_OBTAIN')
            self.w.grants.append((unit.player,aid));return handle
        return super().ev(node)
    def assert_level_one(self,node):assert self.ev(node)==1
    def run(self,actions):
        for n in actions:
            if isinstance(n,dict) and n.get('action_type')=='LIST_LOOP':
                a=n['args_list'];previous=self.loop_index
                try:
                    for i in range(1,len(self.ev(a[0]))+1):self.loop_index=i;self.run(a[1]['args_list'])
                finally:self.loop_index=previous
            else:super().run([n])

class World(base.World):
    def __init__(self):super().__init__();self.journal_enabled=True;self.levels={}
    def card(self,u,aid,add=True,before_lose=False,source=0):
        # The native shared grant appends dense records. Keep the fixture dense,
        # not indexed by the static catalog row number.
        super().card(u,aid,add,before_lose,source)
        self.pools[u.player]={i+1:row for i,row in enumerate(self.pools[u.player].values())}

@contextlib.contextmanager
def runtime():
    with base.runtime():
        prev=(base.old.VM,base.old.read,base.v.read,base.VM,base.FUNCS)
        base.old.VM=VM;base.old.read=read;base.v.read=read;base.VM=VM;base.FUNCS=FUNCS
        try:yield
        finally:base.old.VM,base.old.read,base.v.read,base.VM,base.FUNCS=prev

def read(rel):return DATA[rel] if rel in DATA else base.read(rel)
def world():
    old,c,*units=base.world();x=World();x.units=old.units;x.captains=old.captains;return x,c,*units

class JournalCases(unittest.TestCase):
    def setUp(self):self.context=runtime();self.context.__enter__()
    def tearDown(self):self.context.__exit__(None,None,None)
    def test_hooks_leave_all_original_gameplay_actions_unchanged(self):
        tracking=FIXTURE['hook_tracking']
        def strip(v,ids):
            if isinstance(v,list):return [strip(x,ids) for x in v if not(isinstance(x,dict) and x.get('element_id') in ids)]
            if isinstance(v,dict):return {k:strip(x,ids) for k,x in v.items()}
            return v
        for rel,rec in tracking.items():
            after=strip(copy.deepcopy(DATA[rel]),set(rec['added_ids']))
            for name in rec.get('new_variables',[]):
                for category in after['var_data'][0].values():category.pop(name,None)
                after['var_data'][1].pop(name,None);after['var_data'][2].remove(name)
            for kind in list(after['var_data'][0]):
                if kind not in rec['original']['var_data'][0] and not after['var_data'][0][kind]:del after['var_data'][0][kind]
            self.assertEqual(after,rec['original'],rel)
        self.assertEqual(sum(n.get('sub_type')=='RANDOM_INT' for n in j.b.walk(DATA[f'{w.FOLDER}/{w.NAMES[17]}.json'])),1)
    def test_selection_is_verified_from_actual_instance(self):
        x,c,*_=world();x.card(c,w.BASE);x.card(c,134252946)
        VM(x,c,w.BASE,False).execute(j.FIDS[1],[1,134252946,'选卡获得或升级'])
        self.assertIn('结果=已持有',x.messages[-1]);self.assertIn('卡牌=134252946',x.messages[-1]);self.assertIn('来源=选卡获得或升级',x.messages[-1])
        VM(x,c,w.BASE,False).execute(j.FIDS[1],[1,134264459,'选卡获得或升级'])
        self.assertIn('未读到有效实例',x.messages[-1])
    def test_random_gift_records_exact_source_event_roll_and_result(self):
        x,c,*_=world();x.card(c,w.BASE);x.card(c,134252946);x.random=[1,1]
        VM(x,c,w.BASE,False).execute(w.FIDS[20],[c,1,134229176])
        logs=[m for m in x.messages if '[军略日志/v1]' in m]
        self.assertEqual(len(x.grants),1);self.assertEqual(len(logs),1)
        self.assertIn('随机赠送；来源卡牌=134252946；触发=选卡获骑概率；概率=10.0；掷骰=1',logs[0])
        self.assertIn('卡牌='+str(x.grants[0][1]),logs[0]);self.assertEqual(x.player_kv[1][j.CTX],'');self.assertEqual(x.player_kv[1][j.BOUND],'')
        self.assertEqual(x.random_ranges,[(1,100),(1,8)])
    def test_ex_has_explicit_result_and_snapshot(self):
        x,c,*_=world();x.card(c,w.BASE)
        for aid in base.UR:x.card(c,aid)
        VM(x,c,w.BASE,False).execute(w.FIDS[19],[c])
        results=[m for m in x.messages if '[军略日志/v1]' in m]
        self.assertEqual(len(x.grants),1);self.assertIn(x.grants[0][1],base.EX)
        self.assertIn('身份=EX',results[-1]);self.assertIn('EX授予；条件=八虎骑数量达标；门槛=8',results[-1])
        self.assertTrue(any('EX种数=1' in m for m in x.messages))
    def test_snapshot_excludes_stale_foreign_owner_and_unknown_hero_skills(self):
        x,c,*_=world();x.card(c,w.BASE);x.card(c,134252946);p=x.pools[1]
        p[50]=dict(p[2]);p[51]={'技能':None};other=base.Unit('other');h=(other,134252946,999);x.handles[other.name,134252946]=h;p[52]={'技能':h,'归属单位':other}
        hero=134230908;h=(c,hero,1000);x.handles[c.name,hero]=h;p[53]={'技能':h,'归属单位':c}
        VM(x,c,w.BASE,False).execute(j.FIDS[2],[1,'周期',False])
        entries=[m for m in x.messages if '条目；' in m];self.assertEqual(len(entries),2);self.assertFalse(any(str(hero) in m for m in entries))
        self.assertIn('卡牌种数=2',x.messages[-1])
    def test_unchanged_periodic_snapshot_is_silent_but_forced_exit_is_printed(self):
        x,c,*_=world();x.card(c,w.BASE);vm=VM(x,c,w.BASE,False)
        vm.execute(j.FIDS[2],[1,'周期',False]);n=len(x.messages)
        for _ in range(3):vm.execute(j.FIDS[2],[1,'周期',False])
        self.assertEqual(n,len(x.messages));vm.execute(j.FIDS[2],[1,'主动退出',True]);self.assertGreater(len(x.messages),n)
        self.assertTrue(any('原因=主动退出' in m for m in x.messages))
    def test_folded_card_stays_in_snapshot_and_lost_card_disappears(self):
        x,c,*_=world();x.card(c,w.BASE);x.card(c,134252946)
        x.configs[1][base.ROW_BY_ID[134252946]]['是否格子展示']=False
        vm=VM(x,c,w.BASE,False);vm.execute(j.FIDS[2],[1,'处理结束',False])
        self.assertTrue(any('卡牌=134252946' in m and '界面展示=False' in m for m in x.messages))
        x.card(c,134252946,False);x.messages.clear();vm.execute(j.FIDS[2],[1,'周期',False])
        self.assertFalse(any('条目；' in m and '卡牌=134252946' in m for m in x.messages))
    def test_player_context_binding_prevents_misattribution(self):
        x,c,*_=world();x.card(c,w.BASE);x.card(c,134252946)
        x.player_kv[1]={j.CTX:'随机赠送；来源卡牌=曹彰',j.BOUND:'99999'}
        VM(x,c,w.BASE,False).execute(j.FIDS[1],[1,134252946,'合成授予'])
        self.assertIn('来源=合成授予',x.messages[-1]);self.assertNotIn('来源卡牌=曹彰',x.messages[-1])
    def test_all_players_are_isolated(self):
        x,c,*_=world();other=base.Unit('p2',player=2);x.card(c,134252946);x.card(other,134264459)
        VM(x,c,w.BASE,False).execute(j.FIDS[3],['关卡结算',True])
        self.assertTrue(any('玩家=1' in m and '卡牌=134252946' in m for m in x.messages));self.assertTrue(any('玩家=2' in m and '卡牌=134264459' in m for m in x.messages))
        self.assertEqual(x.player_kv[1][j.SNAP],1);self.assertEqual(x.player_kv[2][j.SNAP],1)
    def test_switch_off_changes_no_rewards_or_logging_state(self):
        x,c,*_=world();x.journal_enabled=False;x.card(c,w.BASE);x.card(c,134252946);x.random=[1,1]
        VM(x,c,w.BASE,False).execute(w.FIDS[20],[c,1,134229176])
        self.assertEqual(len(x.grants),1);self.assertEqual(x.messages,[])
        self.assertFalse(any(key.startswith('军略日志_') for data in x.player_kv.values() for key in data))
    def test_missing_carrier_reports_last_snapshot_instead_of_zero_cards(self):
        x,c,*_=world();x.card(c,w.BASE);vm=VM(x,c,w.BASE,False);vm.execute(j.FIDS[2],[1,'周期',False])
        x.carriers[1]=None;vm.execute(j.FIDS[2],[1,'关卡结算',True]);self.assertIn('最后有效快照=1',x.messages[-1]);self.assertIn('当前记录不可读',x.messages[-1])
    def test_ids_references_and_native_table_encoding(self):
        tids=[]
        for rel,doc in DATA.items():
            if not rel.endswith('.json'):continue
            if rel.startswith((j.FOLDER,'global_trigger/trigger/军略')):
                tids.extend(n['trigger_id'] for n in j.b.walk(doc) if 'trigger_id' in n)
            ids=[n['element_id'] for n in j.b.walk(doc) if 'element_id' in n];self.assertEqual(len(ids),len(set(ids)),rel)
            for n in j.b.walk(doc):self.assertFalse(n.get('arg_type')==100011 and n.get('sub_type')==1 and any(isinstance(a,dict) for a in n.get('args_list',[])),rel)
        self.assertEqual(len(tids),len(set(tids)))
        self.assertTrue(DATA['globaltriggervariable.json']['variable_dict']['BOOLEAN'][j.FLAG])
        pub=DATA[j.TRIGGER];self.assertEqual(len(pub['sub_trigger']),5);self.assertTrue(all(int(k) in pub['action'] for k in pub['sub_trigger']))

if __name__=='__main__':unittest.main(verbosity=2)
