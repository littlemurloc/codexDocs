"""Bounded target-list regressions, not a native casting simulation."""
from copy import deepcopy as cp
from pathlib import Path
from types import SimpleNamespace as NS
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import y3_hero_runtime_followup_r5_20261024 as fix
from test_y3_hero_runtime_followup_20261024 import Frame,unit


class TeamFrame(Frame):
    def __init__(self,*args):
        super().__init__(*args)
        self.enemies=[];self.lookups=0

    def value(self,n):
        if n.get('sub_type')=='869622f5961411f1933a3fb31c846afd':
            assert n['arg_type']==100026 and n['call_rt_index']==1
            self.lookups+=1
            return self.enemies
        return super().value(n)


class FollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=fix.base.trace.read(fix.WORK/'map3-before'/fix.FILES[0])
        cls.new=fix.build(fix.WORK/'map3-before')[fix.FILES[0]]

    def scene(self,new=True,positions=(1,4)):
        owner=unit();owner.can_act=True;owner.kv['自动施法']=True
        f=TeamFrame(NS(cooldown=0),owner)
        f.enemies=[unit(team=2,position=p) for p in positions]
        if f.enemies:f.enemies[0].buffs[134232159]=NS(source=owner)
        f.vars[('UNIT_GROUP','搜索组','actor')]=[]
        doc=self.new if new else self.old
        timer=fix.base.one(doc['trigger_dict']['1959489540']['action'],'RUN_LOOP_TIMER')
        return f,timer['args_list'][3]['args_list']

    def test_empty_old_cache_blocks_even_with_current_live_enemies(self):
        f,actions=self.scene(False);f.run(actions)
        self.assertFalse(f.commands);self.assertEqual(f.lookups,0)

    def test_fresh_lookup_recovers_target_and_preserves_enemy_group(self):
        f,actions=self.scene();original=list(f.enemies);f.run(actions)
        self.assertEqual(len(f.commands),1)
        self.assertIs(f.commands[0][2],original[0])
        self.assertEqual(f.enemies,original);self.assertEqual(f.lookups,1)

    def test_phase_refresh_does_not_clear_shared_alias(self):
        for new in [False,True]:
            f,_=self.scene(new);f.vars[('UNIT_GROUP','搜索组','actor')]=f.enemies
            f.run((self.new if new else self.old)['trigger_dict']['82759685']['action'])
            self.assertEqual(len(f.enemies),2 if new else 0)

    def test_next_poll_reads_replaced_team_instead_of_previous_wave(self):
        f,actions=self.scene();f.run(actions)
        old=f.enemies
        new_target=unit(team=2,position=2);new_other=unit(team=2,position=5)
        new_target.buffs[134232159]=NS(source=f.owner)
        f.enemies=[new_target,new_other];f.run(actions)
        self.assertEqual(len(f.commands),2)
        self.assertIs(f.commands[1][2],new_target)
        self.assertEqual(len(old),2)

    def test_lone_mark_and_different_lane_remain_ineligible(self):
        for positions in [(1,),(1,2),()]:
            f,actions=self.scene(positions=positions);f.run(actions)
            self.assertFalse(f.commands)

    def test_wrong_source_native_death_and_hero_fake_death_are_excluded(self):
        for case in ['wrong_source','native','fake']:
            f,actions=self.scene();target=f.enemies[0]
            if case=='wrong_source':target.buffs[134232159].source=unit()
            if case=='native':target.alive=False
            if case=='fake':target.tags.add('已死亡')
            f.run(actions);self.assertFalse(f.commands,case)

    def test_lookup_is_gated_by_cooldown_phase_and_action_state(self):
        for case in ['cooldown','phase','busy','owner_dead']:
            f,actions=self.scene()
            if case=='cooldown':f.skill.cooldown=1
            if case=='phase':f.phase=1
            if case=='busy':f.owner.can_act=False
            if case=='owner_dead':f.owner.tags.add('已死亡')
            f.run(actions);self.assertEqual(f.lookups,0,case)

    def test_only_one_new_refresh_action_and_one_removed_clear(self):
        old={n['element_id']:n for n in fix.base.walk(self.old) if 'element_id'in n}
        new={n['element_id']:n for n in fix.base.walk(self.new) if 'element_id'in n}
        self.assertEqual(set(old)-set(new),{82759685000003})
        self.assertEqual(len(set(new)-set(old)),1)
        n=new[next(iter(set(new)-set(old)))]
        self.assertEqual(n['action_type'],'SET_VARIABLE')
        self.assertEqual(n['args_list'][1]['call_rt_index'],1)
        self.assertEqual(self.old['trigger_dict']['893440004'],self.new['trigger_dict']['893440004'])
        self.assertEqual(fix.base.one(self.old,'UNIT_RELEASE_COMMAND'),fix.base.one(self.new,'UNIT_RELEASE_COMMAND'))
        reg=fix.base.trace.read(fix.base.trace.REGISTRY)['entries'][fix.FILES[0]]
        fix.base.trace.checked_nodes(self.new,reg['logs'])


if __name__=='__main__':unittest.main()
