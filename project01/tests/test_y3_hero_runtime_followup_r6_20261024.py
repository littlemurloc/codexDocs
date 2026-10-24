"""Value-membership regressions for the one-operand shared helper fix."""
from copy import deepcopy as cp
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import y3_hero_runtime_followup_r6_20261024 as fix
from test_y3_hero_repair_p1_shared import TeamModel


class PvpModel(TeamModel):
    def check(self,node):
        if node['condition_type']=='PLAYERS_IS_ENEMY_RELATION':
            a,b=[self.ev(v) for v in node['args_list']]
            return a!=b
        return super().check(node)


class FollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=fix.base.trace.read(fix.WORK/'map3-before'/fix.TEAM)
        cls.new=fix.build(fix.WORK/'map3-before')[fix.TEAM]

    def result(self,doc,owner=1,mode='PVE',model=TeamModel):
        state=model(mode,owner);state.run(doc['action']);return state.returned

    def test_old_model_failure_reproduced_for_real_value_membership(self):
        self.assertEqual(self.result(self.old),('right',None))
        self.assertEqual(self.result(self.old,2),('right',None))

    def test_two_human_players_get_correct_pve_sides(self):
        self.assertEqual(self.result(self.new),('left','right'))
        self.assertEqual(self.result(self.new,2),('player2','right'))

    def test_npc_direction_unchanged(self):
        self.assertEqual(self.result(self.new,31),('right','left'))
        self.assertEqual(self.result(self.old,31),self.result(self.new,31))

    def test_pvp_opponents_and_return_order_unchanged(self):
        for owner,expected in [(1,('left','player2')),(2,('player2','left'))]:
            self.assertEqual(self.result(self.new,owner,'PVP',PvpModel),expected)
            self.assertEqual(self.result(self.old,owner,'PVP',PvpModel),expected)

    def test_no_implicit_coercion_of_array_keys_to_values(self):
        model=TeamModel('PVE',1)
        old_check=next(n for n in fix.base.walk(self.old) if n.get('condition_type')=='DICT_HAS_VALUE')
        new_check=next(n for n in fix.base.walk(self.new) if n.get('condition_type')=='DICT_HAS_VALUE')
        self.assertIn(1,model.values['玩家队伍'].keys())
        self.assertFalse(model.check(old_check))
        self.assertTrue(model.check(new_check))
        model.values['playersDetail']={1:2,7:1}
        self.assertTrue(model.check(new_check))
        model.values['playersDetail']={1:2}
        self.assertFalse(model.check(new_check))

    def test_missing_ability_preserves_null_returns(self):
        self.assertEqual(self.result(self.new,None),(None,None))
        self.assertEqual(self.result(self.old,None),(None,None))

    def test_only_membership_array_operand_is_changed(self):
        expected=cp(self.old)
        check=next(n for n in fix.base.walk(expected) if n.get('condition_type')=='DICT_HAS_VALUE')
        check['args_list'][0]['args_list'][0]['items']=['PLAYER','playersDetail']
        self.assertEqual(expected,self.new)
        self.assertEqual(self.old['func_id'],self.new['func_id'])
        self.assertEqual({n['element_id'] for n in fix.base.walk(self.old) if 'element_id'in n},
                         {n['element_id'] for n in fix.base.walk(self.new) if 'element_id'in n})

    def test_patch_is_idempotent_and_matches_native_player_array_example(self):
        self.assertEqual(fix.patch_player_membership(self.new),self.new)
        native=fix.base.trace.read(fix.WORK/'map3-before/global_trigger/function/new/参数返回/返回【玩家单位组】根据队长单位.json')
        native_check=next(n for n in fix.base.walk(native) if n.get('condition_type')=='DICT_HAS_VALUE')
        fixed_check=next(n for n in fix.base.walk(self.new) if n.get('condition_type')=='DICT_HAS_VALUE')
        self.assertEqual(native_check['args_list'][0],fixed_check['args_list'][0])


if __name__=='__main__':unittest.main()
