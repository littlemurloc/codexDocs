import json
import unittest
from pathlib import Path
from tools import y3_hero_repair_p2_taishi_context as repair

ROOT = Path('D:/littl/testTempFile/ProjectMonster02/maps/map3')


class ContextTests(unittest.TestCase):
    def test_damage_event_has_no_cast_context_getter(self):
        old = json.loads((ROOT / repair.CORE).read_text('utf8'))
        fixed = repair.patch_core(old)
        hurt = fixed['trigger_dict']['1418035204']
        self.assertFalse(any(n.get('sub_type') == 'TARGET_UNIT_IN_ABILITY' for n in repair.walk(hurt)))
        checks = hurt['action'][0]['args_list'][0]['args_list']
        self.assertEqual([c['condition_type'] for c in checks], ['HAS_KV_ANY', 'HAS_KV_ANY'])
        self.assertEqual(old['trigger_dict']['594665475'], fixed['trigger_dict']['594665475'])

    def test_each_cast_records_after_manual_target_override(self):
        for aid in repair.ACTIVES:
            original = json.loads((ROOT / f'ability/{aid}.json').read_text('utf8'))
            fixed = repair.patch_active(original)
            before = original['trigger_dict']['893440004']['action']
            after = fixed['trigger_dict']['893440004']['action']
            self.assertEqual(after[0]['args_list'][2]['args_list'], [False])
            self.assertEqual(after[1], before[0])
            self.assertEqual(after[3:], before[1:])
            store = after[2]['args_list'][1]['args_list']
            self.assertEqual(store[0]['args_list'][1]['args_list'], [repair.PRIMARY])
            self.assertEqual(store[0]['args_list'][2]['args_list'][0]['items'][-1], 'actor')
            self.assertEqual(store[1]['args_list'][2]['args_list'], [True])

    def test_new_ids_do_not_replace_unknown_metadata(self):
        for aid in repair.ACTIVES:
            original = json.loads((ROOT / f'ability/{aid}.json').read_text('utf8'))
            original['custom_future_field'] = {'number': 9007199254740993123}
            fixed = repair.patch_active(original)
            self.assertEqual(fixed['custom_future_field'], original['custom_future_field'])
            old_ids = {n['element_id'] for n in repair.walk(original) if 'element_id' in n}
            new_ids = [n['element_id'] for n in repair.walk(fixed)
                       if 'element_id' in n and n['element_id'] not in old_ids]
            self.assertEqual(len(new_ids), len(set(new_ids)))
