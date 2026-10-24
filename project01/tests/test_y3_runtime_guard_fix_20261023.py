"""Bounded AST tests; native event dispatch, visuals and attribute application are not simulated."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import y3_runtime_guard_fix_20261023 as fix

NATIVE_SOURCE = fix.WORK / 'map3-before'


class Unit:
    def __init__(self, *, dead=False, alive=True, team=1):
        self.valid = True
        self.dead = dead
        self.alive = alive
        self.team = team


class VM:
    def __init__(self):
        self.owner = Unit()
        self.skill = Unit()
        self.core = Unit()
        self.variables = {'当前游戏进程阶段': 2}
        self.effects = []
        self.callbacks = []
        self.table = {'带领兵种': 'text', '单位类型': 134245859}
        self.defaults = {134245859: 134270627}
        self.result = None
        self.invalidate_core_on_shield = False

    def require(self, unit):
        if unit is None or not unit.valid:
            raise ValueError('invalid object')
        return unit

    def expression(self, node):
        kind, args = node['sub_type'], node['args_list']
        if len(args) == 1 and isinstance(args[0], dict) and args[0].get('__tuple__'):
            return self.variables.get(args[0]['items'][1], 0)
        if kind == 1:
            return args[0] if args else None
        if kind == 'CUR_ABILITY':
            return self.skill
        if kind == 'ABILITY_OWNER':
            self.require(self.skill)
            return self.owner
        if kind == 'UNIT_HAS_TAG':
            return self.require(self.expression(args[0])).dead
        if kind == 'GET_LAST_MODIFIER_INSTANCE':
            self.require(self.expression(args[0]))
            return self.core if self.core is not None and self.core.valid else None
        if kind == 'NONE_UNIT_KEY':
            return 0
        if kind == 'd0dbae83ff4d5da48e8c5600cd8b37c1':
            return self.table
        if kind in ('GET_STRING_TABLE_VAR_ND', 'GET_UNIT_NAME_TABLE_VAR_ND'):
            return self.table[self.expression(args[2])]
        if kind == 'GET_UNIT_NAME_KV':
            return self.defaults[self.expression(args[0])]
        if kind == 'ANY_VAR_TO_STR':
            value = self.expression(args[0])
            assert not isinstance(value, Unit)
            return str(value)
        if kind == 'STR_JOIN':
            return ''.join(str(self.expression(a)) for a in args)
        raise AssertionError('Unmodeled expression: ' + str(kind))

    def condition(self, node):
        kind, args = node['condition_type'], node['args_list']
        if kind == 'TYPE_IS_EXIST':
            unit = self.expression(args[0])
            return isinstance(unit, Unit) and unit.valid
        if kind == 'IS_UNIT_ALIVE':
            return self.require(self.expression(args[0])).alive
        if kind == 'BOOL_NOT':
            return not self.expression(args[0])
        if kind == 'IS_ALLY':
            return self.require(self.expression(args[0])).team == self.require(self.expression(args[1])).team
        if kind in ('FLOAT_COMPARE', 'UNIT_CLASS_COMPARE', 'STRING_COMPARE'):
            left, operator, right = [self.expression(a) for a in args]
            return {'==': lambda: left == right, '!=': lambda: left != right,
                    '>': lambda: left > right}[operator]()
        raise AssertionError('Unmodeled condition: ' + kind)

    def run(self, actions):
        for node in actions:
            if node.get('enable') is False:
                continue
            kind, args = node['action_type'], node['args_list']
            if kind == 'IF_THEN_ELSE':
                # Eager evaluation deliberately does not invent AND short-circuiting.
                checks = [self.condition(c) for c in args[0]['args_list'] if c.get('enable') is not False]
                self.run(args[1 if all(checks) else 2]['args_list'])
            elif kind == 'SET_VARIABLE':
                self.variables[args[0]['args_list'][0]['items'][1]] = self.expression(args[1])
            elif kind == 'PRINT_MESSAGE_ACTION_TO_DIALOG':
                self.expression(args[1])
            elif kind == 400342:
                self.result = self.expression(args[0])
            elif kind == 'ADD_MODIFIER':
                self.require(self.expression(args[0])); self.effects.append('shield')
                if self.invalidate_core_on_shield:
                    self.core.valid = False
            elif kind == 'ADD_BUFF_STACK':
                self.require(self.expression(args[0])); self.effects.append('stack')
            elif kind == 'ADD_CUR_HP':
                self.require(self.expression(args[0])); self.effects.append('heal')
            elif kind == 'RUN_ONCE_TIMER_NO_SAVE':
                self.callbacks.append(next(a['args_list'] for a in args if a.get('arg_type') == 100022))
            else:
                raise AssertionError('Unmodeled action: ' + str(kind))


def zhuge_fixture():
    return {'local_variable': {'58232837': {'variable_dict': {}, 'variable_length_dict': {}}},
            'trigger_dict': {'58232837': {'condition': [], 'var_data': [{}, {}, []], 'action': [
                {'action_type': 'ADD_MODIFIER', 'element_id': 1,
                 'args_list': [fix.ex(100006, 'ABILITY_OWNER'), fix.lit(1)]},
                {'action_type': 'ADD_BUFF_STACK', 'element_id': 58232837974154,
                 'args_list': [fix.ex(100076, 'GET_LAST_MODIFIER_INSTANCE',
                                    fix.ex(100006, 'ABILITY_OWNER'), fix.lit(134267407)), fix.lit(1)]},
                {'action_type': 'RUN_ONCE_TIMER_NO_SAVE', 'element_id': 2,
                 'args_list': [fix.ex(100022, 1)]}]}}}


class GuardTests(unittest.TestCase):
    def test_reproduces_old_empty_core_error(self):
        vm = VM(); vm.core = None
        with self.assertRaisesRegex(ValueError, 'invalid object'):
            vm.run(zhuge_fixture()['trigger_dict']['58232837']['action'])

    def test_zhuge_blocks_removed_core_and_fake_death_and_preparation(self):
        document = fix.zhuge(zhuge_fixture())
        for condition in ('no_core', 'fake_dead', 'engine_dead', 'preparation', 'missing_skill', 'missing_owner'):
            vm = VM()
            if condition == 'no_core': vm.core = None
            if condition == 'fake_dead': vm.owner.dead = True
            if condition == 'engine_dead': vm.owner.alive = False
            if condition == 'preparation': vm.variables['当前游戏进程阶段'] = 1
            if condition == 'missing_skill': vm.skill = None
            if condition == 'missing_owner': vm.owner = None
            vm.run(document['trigger_dict']['58232837']['action'])
            self.assertEqual(vm.effects, [], condition)

    def test_zhuge_valid_cast_and_reentrant_core_removal(self):
        document = fix.zhuge(zhuge_fixture())
        vm = VM(); vm.run(document['trigger_dict']['58232837']['action'])
        self.assertEqual(vm.effects, ['shield', 'stack'])
        vm = VM(); vm.invalidate_core_on_shield = True
        vm.run(document['trigger_dict']['58232837']['action'])
        self.assertEqual(vm.effects, ['shield'])

    def test_heal_eligibility_distinguishes_fake_and_engine_death(self):
        b = fix.builder({'element_id': 1}, 9)
        unit = fix.ref('UNIT_ENTITY', '目标单位', 'actor')
        body = [b.node('ADD_CUR_HP', unit, fix.lit(1))]
        guard = fix.eligible(b, unit, body, owner=fix.ex(100006, 'ABILITY_OWNER'))
        for target, expected in [(Unit(), 1), (Unit(dead=True), 0),
                                 (Unit(alive=False), 0), (Unit(team=2), 0), (None, 0)]:
            vm = VM(); vm.variables['目标单位'] = target; vm.run([guard])
            self.assertEqual(len(vm.effects), expected)

    def test_star_clamp_keeps_valid_values_and_caps_18(self):
        for star in (0, 1, 12, 15, 18, 10000):
            doc = {'action': [{'action_type': 'SET_VARIABLE', 'element_id': 1115783868000144,
                    'args_list': [fix.ex(100030, 1, {'__tuple__': True,
                        'items': ['INTEGER', '当前星数', 'local']}), fix.lit(star)]}]}
            patched = fix.clamp_star(doc, 1115783868000144, 15, 4)
            vm = VM(); vm.run(patched['action'])
            self.assertEqual(vm.variables['当前星数'], min(star, 15))

    @unittest.skipUnless(NATIVE_SOURCE.is_dir(), 'Needs the pre-fix native snapshot')
    def test_native_minion_lookup_preserves_valid_choices_and_falls_back_for_text(self):
        source = fix.trace.read(NATIVE_SOURCE / fix.FILES[7])
        patched = fix.minion_type(source, 7)
        vm = VM(); vm.run(source['action']); self.assertEqual(vm.result, 0)
        expected = {'刀兵': 134270627, '弓兵': 134281982, '枪兵': 134278489,
                    '盾兵': 134236300, '骑兵': 134278285, 'text': 134270627, '': 134270627}
        for name, resource in expected.items():
            vm = VM(); vm.table['带领兵种'] = name; vm.run(patched['action'])
            self.assertEqual(vm.result, resource)

    @unittest.skipUnless(NATIVE_SOURCE.is_dir(), 'Needs the pre-fix native snapshot')
    def test_real_candidates_preserve_existing_trace_nodes_and_trigger_ids(self):
        candidates, maximum = fix.build(NATIVE_SOURCE)
        self.assertEqual(maximum, 15)
        registry = fix.trace.read(fix.trace.REGISTRY)
        for path, candidate in candidates.items():
            source = fix.trace.read(NATIVE_SOURCE / path)
            self.assertEqual(set(source.get('trigger_dict', {})), set(candidate.get('trigger_dict', {})))
            before = Counter(n['element_id'] for n in fix.walk(source) if 'element_id' in n)
            after = Counter(n['element_id'] for n in fix.walk(candidate) if 'element_id' in n)
            for key, count in after.items():
                self.assertLessEqual(count, max(1, before[key]), (path, key))
            if path in registry['entries']:
                fix.trace.checked_nodes(candidate, registry['entries'][path]['logs'])

    @unittest.skipUnless(NATIVE_SOURCE.is_dir(), 'Needs the pre-fix native snapshot')
    def test_null_minion_exits_before_traversal(self):
        source = fix.trace.read(NATIVE_SOURCE / fix.FILES[6])
        patched = fix.minion_star(source, 6)
        vm = VM(); vm.variables['赋值小兵'] = None
        vm.run(patched['action'])
        self.assertEqual(vm.effects, [])


if __name__ == '__main__':
    unittest.main()
