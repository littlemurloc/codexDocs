import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import y3_hero_repair_p2_descriptions as repair

MAP = Path('D:/littl/testTempFile/ProjectMonster02/maps/map3')


class DescriptionTests(unittest.TestCase):
    def test_only_approved_rows_change(self):
        original = repair.load(MAP / 'tables/技能作用描述表.json')
        payload, _ = repair.build(MAP)
        rows = payload['tables/技能作用描述表.json']['table_data']['data']
        for before, after in zip(original['table_data']['data'], rows):
            if len(before) > 1 and before[1] in repair.TEXT:
                self.assertIn('近战普攻受伤', after[3])
                if before[1] == 134271608:
                    self.assertIn('受近战伤害获得守势', after[3])
            else:
                self.assertEqual(before, after)

    def test_overlay_keeps_new_language_keys(self):
        language = repair.load(MAP / 'zhlanguage.json')
        language['test-unrelated-added-key'] = 'new support name'
        saved = copy.deepcopy(language)
        result, _ = repair.build(MAP, {'zhlanguage.json': language})
        self.assertEqual(result['zhlanguage.json']['test-unrelated-added-key'], 'new support name')
        self.assertEqual(language, saved)


if __name__ == '__main__':
    unittest.main()
