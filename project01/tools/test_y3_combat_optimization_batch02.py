"""Real-ECA differential tests; no claims about native engine performance."""
import collections
import copy
import itertools
import ast
import unittest
import y3_combat_optimization_batch02 as batch
import y3_recent_work_fixtures as fixtures


class VM:
    def __init__(self, source, target):
        self.vars = {'输出单位': source, '承受单位': target, 'result': False}
        self.reads = 0;self.result = None
    def ev(self, n):
        t, a = n['sub_type'], n['args_list']
        if t in (1, 2, 11, 'VARIABLE'):
            assert len(a) == 1
            if isinstance(a[0], dict) and a[0].get('__tuple__'):return self.vars[a[0]['items'][1]]
            assert not isinstance(a[0], (dict, list))
            return a[0]
        if t == 'GET_UNIT_KEY_OF_UNIT':
            self.reads += 1;value = self.ev(a[0]);assert isinstance(value, int), 'Invalid unit'
            return value
        raise AssertionError(t)
    def cond(self, n):
        t, a = n['condition_type'], n['args_list']
        if t == 'OR':return any([self.cond(c) for c in a[0]['args_list']])
        assert t == 'UNIT_CLASS_COMPARE'
        x, op, y = [self.ev(c) for c in a];assert op == '=='
        return x == y
    def run(self, actions):
        for n in actions:
            if n.get('enable') is False:continue
            t, a = n['action_type'], n['args_list']
            if t == 'SET_VARIABLE':self.vars[a[0]['args_list'][0]['items'][1]] = self.ev(a[1])
            elif t in ('STORAGE_BOX', 'IF_THEN_ELSE'):
                yes = all([self.cond(c) for c in a[0]['args_list']])
                self.run(a[1 if yes else 2]['args_list'])
            elif t == 400342:self.result = self.ev(a[0])
            else:raise AssertionError(t)


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = fixtures.manifest('combat-batch02')
        cls.old = fixtures.document('combat-batch02','before',batch.COUNTER)
        cls.new = fixtures.document('combat-batch02','staged',batch.COUNTER)
        cls.registry = batch.load(batch.REGISTRY)
        cls.inputs = 0
    def test_all_native_unit_type_pairs(self):
        types = {n['args_list'][0] for _, n in batch.walk(self.old)
                 if n.get('arg_type') == 100116 and n.get('sub_type') == 1}
        types |= {0, 999999, 134284000}
        for source, target in itertools.product(types, repeat=2):
            old, new = VM(source, target), VM(source, target)
            old.run(self.old['action']);new.run(self.new['action'])
            self.assertEqual(old.result, new.result)
            self.assertEqual(old.reads, 20);self.assertEqual(new.reads, 2)
            type(self).inputs += 1
    def test_original_return_and_identity_preserved(self):
        self.assertEqual(self.old['action'][-1], self.new['action'][-1])
        for k in ('func_id', 'func_param_list', 'trigger_id', 'func_rtv_name_list'):
            self.assertEqual(self.old[k], self.new[k])
    def test_invalid_units_are_not_accepted_by_the_model(self):
        for source, target in [(None, 0), (0, None)]:
            for doc in [self.old, self.new]:
                with self.assertRaisesRegex(AssertionError, 'Invalid unit'):VM(source, target).run(doc['action'])
    def test_type_cache_is_per_invocation(self):
        vm = VM(134270627, 134281982);vm.run(self.new['action']);self.assertTrue(vm.result)
        vm.vars.update(输出单位=134281982, 承受单位=134270627)
        vm.run(self.new['action']);self.assertFalse(vm.result)
    def test_no_cross_file_changes_outside_registered_flags(self):
        for row in self.manifest['entries']:
            if row['kind'] != 'trace':continue
            old = fixtures.document('combat-batch02','before',row['path'])
            new = fixtures.document('combat-batch02','staged',row['path'])
            self.assertEqual(batch.undo_logs(new, row['changes']), old)
    def test_exact_registry_nodes_disabled_and_other_prints_preserved(self):
        nodes = 0
        for row in self.manifest['entries']:
            if row['kind'] != 'trace':continue
            old = fixtures.document('combat-batch02','before',row['path']);new = fixtures.document('combat-batch02','staged',row['path'])
            logs = {v['element_id']: v for v in self.registry['entries'][row['path']]['logs']}
            prior = {n['element_id']: n for _, n in batch.walk(old) if 'element_id' in n}
            for _, n in batch.walk(new):
                if n.get('element_id') in logs:
                    self.assertIs(n['enable'], self.manifest['trace_enabled'])
                    self.assertEqual(n['args_list'][1]['args_list'], [logs[n['element_id']]['message']]);nodes += 1
                elif n.get('action_type') == 'PRINT_MESSAGE_ACTION_TO_DIALOG':
                    self.assertEqual(n, prior[n['element_id']])
        self.assertEqual(nodes, 1669)
    def test_switch_can_be_restored_without_regeneration(self):
        for row in self.manifest['entries']:
            if row['kind'] != 'trace':continue
            old = fixtures.document('combat-batch02','before',row['path']);new = fixtures.document('combat-batch02','staged',row['path'])
            on, _ = batch.toggle_logs(new, self.registry['entries'][row['path']]['logs'], True)
            self.assertEqual(old, on)
    def test_counter_scope_is_exactly_reversible(self):
        row = next(row for row in self.manifest['entries'] if row['kind'] == 'counter')
        self.assertEqual(batch.undo_counter(self.new, row['edits']), self.old)
    def test_no_added_gameplay_event_or_timer(self):
        for row in self.manifest['entries']:
            old = fixtures.document('combat-batch02','before',row['path']);new = fixtures.document('combat-batch02','staged',row['path'])
            def events(d):return [n for _, n in batch.walk(d) if 'event_type' in n]
            self.assertEqual(events(old), events(new))
    def test_local_native_unit_name_declarations(self):
        for name in batch.NAMES:
            self.assertEqual(self.new['var_data'][0]['UNIT_NAME'][name], 0)
            self.assertEqual(self.new['var_data'][2].count(name), 1)
        for identity in batch.IDS:
            self.assertEqual(sum(n.get('element_id') == identity for _, n in batch.walk(self.new)), 1)
    def test_maintained_trace_generator_honors_both_modes(self):
        path = batch.PROJECT / 'tools/y3_skill_trace_manager.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'tracing_enabled')
        class Mode:
            exists = lambda self: True
        for enabled in [False, True]:
            scope = {'TRACE_MODE': Mode(), 'read': lambda p: {'schema':1,'enabled':enabled}}
            exec(compile(ast.Module(body=[fn],type_ignores=[]), str(path),'exec'),scope)
            self.assertIs(scope['tracing_enabled'](), enabled)
        class Missing:
            exists = lambda self: False
        scope = {'TRACE_MODE': Missing()}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),str(path),'exec'),scope)
        self.assertIs(scope['tracing_enabled'](), True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
