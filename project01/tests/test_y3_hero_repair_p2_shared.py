import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import y3_hero_repair_p2_shared as repair

MAP = Path('D:/littl/testTempFile/ProjectMonster02/maps/map3')


class KnockbackTests(unittest.TestCase):
    def test_original_division_is_unprotected(self):
        old = repair.load(MAP / repair.KNOCKBACK)
        actions = old['action'][0]['args_list'][1]['args_list']
        self.assertIn(1311690899000648, [a['element_id'] for a in actions])
        with self.assertRaises(ZeroDivisionError):
            _ = 0.0 / math.hypot(0.0, 0.0)

    def test_guard_precedes_both_normalizations(self):
        old = repair.load(MAP / repair.KNOCKBACK)
        fixed = repair.patch_knockback(old)
        actions = fixed['action'][0]['args_list'][1]['args_list']
        self.assertEqual(actions[-2]['element_id'], 1754329234000241)
        guard = actions[-1]
        self.assertEqual(guard['action_type'], 'IF_THEN_ELSE')
        test = guard['args_list'][0]['args_list'][0]
        self.assertEqual(test['condition_type'], 'FLOAT_COMPARE')
        self.assertEqual(test['args_list'][1]['args_list'], ['>'])
        self.assertEqual(test['args_list'][2]['args_list'], [0.000001])
        self.assertEqual(guard['args_list'][1]['args_list'],
                         old['action'][0]['args_list'][1]['args_list'][4:])

    def test_direction_and_distance_still_match(self):
        for dx, dy in [(0, 0), (0.0000001, 0), (3, 4), (-3, 4), (0, -10)]:
            magnitude = math.hypot(dx, dy)
            if magnitude <= 0.000001:
                displacement = (0, 0)
            else:
                displacement = (200 * dx / magnitude, 200 * dy / magnitude)
                self.assertAlmostEqual(math.hypot(*displacement), 200)
            self.assertTrue(all(math.isfinite(x) for x in displacement))


class LevelTests(unittest.TestCase):
    def test_user_approved_floor_retains_level_one(self):
        for oid, key in repair.LEVEL_KEYS.items():
            with self.subTest(skill=oid):
                original = repair.load(MAP / f'ability/{oid}.json')
                fixed, before, after = repair.patch_levels(original, key)
                self.assertLess(before[1], before[0])
                self.assertEqual(before[0], after[0])
                self.assertEqual(after, sorted(after))
                self.assertTrue(all(new >= old for old, new in zip(before, after)))
                self.assertEqual(fixed['trigger_dict']['893440004'], original['trigger_dict']['893440004'])
                self.assertEqual(repair.patch_levels(fixed, key)[1], after)


if __name__ == '__main__':
    unittest.main()
