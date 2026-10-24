"""Bounded AST lifecycle checks, not a Y3 engine or UI renderer."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import y3_core_loop_reinit_fix as fix


class VM:
    def __init__(self, doc, *, pseudo_dead=False, alive=True, old_valid=True,
                 add_ok=True, unit_exists=True, table=True, maximum=4):
        self.doc = doc
        self.pseudo_dead, self.alive = pseudo_dead, alive
        self.unit = {'valid': unit_exists}
        self.old = {'valid': old_valid, 'maximum': maximum}
        self.maximum, self.add_ok = maximum, add_ok
        self.kv = {'能力循环机制': self.old, '循环机制面板': True}
        if table:
            self.kv['能量格数据表'] = [1, 2, 3]
        self.cells, self.removed, self.created = 3, 0, 0
        self.buff, self.selected = None, None
        self.matched = next(n for n in fix.walk(doc)
                            if n.get('element_id') == 1935909566000308)

    def valid(self, x):
        return isinstance(x, dict) and x.get('valid') is True

    def ev(self, n):
        s, a = n.get('sub_type'), n.get('args_list', [])
        if s == 11:
            return self.buff if n['arg_type'] == 100076 else self.unit
        if s == 1:
            return a[0] if a else None
        if s == 'GET_MODIFIER_ENTITY_KV':
            return self.kv.get(self.ev(a[1]))
        if s == 'UNIT_HAS_TAG':
            return self.pseudo_dead
        if s == 'ADD_MODIFIER':
            self.created += 1
            return {'valid': True, 'maximum': self.maximum} if self.add_ok else None
        raise AssertionError(('Unsupported expression', s))

    def cond(self, n):
        k, a = n['condition_type'], n['args_list']
        if k == 'TYPE_IS_EXIST':
            return self.valid(self.ev(a[0]))
        if k == 'HAS_KV_ANY':
            return self.ev(a[1]) in self.kv
        if k == 'IS_UNIT_ALIVE':
            return self.alive
        if k == 'BOOL_NOT':
            return not self.ev(a[0])
        raise AssertionError(('Unsupported condition', k))

    def run(self, actions):
        for n in actions:
            k, a = n['action_type'], n['args_list']
            if k == 'IF_THEN_ELSE':
                checks = [self.cond(c) for c in a[0]['args_list']]
                self.run(a[1 if all(checks) else 2]['args_list'])
            elif k == 'TRAVERSE_TABLE_NEW':
                # Projection: the unchanged native traversal deletes the saved cells.
                self.cells -= len(self.kv['能量格数据表'])
            elif k == 'CLEAR_TABLE':
                self.kv['能量格数据表'].clear()
            elif k == 'REMOVE_BUFF_INS':
                obj = self.ev(a[0])
                assert self.valid(obj), 'invalid old Buff removal'
                obj['valid'] = False
                self.removed += 1
            elif k == 'ITER_ABILITY_DO':
                # Fixture: exactly one held passive matches one loop table row.
                self.run(self.matched['args_list'][1]['args_list'])
            elif k == 'SET_VARIABLE':
                self.buff = self.ev(a[1])
            elif k == 'SET_ENTITY_KV':
                self.kv[self.ev(a[1])] = self.ev(a[2])
            elif k == 'FOR_INT_DO_ACTION_NEW':
                assert self.valid(self.buff), 'invalid new Buff maximum read'
                count = self.buff['maximum'] - 1
                self.cells += count
                self.kv['能量格数据表'] = list(range(count))
            elif k == 'SET_UI_COMP_TEXT':
                if n['element_id'] == 1935909566000305:
                    assert self.valid(self.buff), 'invalid new Buff name read'
            elif k in ('SET_UI_COMP_VISIBLE', 'BREAK_LOOP'):
                pass
            else:
                raise AssertionError(('Unsupported action', k))


class LifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original = fix.pub.WORK / fix.PHASE / 'original' / fix.FUNCTION
        cls.old = json.loads((original if original.exists() else fix.pub.MAP / fix.FUNCTION).read_text('utf8'))
        cls.new = fix.build(cls.old)

    def test_old_dead_path_rebuilds_without_clearing(self):
        old = VM(self.old, pseudo_dead=True, alive=False)
        old.run(self.old['action'])
        self.assertEqual(old.cells, 6)
        new = VM(self.new, pseudo_dead=True, alive=False)
        new.run(self.new['action'])
        self.assertEqual((new.cells, new.created), (0, 0))

    def test_pseudo_dead_but_engine_alive_does_not_rebuild(self):
        vm = VM(self.new, pseudo_dead=True, alive=True)
        vm.run(self.new['action'])
        self.assertEqual((vm.cells, vm.created), (0, 0))

    def test_invalid_old_buff_does_not_block_ui_cleanup(self):
        vm = VM(self.new, old_valid=False)
        vm.run(self.new['action'])
        self.assertEqual((vm.cells, vm.removed), (3, 0))

    def test_add_failure_does_not_read_new_buff(self):
        vm = VM(self.new, add_ok=False)
        vm.run(self.new['action'])
        self.assertEqual(vm.cells, 0)

    def test_repeat_retry_cycle_and_non_three_point_loop(self):
        for maximum in (2, 4, 6):
            vm = VM(self.new, maximum=maximum)
            for _ in range(5):
                vm.pseudo_dead = True
                vm.run(self.new['action'])
                self.assertEqual(vm.cells, 0)
                vm.pseudo_dead = False
                vm.run(self.new['action'])
                self.assertEqual(vm.cells, maximum - 1)

    def test_deleted_unit_no_operations(self):
        vm = VM(self.new, unit_exists=False)
        vm.run(self.new['action'])
        self.assertEqual((vm.cells, vm.removed, vm.created), (3, 0, 0))

    def test_native_creation_payload_unchanged(self):
        def find(doc, eid):
            return next(n for n in fix.walk(doc) if n.get('element_id') == eid)
        for eid in (1935909566000302, 1935909566000324, 1935909566000305):
            self.assertEqual(find(self.old, eid), find(self.new, eid))
        self.assertEqual(self.old['var_data'], self.new['var_data'])
        self.assertEqual(self.old['func_id'], self.new['func_id'])


if __name__ == '__main__':
    unittest.main()
