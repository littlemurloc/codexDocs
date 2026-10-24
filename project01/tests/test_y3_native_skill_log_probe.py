import importlib.util
from pathlib import Path
import unittest


path = Path(__file__).resolve().parents[1] / 'tools/y3_native_skill_log_probe.py'
spec = importlib.util.spec_from_file_location('native_probe', path)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class NativeLogTests(unittest.TestCase):
    def test_only_literal_log_actions_are_added(self):
        source = {'trigger_dict': {'10': {'enabled': False,
            'event': [{'event_type': 'SPECIAL_UNIT_EVENT'}], 'condition': ['unchanged'],
            'action': [{'action_type': 'IF_THEN_ELSE', 'element_id': 1,
                'args_list': [{'arg_type': 100022, 'args_list': [
                    {'action_type': 'APPLY_DAMAGE', 'element_id': 2, 'args_list': ['exact']},
                    {'action_type': 'ADD_MODIFIER', 'element_id': 3, 'enable': False,
                     'args_list': ['disabled']}]}]}]}}}
        result, added = probe.instrument(source, 'test', iter(range(100, 200)))
        ids = {v['element_id'] for v in added}
        self.assertEqual(probe.strip_logs(result, ids), source)
        self.assertEqual(len(added), 3)
        for node in probe.walk(result):
            if node.get('element_id') in ids:
                self.assertEqual(node['action_type'], 'PRINT_MESSAGE_ACTION_TO_DIALOG')
                self.assertEqual(node['args_list'][0],
                                 {'arg_type': 100175, 'sub_type': 1, 'args_list': [3]})
                self.assertEqual(node['args_list'][1]['sub_type'], 1)
                self.assertIsInstance(node['args_list'][1]['args_list'][0], str)

    def test_lifecycle_and_layer_entry_labels(self):
        for event, phase in probe.EVENTS.items():
            source = {'trigger_dict': {'1': {'event': [{'event_type': event}], 'action': []}}}
            result, added = probe.instrument(source, 'test', iter([100]))
            self.assertEqual(len(added), 1)
            self.assertIn(phase, added[0]['message'])
            self.assertEqual(probe.strip_logs(result, {100}), source)

    def test_pure_timer_work_is_not_logged_on_every_tick(self):
        source = {'trigger_dict': {'1': {'event': [], 'action': [
            {'action_type': 'RUN_LOOP_TIMER', 'element_id': 1, 'args_list': [
                {'arg_type': 100022, 'args_list': [
                    {'action_type': 'SET_VARIABLE', 'element_id': 2, 'args_list': []}]}]}]}}}
        result, added = probe.instrument(source, 'test', iter([100]))
        self.assertEqual(added, [])
        self.assertEqual(result, source)


if __name__ == '__main__':
    unittest.main()
