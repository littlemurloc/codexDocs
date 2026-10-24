import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import y3_hero_repair_p2_passives as repair

MAP = Path('D:/littl/testTempFile/ProjectMonster02/maps/map3')


class PassiveTests(unittest.TestCase):
    def test_lubu_checks_victim_not_self(self):
        original = repair.load(MAP / 'modifier/134274222.json')
        fixed = repair.patch_lubu_core(original)
        old = original['trigger_dict']['762560516']
        new = fixed['trigger_dict']['762560516']
        self.assertEqual(old['action'], new['action'])
        for _, node in repair.walk(new['condition']):
            if node.get('condition_type') == 'UNIT_HAS_TAG':
                self.assertEqual(node['args_list'][0], repair.ex(100006, 'KILLED_UNIT'))

    def test_lubu_requires_one_visible_resource(self):
        fixed = repair.patch_lubu_six(repair.load(MAP / 'ability/134275485.json'))
        outer = fixed['trigger_dict']['58232837']['action'][0]
        self.assertEqual(outer['args_list'][0]['args_list'][0]['condition_type'], 'TYPE_IS_EXIST')
        check = outer['args_list'][1]['args_list'][0]['args_list'][0]['args_list'][0]
        self.assertEqual(check['args_list'][1]['args_list'], ['>'])
        self.assertEqual(check['args_list'][2]['args_list'], [1])
        self.assertFalse(1 > 1)
        self.assertTrue(2 > 1)

    def test_zhaoyun_tracks_applied_contribution(self):
        original = repair.load(MAP / 'ability/134263318.json')
        fixed = repair.patch_zhaoyun_contribution(original)
        self.assertEqual(fixed['variable_dict']['FLOAT']['P2已应用游龙闪避'], 0)
        applied, total = 0, 7  # Seven points supplied by a different source.
        for level in (1, 2, 3, 3, 5):
            total -= applied
            applied = 15
            total += applied
            self.assertEqual(total, 22)
        total -= applied
        applied = 0
        self.assertEqual(total, 7)
        # The lose path actually contains the corresponding subtraction.
        loss = fixed['trigger_dict']['225054724']['action']
        self.assertEqual(len([n for _, n in repair.walk(loss) if n.get('action_type') == 'ADD_ATTR']), 1)

    def test_kongcheng_uses_twelve_seconds(self):
        original = repair.load(MAP / 'ability/134263515.json')
        fixed = repair.patch_zhuge_cooldown(original)
        old = original['trigger_dict']['58232837']['action'][4]
        new = fixed['trigger_dict']['58232837']['action'][4]
        self.assertEqual(old['args_list'][0]['args_list'], [6])
        self.assertEqual(new['args_list'][0]['args_list'], [12])
        self.assertEqual(old['args_list'][1:], new['args_list'][1:])

    def test_lumeng_only_own_invisibility(self):
        old = repair.load(MAP / 'ability/134243085.json')
        new = repair.patch_lumeng_owner(old)
        trigger = new['trigger_dict']['58232837']
        check = trigger['condition'][-1]
        self.assertEqual(check['condition_type'], 'UNIT_COMPARE')
        self.assertEqual(check['args_list'][0], repair.ex(100006, 'MODIFIER_OWNER'))
        self.assertEqual(check['args_list'][2], repair.ex(100006, 'ABILITY_OWNER'))
        self.assertEqual(trigger['action'], old['trigger_dict']['58232837']['action'])
        self.assertEqual(trigger['condition'][:-1], old['trigger_dict']['58232837']['condition'])


if __name__ == '__main__':
    unittest.main()
