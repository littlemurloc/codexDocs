"""Regression branches for the failures observed in the 09:40 retest."""
from pathlib import Path
from types import SimpleNamespace as NS
import collections
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import y3_hero_runtime_followup_r2_20261024 as fix
from test_y3_hero_runtime_followup_20261024 import Frame, unit


class FollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = {p: fix.first.trace.read(fix.WORK/'map3-before'/p) for p in fix.FILES}
        cls.new = fix.build(fix.WORK/'map3-before')

    def zhang(self, stack=3):
        owner, target = unit(), unit(team=2)
        owner.can_act = True; owner.kv['自动施法'] = True
        target.buffs[134259870] = NS(stack=stack, maximum=3)
        core = NS(kv={'震慑单位': target})
        owner.buffs[134259689] = core
        f = Frame(NS(cooldown=0), owner)
        f.vars[('UNIT_GROUP','搜索组','actor')] = []
        timer = fix.first.one(self.new[fix.FILES[0]]['trigger_dict']['1959489540']['action'], 'RUN_LOOP_TIMER')
        return f, target, timer['args_list'][3]['args_list']

    def test_zhang_empty_cached_group_no_longer_blocks_real_full_target(self):
        f, target, actions = self.zhang(); f.run(actions)
        self.assertEqual(len(f.commands), 1)
        self.assertIs(f.commands[0][2], target)

    def test_zhang_not_full_does_not_cast(self):
        f, _, actions = self.zhang(2); f.run(actions); self.assertFalse(f.commands)

    def test_zhang_dead_target_no_core_and_busy_do_not_cast(self):
        for case in ['dead', 'fake', 'no_core', 'busy', 'cooldown', 'preparation']:
            f, target, actions = self.zhang()
            if case=='dead': target.alive=False
            if case=='fake': target.tags.add('已死亡')
            if case=='no_core': f.owner.buffs.clear()
            if case=='busy': f.owner.can_act=False
            if case=='cooldown': f.skill.cooldown=1
            if case=='preparation': f.phase=1
            f.run(actions); self.assertFalse(f.commands,case)

    def test_zhang_does_not_clear_aliased_team_group(self):
        d=self.new[fix.FILES[0]]
        phase=d['trigger_dict']['1016573957']
        self.assertFalse([n for n in fix.walk(phase) if n.get('action_type')=='CLEAR_GROUP'])
        timer=fix.first.one(d['trigger_dict']['1959489540']['action'],'RUN_LOOP_TIMER')
        self.assertFalse([n for n in fix.walk(timer) if n.get('sub_type')==14
                          and '搜索组' in str(n)])

    def test_sunce_consumption_reentry_is_filtered_at_event_root(self):
        old=self.old[fix.FILES[1]]['trigger_dict']['1051000836']
        new=self.new[fix.FILES[1]]['trigger_dict']['1051000836']
        buff=NS(resource=134279388,stack=1,kv={'孙策潮势冲斩处理中':True})
        f=Frame(NS(),unit(),buff)
        self.assertTrue(all(f.condition(n) for n in old['condition']))
        self.assertFalse(all(f.condition(n) for n in new['condition']))
        buff.stack=3;buff.kv['孙策潮势冲斩处理中']=False
        self.assertTrue(all(f.condition(n) for n in new['condition']))

    def test_sunce_ignores_other_buffs_before_snapshot_writes(self):
        t=self.new[fix.FILES[1]]['trigger_dict']['1051000836']
        f=Frame(NS(),unit(),NS(resource=123,stack=3,kv={}))
        self.assertFalse(all(f.condition(n) for n in t['condition']))

    def test_sunce_no_callback_context_reads_outer_local_frame(self):
        d=self.new[fix.FILES[1]]
        references=[n['items'] for n in fix.walk(d) if '__tuple__' in n and len(n['items'])==3
                    and isinstance(n['items'][1],str) and n['items'][1].startswith('P2_latest_')]
        self.assertTrue(references)
        self.assertTrue(all(r[2]=='actor' for r in references))
        self.assertEqual(sum(len(v) for k,v in d['variable_dict'].items()
                             if k in ['ABILITY','BOOLEAN','FLOAT','INTEGER','MODIFIER_ENTITY','POINT','UNIT_ENTITY']),9)
        self.assertFalse(any(n.startswith('P2_latest_') for v in
                            d['local_variable']['1051000836']['variable_dict'].values() for n in v))

    def test_summer_three_valid_target_survives_nested_iteration(self):
        d=self.new[fix.FILES[2]]
        owner=unit();owner.can_act=True;owner.kv['自动施法']=True
        a,b=unit(team=2,position=1),unit(team=2,position=4)
        a.buffs[134232159]=NS(source=owner)
        f=Frame(NS(cooldown=0),owner)
        f.vars[('UNIT_GROUP','搜索组','actor')]=[a,b]
        timer=fix.first.one(d['trigger_dict']['1959489540']['action'],'RUN_LOOP_TIMER')
        f.run(timer['args_list'][3]['args_list'])
        self.assertEqual(len(f.commands),1)
        self.assertIs(f.commands[0][2],a)
        refs=[n['items'] for n in fix.walk(timer) if '__tuple__' in n and len(n['items'])==3
              and isinstance(n['items'][1],str) and n['items'][1].startswith('修复_贯阵')]
        self.assertTrue(all(r[2]=='actor' for r in refs))

    def test_summer_five_missing_core_is_guarded(self):
        t=self.new[fix.FILES[3]]['trigger_dict']['1959489540']
        guards=[n for n in fix.walk(t) if n.get('action_type')=='IF_THEN_ELSE'
                and n['element_id'] in range(209996800130000,209996800140000)]
        outer=next(n for n in guards if n['args_list'][0]['args_list'][0]['args_list'][0]
                   .get('sub_type')=='ABILITY_OWNER')
        Frame(NS(),unit()).run([outer])

    def test_registry_and_original_trigger_ids_preserved(self):
        registry=fix.first.trace.read(fix.first.trace.REGISTRY)
        for path,d in self.new.items():
            fix.first.trace.checked_nodes(d,registry['entries'][path]['logs'])
            self.assertEqual(set(d['trigger_dict']),set(self.old[path]['trigger_dict']))

    def test_no_added_duplicate_node_ids(self):
        fresh=set()
        for path,d in self.new.items():
            before=collections.Counter(n['element_id'] for n in fix.walk(self.old[path]) if 'element_id' in n)
            after=collections.Counter(n['element_id'] for n in fix.walk(d) if 'element_id' in n)
            self.assertFalse({k:v for k,v in after.items() if v>max(1,before[k])})
            new=set(after)-set(before);self.assertFalse(fresh&new);fresh.update(new)


if __name__=='__main__':unittest.main()
