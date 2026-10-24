from copy import deepcopy
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import y3_skill_trace_manager as manager


class TraceRemovalTests(unittest.TestCase):
    def fixture(self):
        source = {'trigger_dict': {'1': {'event': [{'event_type': 'ABILITY_SP_END'}],
            'action': [{'action_type': 'APPLY_DAMAGE', 'element_id': 15, 'args_list': [1.5]}]}}}
        instrumented, logs = manager.instrument(source, 'hero', iter(range(100, 200)))
        return source, instrumented, logs

    def test_round_trip(self):
        source, instrumented, logs = self.fixture()
        self.assertEqual(manager.remove_registered(instrumented, logs), source)

    def test_preserves_later_manual_gameplay_edits(self):
        source, instrumented, logs = self.fixture()
        for node in manager.walk(instrumented):
            if node.get('element_id') == 15:
                node['args_list'] = [9.9]
        source['trigger_dict']['1']['action'][0]['args_list'] = [9.9]
        source['new_manual_field'] = 42
        instrumented['new_manual_field'] = 42
        self.assertEqual(manager.remove_registered(instrumented, logs), source)

    def test_rejects_reused_log_id(self):
        _, document, logs = self.fixture()
        document['trigger_dict']['1']['action'][0]['action_type'] = 'SET_VARIABLE'
        with self.assertRaisesRegex(AssertionError, 'Log ID reused'):
            manager.remove_registered(document, logs)

    def test_rejects_edited_log_text(self):
        _, document, logs = self.fixture()
        document['trigger_dict']['1']['action'][0]['args_list'][1]['args_list'] = ['manual text']
        with self.assertRaisesRegex(AssertionError, 'Log changed'):
            manager.remove_registered(document, logs)

    def test_rejects_missing_or_duplicate_nodes(self):
        _, document, logs = self.fixture()
        document['trigger_dict']['1']['action'].append(deepcopy(document['trigger_dict']['1']['action'][0]))
        with self.assertRaisesRegex(AssertionError, 'Expected one log node'):
            manager.remove_registered(document, logs)
        document['trigger_dict']['1']['action'] = []
        with self.assertRaisesRegex(AssertionError, 'Expected one log node'):
            manager.remove_registered(document, logs)

    def test_does_not_remove_other_native_logs(self):
        source, document, logs = self.fixture()
        other = manager.log_node(999, 'native user log')
        source['trigger_dict']['1']['action'].append(other)
        document['trigger_dict']['1']['action'].append(other)
        self.assertEqual(manager.remove_registered(document, logs), source)

    def test_discovery_uses_named_slots_and_reports_absent_eca(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            columns = ['单位名称', '单位类型'] + [f'技能{i}' for i in range(1, 9)]
            manager.save(root / 'tables/单位技能配置表.json', {'table_data': {'data': [
                columns, [], ['许褚', 99, 101, 103, 105, 134255698, 102, 104, 106, 134255698]]}})
            manager.save(root / 'tables/技能特有循环机制表.json', {'table_data': {'data': [
                ['key', '能力循环机制BUFF', '关联技能1', '关联技能2', '关联技能3'],
                [], [1, 201, 102, 0, 0]]}})
            for resource in (101, 103, 104, 105):
                manager.save(root / f'ability/{resource}.json', {'trigger_dict': {}})
            for resource in (102, 106):
                manager.save(root / f'editor_table/abilityall/{resource}.json', {})
            manager.save(root / 'modifier/201.json', {'trigger_dict': {}})
            specs, heroes, gaps = manager.discover(root)
            self.assertEqual(heroes, ['许褚'])
            self.assertEqual(len(specs), 5)
            self.assertEqual(specs['ability/103.json']['role'], '3星主动')
            self.assertEqual({g['role'] for g in gaps}, {'2星被动', '6星被动'})


if __name__ == '__main__':
    unittest.main()
