"""Differential execution of the real original/candidate damage callback.

This bounded VM rejects unknown expressions and eager-evaluates conditions.
It checks equivalence and event operand counts, not native engine timing,
floating-point rounding details or the ordering of other event listeners.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import itertools
import random
import unittest

import y3_damage_context_optimization as patch


@dataclass
class Unit:
    kv: dict = field(default_factory=dict)
    tags: set = field(default_factory=set)
    attrs: dict = field(default_factory=dict)
    valid: bool = True


class VM:
    def __init__(self, trigger, source, target, normal, damage):
        self.vars = {name: value for group in trigger['var_data'][0].values()
                     for name, value in group.items()}
        self.source, self.target, self.normal = source, target, normal
        self.damage = damage
        self.reads = dict(source=0, target=0)
        self.damage_writes = []
        self.attribute_reads = []

    @staticmethod
    def require(unit):
        assert isinstance(unit, Unit) and unit.valid, 'Invalid unit dereferenced'
        return unit

    @staticmethod
    def reference(ref):
        if isinstance(ref, dict) and ref.get('__tuple__'):
            ref = ref['items']
        if isinstance(ref, list) and len(ref) == 3:
            kind, name, scope = ref
            assert kind in ('UNIT_ENTITY', 'INTEGER', 'FLOAT') and scope == 'local'
            return name
        return None

    def ev(self, node):
        typ, args = node['sub_type'], node['args_list']
        if typ in (1, 2, 6, 11, 'VARIABLE'):
            assert len(args) == 1
            ref = args[0]
            name = self.reference(ref)
            if name is not None:
                return self.vars[name]
            assert not isinstance(ref, (dict, list)), 'Expression hidden inside a constant'
            return ref
        if typ in ('DAMAGE_SOURCE_UNIT', 'DAMAGE_TARGET_UNIT'):
            key = 'source' if typ == 'DAMAGE_SOURCE_UNIT' else 'target'
            self.reads[key] += 1
            return getattr(self, key)
        if typ == 'NONE_UNIT':
            return None
        if typ == 'GET_IS_NORMAL_HIT_FROM_EVENT':
            return self.normal
        if typ == 'HURT_DAMAGE':
            return self.damage
        if typ in ('GET_INTEGER_KV', 'GET_UNIT_ENTITY_KV'):
            unit, key = self.require(self.ev(args[0])), self.ev(args[1])
            assert key in unit.kv, 'Absent KV dereferenced'
            return unit.kv[key]
        if typ == 'GET_UNIT_ATTR':
            unit = self.require(self.ev(args[0]))
            assert self.ev(args[1]) == 'ATTR_RESULT'
            attr = self.ev(args[2])
            self.attribute_reads.append(attr)
            return unit.attrs.get(attr, 0.0)
        if typ == 'ARITHMETIC_OPERATION':
            x, op, y = [self.ev(value) for value in args]
            if op == '+':
                return x + y
            if op == '*':
                return x * y
            if op == '/':
                return x / y
            raise AssertionError('Unsupported arithmetic: ' + op)
        if typ == 'FLOAT_FORMULA':
            assert self.ev(args[0]) == 'a+b+c+d+e'
            values = [self.ev(value) for value in args[1:]]
            assert len(values) == 5
            a, b, c, d, e = values
            return a + b + c + d + e
        if typ == 'ROUND_DEC':
            return round(self.ev(args[0]), self.ev(args[1]))
        raise AssertionError('Unhandled expression: ' + str(typ))

    def cond(self, node):
        typ, args = node['condition_type'], node['args_list']
        if typ == 'BOOL_NOT':
            return not self.ev(args[0])
        if typ == 'TYPE_IS_EXIST':
            unit = self.ev(args[0])
            return isinstance(unit, Unit) and unit.valid
        if typ == 'HAS_KV_ANY':
            return self.ev(args[1]) in self.require(self.ev(args[0])).kv
        if typ == 'UNIT_HAS_TAG':
            return self.ev(args[1]) in self.require(self.ev(args[0])).tags
        if typ == 'OR':
            return any([self.cond(child) for child in args[0]['args_list']
                        if child.get('enable') is not False])
        if typ == 'FLOAT_COMPARE':
            x, op, y = [self.ev(value) for value in args]
            assert op == '=='
            return x == y
        raise AssertionError('Unhandled condition: ' + str(typ))

    def run(self, actions):
        for node in actions:
            if node.get('enable') is False:
                continue
            typ, args = node['action_type'], node['args_list']
            if typ == 'SET_VARIABLE':
                ref = args[0]['args_list'][0]
                name = self.reference(ref)
                assert name is not None
                self.vars[name] = self.ev(args[1])
            elif typ in ('STORAGE_BOX', 'IF_THEN_ELSE'):
                verdict = all([self.cond(child) for child in args[0]['args_list']
                               if child.get('enable') is not False])
                self.run(args[1 if verdict else 2]['args_list'])
            elif typ == 'SET_CUR_DAMAGE':
                self.damage = self.ev(args[0])
                self.damage_writes.append(self.damage)
            else:
                raise AssertionError('Unhandled action: ' + str(typ))


class Equivalence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import y3_recent_work_fixtures as fixtures
        cls.manifest = fixtures.manifest('damage-context')
        cls.before = fixtures.document('damage-context','before',patch.REL)
        cls.after = fixtures.document('damage-context','staged',patch.REL)
        cls.old = cls.before['sub_trigger'][patch.TID]
        cls.new = cls.after['sub_trigger'][patch.TID]
        cls.attrs = {n['args_list'][2]['args_list'][0] for _, n in patch.walk(cls.old['action'], active=True)
                     if n.get('sub_type') == 'GET_UNIT_ATTR'}
        cls.case_count = 0

    def compare(self, source, target, normal=False, damage=123.45):
        pair = [VM(doc, source, target, normal, damage) for doc in (self.old, self.new)]
        for vm, doc in zip(pair, (self.old, self.new)):
            vm.run(doc['action'])
        old, new = pair
        self.assertEqual(old.damage_writes, new.damage_writes)
        self.assertEqual(old.attribute_reads, new.attribute_reads)
        for key in self.old['var_data'][0].get('FLOAT', {}):
            self.assertEqual(old.vars[key], new.vars[key])
        self.assertEqual(new.reads, dict(source=1, target=1))
        type(self).case_count += 1
        return old, new

    def source(self, seed=0):
        rng = random.Random(seed)
        return Unit(attrs={key: rng.uniform(-30, 90) for key in sorted(self.attrs)})

    def test_exact_inverse_preserves_every_unrelated_field(self):
        self.assertEqual(patch.restore(self.after, self.manifest['edits']), self.before)

    def test_exhaustive_self_and_captain_slots(self):
        slots = [None, -1, 0, *range(1, 11)]
        for own, captain, normal in itertools.product(slots, slots, [False, True]):
            hero = Unit(kv={} if captain is None else {'归属阵型编号': captain})
            target = Unit(kv={'所属英雄': hero}, tags={'吴国', '弓兵'})
            if own is not None:
                target.kv['归属阵型编号'] = own
            self.compare(self.source(), target, normal)

    def test_all_troop_and_camp_tag_intersections(self):
        tags = ['盾兵', '弓兵', '骑兵', '枪兵', '蜀国', '魏国', '吴国', '群雄']
        for mask in range(256):
            target = Unit(kv={'归属阵型编号': 2},
                          tags={tag for index, tag in enumerate(tags) if mask & (1 << index)})
            for normal in [False, True]:
                self.compare(self.source(mask), target, normal)

    def test_missing_and_invalid_captain_handle(self):
        for owner in [None, Unit(valid=False), Unit(), Unit(kv={'归属阵型编号': 8})]:
            for normal in [False, True]:
                self.compare(self.source(), Unit(kv={'所属英雄': owner}), normal)
        self.compare(self.source(), Unit())

    def test_random_attributes_zero_and_negative_damage(self):
        rng = random.Random(20261030)
        for index in range(500):
            target = Unit(kv={'归属阵型编号': rng.randrange(-1, 12)},
                          tags=set(rng.sample(['盾兵', '弓兵', '蜀国', '魏国', '吴国', '群雄'], 3)))
            self.compare(self.source(index), target, bool(index % 2),
                         rng.choice([0.0, -5.0, 1.0, 1e6, rng.uniform(1, 9999)]))

    def test_invalid_event_operands_are_not_silently_tolerated(self):
        for source, target in [(None, Unit()), (Unit(), None), (Unit(valid=False), Unit())]:
            for doc in [self.old, self.new]:
                vm = VM(doc, source, target, False, 100)
                with self.assertRaisesRegex(AssertionError, 'Invalid unit'):
                    vm.run(doc['action'])

    def test_event_reads_reduced_without_additional_attribute_reads(self):
        old, new = self.compare(self.source(), Unit(kv={'归属阵型编号': 1}, tags={'吴国', '弓兵'}))
        self.assertEqual(old.reads, dict(source=5, target=9))
        self.assertEqual(new.reads, dict(source=1, target=1))

    def test_event_subscription_and_final_damage_write_unchanged(self):
        for key in ['event', 'condition', 'enabled', 'call_enabled', 'trigger_id', 'p_trigger_id']:
            self.assertEqual(self.old[key], self.new[key])
        self.assertEqual(self.old['action'][-2:], self.new['action'][-2:])

    def test_each_callback_overwrites_context_for_a_different_hit(self):
        source1, source2 = self.source(1), self.source(2)
        targets = [Unit(kv={'归属阵型编号': 3}, tags={'魏国'}),
                   Unit(kv={'归属阵型编号': 7}, tags={'弓兵', '吴国'})]
        vm = VM(self.new, source1, targets[0], False, 100)
        vm.run(self.new['action'])
        vm.source, vm.target, vm.normal, vm.damage = source2, targets[1], True, 37
        vm.run(self.new['action'])
        original = VM(self.old, source2, targets[1], True, 37)
        original.run(self.old['action'])
        self.assertEqual(vm.damage_writes[-1], original.damage_writes[-1])
        self.assertIs(vm.vars[patch.SOURCE], source2)
        self.assertIs(vm.vars[patch.TARGET], targets[1])

    def test_new_native_nodes_and_local_references_are_well_formed(self):
        nodes = [node for _, node in patch.walk(self.after)]
        for identity in (patch.SECTION_ID, patch.SOURCE_ID, patch.TARGET_ID):
            self.assertEqual(sum(node.get('element_id') == identity for node in nodes), 1)
        section = self.new['action'][0]
        self.assertEqual([arg['arg_type'] for arg in section['args_list']],
                         [100021, 100022, 100022, 100003])
        for name in (patch.SOURCE, patch.TARGET):
            self.assertIn(name, self.new['var_data'][0]['UNIT_ENTITY'])
            self.assertEqual(self.new['var_data'][1][name], 0)
            self.assertEqual(self.new['var_data'][2].count(name), 1)

    def test_no_global_variable_timer_or_new_listener(self):
        self.assertEqual(self.after.keys(), self.before.keys())
        self.assertEqual(self.after['var_data'], self.before['var_data'])
        self.assertEqual(set(self.new['var_data'][1]) - set(self.old['var_data'][1]), {patch.SOURCE})
        for _, node in patch.walk(self.after['sub_trigger'][patch.TID]['action'][0]):
            if 'action_type' in node:
                self.assertIn(node['action_type'], ['STORAGE_BOX', 'SET_VARIABLE'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
