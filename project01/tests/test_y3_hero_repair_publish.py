import sys
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import y3_hero_repair_publish as publish
from y3_hero_repair_publish import merge_three_way, publication_blockers


class MergeTests(unittest.TestCase):
    def test_disjoint_language_additions(self):
        self.assertEqual(merge_three_way({'1': 'old'}, {'1': 'old', '2': 'new'}, {'1': 'old', '3': 'third'}),
                         {'1': 'old', '2': 'new', '3': 'third'})

    def test_conflicting_language_id_is_rejected(self):
        with self.assertRaises(ValueError):
            merge_three_way({}, {'2': 'a'}, {'2': 'b'})

    def test_disjoint_list_leaves_merge(self):
        self.assertEqual(merge_three_way([1, 2], [3, 2], [1, 4]), [3, 4])

    def test_action_insertions_are_not_guessed(self):
        with self.assertRaises(ValueError):
            merge_three_way([1], [1, 2], [3, 1])

    def test_identical_changes_are_not_duplicated(self):
        self.assertEqual(merge_three_way([1], [1, 2], [1, 2]), [1, 2])

    def test_delete_and_other_key_update(self):
        self.assertEqual(merge_three_way({'x': 1, 'y': 2}, {'x': 1}, {'x': 3, 'y': 2}), {'x': 3})

    def test_unfinished_repair_cannot_be_published(self):
        for note in ({'status': 'pending_api_verification'}, {'status': 'review_required'},
                     {'status': 'candidate', 'pending_review': ['missing damage logic']},
                     {'publishable': False}, {'severity': 'blocker'},
                     {'code': 'review_required', 'candidate_omitted': True}):
            self.assertEqual(publication_blockers([note], []), [note])

    def test_declared_module_dependency_is_required(self):
        note = {'status': 'delegated', 'required_modules': ['conditional']}
        self.assertEqual(publication_blockers([note], []), [note])
        self.assertEqual(publication_blockers([note], ['conditional']), [])

    def test_gameplay_limit_does_not_claim_offline_failure(self):
        note = {'status': 'limitation', 'explanation': 'Not engine verified'}
        self.assertEqual(publication_blockers([note], []), [])

    def test_language_index_is_part_of_protected_baseline(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ('attr.json', 'zhlanguage.json', 'tidindexinfo.json'):
                (root / name).write_text('{}', encoding='utf8')
            with patch.object(publish, 'MAP', root):
                names = {p.name for p in publish.map_files()}
            self.assertIn('tidindexinfo.json', names)


if __name__ == '__main__':
    unittest.main()
