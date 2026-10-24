import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from y3_hero_repair_p1_shared import walk, load
import y3_hero_repair_p1_huangzhong as repair

MAP = Path('D:/littl/testTempFile/ProjectMonster02/maps/map3')


class HuangZhongTests(unittest.TestCase):
    def setUp(self):
        self.old = load(MAP / repair.FILE)
        self.new = repair.patch(self.old)

    def test_old_log_node_writes_unit_but_reader_uses_skill(self):
        old = [n for _, n in walk(self.old['trigger_dict']['1340796934'])
               if n.get('action_type') == 'SET_ENTITY_KV']
        self.assertEqual({n['args_list'][0]['sub_type'] for n in old}, {'ABILITY_OWNER'})
        new = [n for _, n in walk(self.new['trigger_dict']['1340796934'])
               if n.get('action_type') == 'SET_ENTITY_KV']
        self.assertEqual({n['args_list'][0]['sub_type'] for n in new}, {'CUR_ABILITY'})

    def test_timer_is_owned_restarted_and_cancelled(self):
        hit = self.new['trigger_dict']['1340796934']
        timers = [n for _, n in walk(hit) if n.get('action_type') == 'RUN_ONCE_TIMER']
        self.assertEqual(len(timers), 1)
        self.assertEqual(timers[0]['args_list'][1], repair.ex(100000, 1, 3))
        self.assertTrue(any(n.get('action_type') == 'DELETE_TIMER' for _, n in walk(hit)))
        self.assertEqual(self.new['trigger_dict']['225054724']['action'][0]['action_type'], 'DELETE_TIMER')

    def test_prerequisite_checks_are_behind_valid_ability(self):
        for tid in ('1340796934', '2111275013'):
            trigger = self.new['trigger_dict'][tid]
            self.assertEqual(trigger['condition'], [])
            self.assertEqual(trigger['action'][0]['args_list'][0]['args_list'][0]['condition_type'], 'TYPE_IS_EXIST')
        reset = next(n for _, n in walk(self.new) if n.get('element_id') == 1340796934000042)
        self.assertEqual(reset['args_list'][0]['sub_type'], 'CUR_ABILITY')


if __name__ == '__main__':
    unittest.main()
