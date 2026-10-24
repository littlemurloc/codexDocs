"""Native AST checks with bounded auto-command fixtures, not engine gameplay."""
from copy import deepcopy
from dataclasses import dataclass, field
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import y3_taishi_autocast_fix as fix


@dataclass(eq=False)
class Entity:
    alive: bool = True
    valid: bool = True
    team: int = 1
    hp: float = 100
    maximum: float = 100
    tags: set = field(default_factory=set)
    buffs: dict = field(default_factory=dict)
    source: object = None


class VM:
    def __init__(self, doc):
        self.doc = doc
        self.owner = Entity(tags={'仆从伙伴'})
        self.skill = Entity()
        self.phase, self.cd, self.auto, self.allowed = 2, 0, True, True
        self.group, self.commands = [], []
        self.vars = {('UNIT_GROUP', '搜索组', 'actor'): [],
                     ('UNIT_ENTITY', '目标单位', 'actor'): None}
        self.selected = None

    def reference(self, node):
        return tuple(node['args_list'][0]['items'])

    def ev(self, node):
        s, a = node['sub_type'], node.get('args_list', [])
        if a and isinstance(a[0], dict) and a[0].get('__tuple__'):
            items = a[0]['items']
            if items[:2] == ['INTEGER', '当前游戏进程阶段']:
                return self.phase
            if items[:2] == ['STRING', '当前关卡模式']:
                return 'PVE'
            return self.vars.get(tuple(items))
        if s == 1:
            return a[0] if a else None
        if s == 'CUR_ABILITY':
            return self.skill
        if s == 'ABILITY_OWNER':
            return self.owner
        if s == 'FOR_EACH_SELECTED_UNIT':
            return self.selected
        if s == 'NONE_UNIT':
            return None
        if s == 'ABILITY_CD_LEFT_TIME':
            return self.cd
        if s == 'GET_BOOLEAN_KV':
            return self.auto
        if s == 'UNIT_HAS_TAG':
            return self.ev(a[1]) in self.ev(a[0]).tags
        if s == fix.STATE:
            return self.allowed  # Explicit fixture, not an implementation of the helper.
        if s == fix.TEAM:
            return self.group  # Borrowed reference fixture, not proven engine copy semantics.
        if s == 'UNIT_LIST_IN_SHAPE':
            return self.group  # Fixture for the unchanged native spatial selector.
        if s == 'GET_LAST_MODIFIER_INSTANCE':
            return self.ev(a[0]).buffs.get(self.ev(a[1]))
        if s == 'GET_BUFF_SOURCE':
            buff = self.ev(a[0])
            assert buff is not None and buff.valid, 'invalid Buff source read'
            return buff.source
        if s == 'GET_HP_CUR':
            return self.ev(a[0]).hp
        if s == 'GET_UNIT_ATTR':
            assert self.ev(a[2]) == 'hp_max'
            return self.ev(a[0]).maximum
        if s == 'ARITHMETIC_OPERATION':
            assert self.ev(a[1]) == '*'
            return self.ev(a[0]) * self.ev(a[2])
        if s == 'UNIT_COMMAND_USE_SKILL':
            assert node['op_arg_enable'] == [False, False, True, False, False]
            return self.ev(node['op_arg'][2])
        raise AssertionError(('unimplemented expression', s))

    def cond(self, node):
        k, a = node['condition_type'], node['args_list']
        if k == 'TYPE_IS_EXIST':
            obj = self.ev(a[0])
            return isinstance(obj, Entity) and obj.valid
        if k == 'IS_UNIT_ALIVE':
            return self.ev(a[0]).alive
        if k == 'BOOL_NOT':
            return not self.ev(a[0])
        if k == 'IS_ENEMY':
            return self.ev(a[0]).team != self.ev(a[1]).team
        if k == 'UNIT_HAS_TAG':
            return self.ev(a[1]) in self.ev(a[0]).tags
        if k == 'OR':
            values = [self.cond(c) for c in a[0]['args_list']]
            return any(values)
        if k == 'UNIT_HAS_MODIFIER':
            return self.ev(a[1]) in self.ev(a[0]).buffs
        if k in ('FLOAT_COMPARE', 'BOOL_COMPARE', 'UNIT_COMPARE'):
            left, op, right = map(self.ev, a)
            if op == '==':
                return left == right
            if op == '!=':
                return left != right
            if op == '<=':
                return left <= right
            if op == '<':
                return left < right
            raise AssertionError(op)
        raise AssertionError(('unimplemented condition', k))

    def run(self, actions):
        for node in actions:
            if node.get('enable') is False:
                continue
            k, a = node['action_type'], node['args_list']
            if k == 'IF_THEN_ELSE':
                checks = [self.cond(c) for c in a[0]['args_list']]
                self.run(a[1 if all(checks) else 2]['args_list'])
            elif k == 'SET_VARIABLE':
                self.vars[self.reference(a[0])] = self.ev(a[1])
            elif k == 'CLEAR_GROUP':
                self.ev(a[0]).clear()
            elif k == 'PICK_UNIT_DO_ACTION':
                for obj in list(self.ev(a[0])):
                    self.selected = obj
                    if self.run(a[1]['args_list']) == 'break':
                        break
            elif k == 'UNIT_RELEASE_COMMAND':
                self.commands.append(self.ev(a[1]))
            elif k == 'BREAK_LOOP':
                return 'break'
            else:
                raise AssertionError(('unimplemented action', k))

    def tick(self):
        gain = self.doc['trigger_dict']['1959489540']
        for kind, values in gain['var_data'][0].items():
            for name, default in values.items():
                self.vars[(kind, name, 'local')] = default
        timer = fix.one(gain['action'], 'RUN_LOOP_TIMER')
        self.run(timer['args_list'][3]['args_list'])

    def target(self, hp=80, source=None):
        obj = Entity(team=2, hp=hp, tags={'阵型队长'})
        obj.buffs[134274015] = Entity(source=source or self.owner)
        self.group.append(obj)
        return obj


class AutoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old, cls.new = {}, {}
        for oid in fix.IDS:
            rel = f'ability/{oid}.json'
            p = fix.pub.WORK / fix.PHASE / 'original' / rel
            cls.old[oid] = json.loads((p if p.exists() else fix.pub.MAP / rel).read_text('utf8'))
            cls.new[oid] = fix.patch(cls.old[oid], oid)

    def test_read_only_team_cache(self):
        for oid in fix.IDS[1:]:
            old, new = VM(self.old[oid]), VM(self.new[oid])
            for vm in (old, new):
                vm.target()
                vm.vars[('UNIT_GROUP', '搜索组', 'actor')] = vm.group
                vm.run(vm.doc['trigger_dict']['82759685']['action'])
            self.assertEqual(len(old.group), 0)
            self.assertEqual(len(new.group), 1)

    def test_three_star_marked_target_casts_and_refreshes_each_tick(self):
        vm = VM(self.new[fix.IDS[1]])
        first = vm.target()
        vm.tick()
        second = Entity(team=2, buffs={134274015: Entity(source=vm.owner)})
        vm.group = [second]
        vm.tick()
        self.assertEqual(vm.commands, [first, second])

    def test_first_star_reselects_alive_target_without_stale_cache(self):
        vm = VM(self.new[fix.IDS[0]])
        vm.vars[('UNIT_ENTITY', '目标单位', 'actor')] = Entity(team=2, hp=1, alive=False)
        first, second = vm.target(80), vm.target(30)
        vm.tick()
        self.assertEqual(vm.commands, [second])
        first.tags.add('已死亡')
        second.tags.add('已死亡')
        vm.tick()
        self.assertEqual(vm.commands, [second])
        self.assertIsNone(vm.vars[('UNIT_ENTITY', '目标单位', 'actor')])

    def test_five_star_keeps_half_hp_gate(self):
        for hp, expected in [(51, 0), (50, 1), (39, 1)]:
            vm = VM(self.new[fix.IDS[2]])
            vm.target(hp)
            vm.tick()
            self.assertEqual(len(vm.commands), expected)

    def test_missing_foreign_or_invalid_letter_skips(self):
        for oid in fix.IDS[1:]:
            for state in ('missing', 'foreign', 'invalid'):
                vm = VM(self.new[oid])
                target = vm.target(30)
                if state == 'missing':
                    target.buffs.clear()
                elif state == 'foreign':
                    target.buffs[134274015].source = Entity()
                else:
                    target.buffs[134274015].valid = False
                vm.tick()
                self.assertEqual(vm.commands, [])

    def test_owner_and_target_pseudo_death_are_rejected(self):
        for oid in fix.IDS[1:]:
            for role in ('owner', 'target'):
                vm = VM(self.new[oid])
                target = vm.target(30)
                (vm.owner if role == 'owner' else target).tags.add('已死亡')
                vm.tick()
                self.assertEqual(vm.commands, [])

    def test_cooldown_stage_auto_and_action_gate(self):
        for oid in fix.IDS[1:]:
            for attr, value in [('cd', 2), ('phase', 1), ('auto', False), ('allowed', False)]:
                vm = VM(self.new[oid])
                vm.target(30)
                setattr(vm, attr, value)
                vm.tick()
                self.assertEqual(vm.commands, [])

    def test_stale_target_cleared_when_no_valid_letter(self):
        vm = VM(self.new[fix.IDS[1]])
        vm.vars[('UNIT_ENTITY', '目标单位', 'actor')] = Entity(team=2)
        vm.tick()
        self.assertIsNone(vm.vars[('UNIT_ENTITY', '目标单位', 'actor')])

    def test_spell_and_level_payloads_unchanged_and_no_group_mutators(self):
        for oid in fix.IDS:
            for tid in ('893440004', '26066946'):
                self.assertEqual(self.old[oid]['trigger_dict'][tid], self.new[oid]['trigger_dict'][tid])
            self.assertFalse(any(n.get('action_type') == 'CLEAR_GROUP' for n in fix.walk(self.new[oid])))
            self.assertTrue(all(t['valid'] for t in self.new[oid]['trigger_dict'].values()))


if __name__ == '__main__':
    unittest.main()
