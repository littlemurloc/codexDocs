"""Execute forge ECA and native merge/material-accumulation paths offline.

Engine/UI are separate acceptance layers; no forced cards are published.
"""
from __future__ import annotations
import copy,json,unittest
import y3_forge_command_cards as f
import test_y3_qun_command_cards as h
import y3_recent_work_fixtures as fixtures
FIXTURE=fixtures.load('forge')
DATA=FIXTURE['staged']
h.DATA.update(DATA)
h.FUNCS.update({v['func_id']:v for v in DATA.values()if isinstance(v,dict)and v.get('is_func')})
for path in (f.q.journal.SELECT,f.q.journal.MERGE):h.FUNCS[DATA[path]['func_id']]=DATA[path]
ROWS=DATA['tables/军令卡牌技能表.json']['table_data']['data']
CONFIG={int(row[0]):{k:True if v=='true'else False if v=='false'else v for k,v in zip(ROWS[0],row)if k}for row in ROWS[2:]}
ROW={v['技能类型']:k for k,v in CONFIG.items()}
class VM(h.VM):
    def cond(self,node):
        if node.get('condition_type')=='CHECK_HAS_ABILITY_TYPE':
            unit,aid=[self.ev(v)for v in node['args_list']];return unit is not None and aid in unit.cards
        return super().cond(node)
    def ev(self,node):
        if isinstance(node,dict)and node.get('sub_type')=='NONE_ABILITY_KEY':return None
        if isinstance(node,dict)and node.get('sub_type')=='INT_TO_STR':return str(self.ev(node['args_list'][0]))
        if isinstance(node,dict)and node.get('sub_type')=='GET_ABILITY_CONF_STR_ATTR':
            aid,key=[self.ev(v)for v in node['args_list']];value=DATA[f'editor_table/abilityall/{aid}.json'][key]
            return DATA['zhlanguage.json'].get(str(value),value)
        if isinstance(node,dict)and node.get('sub_type')=='MATH_OPERATION':
            a,op,c=[self.ev(v)for v in node['args_list']]
            if op=='+':return a+c
            if op=='-':return a-c
            if op=='*':return a*c
            if op=='/':return a/c
            raise AssertionError(op)
        return super().ev(node)
class World(h.World):
    def setup(self,u):
        self.carriers[u.player]=u;self.configs.setdefault(u.player,copy.deepcopy(CONFIG));self.pools.setdefault(u.player,{})
    def choose(self,u,aid):
        self.setup(u);cfg=self.configs[u.player];assert cfg[ROW[aid]]['是否解锁']
        if aid in f.MATERIALS.values()and aid in u.cards:
            doc=DATA[f.q.journal.SELECT];box=next(n for n in f.b.walk(doc)if n.get('action_type')=='STORAGE_BOX'and len(n.get('args_list',[]))>3 and n['args_list'][3].get('args_list')==['武器锻造 材料累计 特殊处理'])
            vm=VM(self,u,f.BASE,False);vm.vars.update(执行玩家=u.player,所属set='武器锻造材料',处理技能类型=aid);vm.iter_key=ROW[aid];vm.run([box])
        else:self.inject(u,aid);cfg[ROW[aid]]['是否已抽取']=True
        vm=VM(self,u,f.BASE,False);vm.execute(f.FIDS[15],[u.player,aid]);vm.execute(f.FIDS[14],[u])
    def tick(self):
        for oid in (f.CONTROL,f.ARMY):
            for vm in list(self.buffs.values()):
                if vm.oid==oid:vm.fire('MODIFIER_CYCLE_TRIGGER')
    def contribution(self,u,attr):
        vm=self.buffs.get((u.name,f.ARMY));return vm.contributions.get((attr,'ATTR_BASE'),0.)if vm else 0.

def world():
    x=World();c=h.Unit('carrier');hero=h.Unit('hero',kv={'归属阵型编号':1});soldier=h.Unit('soldier',kv={'所属英雄':hero});hero.kv['带领小队']=[soldier]
    x.units=[c,hero,soldier];x.captains[1]=[hero];x.choose(c,f.BASE);return x,c,hero,soldier
def count(x,c,aid):return VM(x,c,f.BASE,False).execute(f.FIDS[18],[c.player,aid])
def forge(x,c,paper):
    if paper not in c.cards:x.choose(c,paper)
    kv=DATA[f'editor_table/abilityall/{paper}.json']['kv']
    for material,aid in f.MATERIALS.items():
        for _ in range(kv[material]['value']):x.choose(c,aid)

class ForgeCases(unittest.TestCase):
    def setUp(self):
        self.old=h.VM;h.VM=VM;self.ctx=h.runtime();self.ctx.__enter__()
    def tearDown(self):self.ctx.__exit__(None,None,None);h.VM=self.old
    def test_open_ten_inputs_and_no_results_or_ex(self):
        x,c,*_=world();opened={v['技能类型']for v in x.configs[1].values()if v['是否解锁']}
        self.assertEqual(opened,{f.BASE,*f.BLUEPRINTS,*f.MATERIALS.values()})
    def test_minimal_route_opens_only_copper_and_one_blueprint(self):
        old=h.FUNCS[f.FIDS[17]]
        try:
            h.FUNCS[f.FIDS[17]]=copy.deepcopy(FIXTURE['minimal_opening_rule'])
            x,c,*_=world();opened={v['技能类型']for v in x.configs[1].values()if v['是否解锁']}
            self.assertEqual(opened,{f.BASE,134264424,134275195});forge(x,c,134264424);self.assertIn(134229761,c.cards)
        finally:h.FUNCS[f.FIDS[17]]=old
    def test_first_and_repeated_material_quantity(self):
        x,c,*_=world();aid=f.MATERIALS['铜'];x.choose(c,aid);self.assertEqual(count(x,c,aid),1);x.choose(c,aid);self.assertEqual(count(x,c,aid),2)
        self.assertTrue(x.configs[1][ROW[aid]]['是否解锁']);self.assertFalse(x.configs[1][ROW[aid]]['是否已抽取'])
    def test_hero_only_basic_stats(self):
        x,c,hero,soldier=world();x.tick();self.assertEqual(x.contribution(hero,'strength'),5);self.assertEqual(x.contribution(hero,'attack_phy'),10)
        self.assertEqual(x.contribution(soldier,'strength'),0);self.assertEqual(x.contribution(soldier,'attack_phy'),0)
    def test_each_recipe_and_growth_once(self):
        for paper,weapon in f.BLUEPRINTS.items():
            x,c,hero,soldier=world();forge(x,c,paper);x.tick();self.assertIn(weapon,c.cards);self.assertEqual(x.player_kv[1][f.COUNT],1)
            self.assertEqual(x.levels[c.name,f.BASE],2);self.assertEqual(x.contribution(hero,'strength'),12);self.assertEqual(x.contribution(soldier,'strength'),0)
            vm=VM(x,c,f.BASE,False)
            for _ in range(3):vm.execute(f.FIDS[15],[1,paper]);x.tick()
            self.assertEqual(x.player_kv[1][f.COUNT],1);self.assertEqual(sum(aid==weapon for _,aid in x.grants),1)
            for material,aid in f.MATERIALS.items():self.assertEqual(count(x,c,aid),0)
    def test_insufficient_material_does_not_consume_or_grant(self):
        x,c,*_=world();x.choose(c,134264424)
        for _ in range(2):x.choose(c,f.MATERIALS['铜'])
        self.assertNotIn(134229761,c.cards);self.assertEqual(count(x,c,f.MATERIALS['铜']),2);self.assertEqual(x.player_kv[1].get(f.COUNT,0),0)
    def test_grant_failure_keeps_materials_and_retries(self):
        x,c,*_=world();x.fail_grants.add(134229761);forge(x,c,134264424)
        self.assertEqual(count(x,c,f.MATERIALS['铜']),3);self.assertEqual(x.player_kv[1].get(f.COUNT,0),0)
        x.fail_grants.clear();x.tick();self.assertIn(134229761,c.cards);self.assertEqual(count(x,c,f.MATERIALS['铜']),0)
    def test_materials_before_paper_also_craft(self):
        x,c,*_=world()
        for _ in range(3):x.choose(c,f.MATERIALS['铜'])
        x.choose(c,134264424);self.assertIn(134229761,c.cards)
    def test_all_five_terminal_and_no_double_reward(self):
        x,c,hero,soldier=world()
        for paper in f.BLUEPRINTS:forge(x,c,paper)
        x.tick();self.assertEqual(x.player_kv[1][f.COUNT],5);self.assertEqual(x.levels[c.name,f.BASE],6);self.assertIn(f.EX,c.cards)
        self.assertEqual(x.contribution(hero,'strength'),70);self.assertEqual(x.contribution(hero,'extra_dmg'),50);self.assertEqual(x.contribution(soldier,'extra_dmg'),50)
        for _ in range(3):VM(x,c,f.BASE,False).execute(f.FIDS[22],[1]);x.tick()
        self.assertEqual(sum(aid==f.EX for _,aid in x.grants),1)
    def test_reacquired_ex_does_not_double_terminal(self):
        x,c,hero,soldier=world()
        for paper in f.BLUEPRINTS:forge(x,c,paper)
        x.card(c,f.EX,False);x.tick();self.assertNotIn(f.EX,c.cards);self.assertEqual(sum(aid==f.EX for _,aid in x.grants),1);self.assertEqual(x.contribution(hero,'extra_dmg'),50)
    def test_growth_survives_hammer_loss(self):
        x,c,hero,soldier=world();forge(x,c,134264424);x.card(c,f.BASE,False);x.tick()
        self.assertEqual(x.contribution(hero,'strength'),2);self.assertEqual(x.contribution(soldier,'strength'),0)
    def test_whole_shared_nonforge_actions_preserved(self):
        track=FIXTURE['shared_tracking'];doc=copy.deepcopy(DATA[f.q.journal.SELECT])
        node=next(n for n in f.b.walk(doc)if n.get('element_id')==track['new_box_id']);node.clear();node.update(track['old_forge_box']);self.assertEqual(doc,track['select_original'])
    def test_all_hammer_levels_are_replacements(self):
        x,c,hero,soldier=world();handle=x.handles[c.name,f.BASE]
        for level,(all_,atk)in enumerate(zip(f.ALL,f.ATTACK),1):
            x.levels[c.name,f.BASE]=level;VM(x,c,f.BASE,False).fire('ABILITY_LEVEL_CHANGED');x.tick()
            self.assertEqual(x.contribution(hero,'strength'),all_);self.assertEqual(x.contribution(hero,'attack_phy'),atk);self.assertEqual(x.contribution(soldier,'attack_phy'),0)
    def test_terminal_reward_failure_retries_without_extra_crafting(self):
        x,c,*_=world();x.fail_grants.add(f.EX)
        for paper in f.BLUEPRINTS:forge(x,c,paper)
        self.assertEqual(x.player_kv[1][f.COUNT],5);self.assertNotIn(f.EX,c.cards)
        x.fail_grants.clear();x.tick();self.assertIn(f.EX,c.cards);self.assertEqual(x.player_kv[1][f.COUNT],5)
    def test_terminal_controller_has_no_periodic_reapply(self):
        x,c,*_=world()
        for paper in f.BLUEPRINTS:forge(x,c,paper)
        x.tick();version=c.kv[f.PREFIX+'版本']
        for _ in range(4):x.tick()
        self.assertEqual(c.kv[f.PREFIX+'版本'],version)
        for aid in f.MATERIALS.values():self.assertFalse(x.configs[1][ROW[aid]]['是否解锁'])
    def test_completion_and_material_inventory_are_player_isolated(self):
        x,c,*_=world();other=h.Unit('other',player=2);x.choose(other,f.BASE);forge(x,c,134264424)
        self.assertEqual(x.player_kv[1][f.COUNT],1);self.assertEqual(x.player_kv.get(2,{}).get(f.COUNT,0),0)
        self.assertNotIn(134229761,other.cards);self.assertEqual(count(x,other,f.MATERIALS['铜']),0)
    def test_native_types_ids_and_no_old_faction_refs(self):
        tids=[]
        for path,doc in DATA.items():
            if not path.startswith((f.FOLDER+'/','ability/','modifier/')):continue
            for n in f.b.walk(doc):
                if 'trigger_id'in n:tids.append(n['trigger_id'])
                self.assertFalse(n.get('arg_type')in(100003,100011)and n.get('sub_type')==1 and any(isinstance(a,dict)for a in n.get('args_list',[])),path)
                self.assertNotIn(n.get('sub_type'),set(f.q.FIDS.values()),path)
            ids=[n['element_id']for n in f.b.walk(doc)if 'element_id'in n];self.assertEqual(len(ids),len(set(ids)),path)
        self.assertEqual(len(tids),len(set(tids)))

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ForgeCases))
    raise SystemExit(not result.wasSuccessful())
