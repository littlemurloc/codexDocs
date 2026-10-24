"""Strict AST projections; timer snapshots are test inputs, not engine proof."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from tools import y3_sunshangxiang_orbit_fix as p

ROOT = Path('D:/littl/testTempFile/ProjectMonster02/maps/map3')
BASELINE = Path(__file__).resolve().parents[1] / 'tmp/hero-repair-20261020/ssx-orbit-20261021/original' / p.FILE


class Entity:
    def __init__(self, kind, *, alive=True, enemy=False, kv=None):
        self.kind, self.alive, self.enemy = kind, alive, enemy
        self.exists, self.kv = True, kv or {}


class Projection:
    def __init__(self):
        self.owner = Entity('unit', kv={'自动施法': True})
        self.skill = Entity('ability', kv={'伤害系数': .9})
        self.group = []
        self.core = Entity('modifier', kv={'游剑-组': self.group})
        self.selected, self.variables = None, {}
        self.wave, self.phase = 1, 2
        self.scheduled, self.hits, self.sfx = [], [], []
        self.commands = 0

    def readable(self, obj):
        if not isinstance(obj, Entity) or not obj.exists:
            raise AssertionError('invalid entity dereference')
        return obj

    def value(self, n):
        s, a = n['sub_type'], n['args_list']
        if s == 1:
            if len(a) != 1: raise AssertionError('not a primitive')
            return a[0]
        if s in (2, 6, 11, 19):
            key = tuple(a[0]['items'])
            if key == ('INTEGER', p.WAVE): return self.wave
            if key == ('INTEGER', p.PHASE): return self.phase
            return self.variables.get(key)
        if s == 'CUR_ABILITY': return self.skill
        if s == 'ABILITY_OWNER': return self.owner
        if s == 'GET_ABILITY_OWNER':
            self.readable(self.value(a[0])); return self.owner
        if s == 'NONE_UNIT': return None
        if s == 'GET_LAST_MODIFIER_INSTANCE':
            self.readable(self.value(a[0])); return self.core
        if s in ('GET_PROJECTILE_GROUP_KV', 'GET_UNIT_ENTITY_KV', 'GET_BOOLEAN_KV', 'GET_FLOAT_KV'):
            return self.readable(self.value(a[0])).kv[self.value(a[1])]
        if s == 'UNIT_HAS_TAG':
            obj = self.readable(self.value(a[0]))
            return self.value(a[1]) == '已死亡' and not obj.alive
        if s == 'FOR_EACH_SELECTED_PROJECTILE': return self.selected
        if s == 'PROJECTILE_ENTITY_POINT':
            obj = self.readable(self.value(a[0]));return obj.kv['point']
        if s == 'ABILITY_CD_LEFT_TIME':
            self.readable(self.value(a[0])); return 0
        if s == '97642c3d802a5935a73289745a266ac8':
            self.readable(self.value(a[0])); return True
        if s == 'GET_UNIT_ATTR':
            self.readable(self.value(a[0])); return 100
        if s == 'ARITHMETIC_OPERATION':
            left, op, right = (self.value(x) for x in a)
            if op != '*': raise AssertionError(op)
            return left * right
        if s == 'INT_PLUS_ONE': return self.value(a[0]) + 1
        if s == 'RANDOM_FLOAT': return .25
        raise AssertionError(('unsupported expression', s))

    def condition(self, n):
        kind, a = n['condition_type'], n['args_list']
        if kind == 'TYPE_IS_EXIST':
            obj = self.value(a[0])
            return obj is not None and (not isinstance(obj, Entity) or obj.exists)
        if kind == 'HAS_KV_ANY': return self.value(a[1]) in self.readable(self.value(a[0])).kv
        if kind == 'IS_UNIT_ALIVE': return self.readable(self.value(a[0])).alive
        if kind == 'IS_ENEMY':
            target, source = (self.readable(self.value(x)) for x in a)
            return target.enemy != source.enemy
        if kind == 'BOOL_NOT': return not self.value(a[0])
        if kind in ('FLOAT_COMPARE', 'BOOL_COMPARE', 'UNIT_COMPARE', 'MODIFIER_COMPARE'):
            left, op, right = (self.value(x) for x in a)
            return {'==': lambda: left == right, '!=': lambda: left != right,
                    '<': lambda: left < right}[op]()
        raise AssertionError(('unsupported condition', kind))

    def run(self, actions):
        for n in actions:
            if n.get('enable') is False: continue
            kind, a = n['action_type'], n['args_list']
            if kind == 'IF_THEN_ELSE':
                checks = [self.condition(c) for c in a[0]['args_list'] if c.get('enable') is not False]
                self.run(a[1 if all(checks) else 2]['args_list'])
            elif kind == 'SET_VARIABLE':
                self.variables[tuple(a[0]['args_list'][0]['items'])] = self.value(a[1])
            elif kind == 'PICK_PROJECTILE_DO_ACTION':
                for obj in list(self.value(a[0])):
                    self.selected = obj
                    try: self.run(a[1]['args_list'])
                    except StopIteration: break
                self.selected = None
            elif kind == 'BREAK_LOOP': raise StopIteration
            elif kind == 'UNIT_RELEASE_COMMAND': self.commands += 1
            elif kind == 'PLAY_ANIMATION': pass
            elif kind == 'RUN_ONCE_TIMER_NO_SAVE':
                # Explicit per-cast capture assumption; structural assertions
                # independently ban all projectile-context reads after delay.
                self.scheduled.append((a[1]['args_list'], self.variables.copy()))
            elif kind == 'CREATE_SFX_ON_POINT_NEW': self.sfx.append(self.value(a[1]))
            elif kind == 'APPLY_DAMAGE':
                self.hits.append((self.readable(self.value(a[2])), self.value(a[4])))
            else: raise AssertionError(('unsupported action', kind))

    def callbacks(self):
        for actions, variables in self.scheduled:
            self.variables = variables
            self.run(actions)

    def sword(self, target, point):
        sword = Entity('projectile', kv={'目标单位': target, 'point': point})
        self.group.append(sword)
        return sword


class OrbitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = json.loads((BASELINE if BASELINE.exists() else ROOT / p.FILE).read_text('utf8'))
        cls.fixed = p.patch(cls.old)
        cls.auto = p.one(cls.fixed['trigger_dict'][p.GAIN]['action'], 'RUN_LOOP_TIMER')['args_list'][3]['args_list']
        cls.cast = cls.fixed['trigger_dict'][p.CAST]['action']

    def test_old_auto_faults_without_core(self):
        f = Projection(); f.core = None
        old = p.one(self.old['trigger_dict'][p.GAIN]['action'], 'RUN_LOOP_TIMER')['args_list'][3]['args_list']
        with self.assertRaises(AssertionError): f.run(old)

    def test_auto_missing_skill_owner_core_or_group_skips(self):
        for fault in ('skill', 'owner', 'core', 'group', 'dead', 'phase'):
            f = Projection()
            if fault in ('skill', 'owner'): getattr(f, fault).exists = False
            if fault == 'core': f.core = None
            if fault == 'group': f.core.kv.clear()
            if fault == 'dead': f.owner.alive = False
            if fault == 'phase': f.phase = 1
            f.run(self.auto); self.assertEqual(f.commands, 0, fault)

    def test_auto_filters_invalid_blades_and_stale_target(self):
        f = Projection(); target = Entity('unit', enemy=True)
        stale = ('UNIT_ENTITY', '目标单位', 'actor'); f.variables[stale] = target
        invalid = f.sword(target, (0, 0, 0)); invalid.exists = False
        f.group.append(Entity('projectile'))
        f.sword(Entity('unit', alive=False, enemy=True), (1, 0, 0))
        f.sword(f.owner, (2, 0, 0))
        f.run(self.auto); self.assertEqual(f.commands, 0); self.assertIsNone(f.variables[stale])
        f.sword(target, (3, 0, 0)); f.run(self.auto)
        self.assertEqual(f.commands, 1); self.assertIs(f.variables[stale], target)

    def test_three_delays_keep_distinct_targets_and_points(self):
        f = Projection(); targets = [Entity('unit', enemy=True) for _ in range(3)]
        swords = [f.sword(t, (i, 0, 0)) for i, t in enumerate(targets)]
        f.run(self.cast); self.assertEqual(len(f.scheduled), 3)
        for sword in swords: sword.exists = False; sword.kv.clear()
        f.callbacks()
        self.assertEqual(f.hits, [(target, 90) for target in targets])
        self.assertEqual(f.sfx, [(i, 0, 0) for i in range(3)])

    def test_delayed_damage_rejects_death_loss_new_core_and_wave(self):
        for fault in ('source-dead', 'source-gone', 'target-dead', 'skill-gone', 'core-gone', 'core-new', 'wave', 'phase'):
            f = Projection(); target = Entity('unit', enemy=True); f.sword(target, (1, 2, 3))
            f.run(self.cast)
            if fault == 'source-dead': f.owner.alive = False
            if fault == 'source-gone': f.owner.exists = False
            if fault == 'target-dead': target.alive = False
            if fault == 'skill-gone': f.skill.exists = False
            if fault == 'core-gone': f.core.exists = False; f.core = None
            if fault == 'core-new': f.core = Entity('modifier')
            if fault == 'wave': f.wave += 1
            if fault == 'phase': f.phase = 1
            f.callbacks(); self.assertEqual(f.hits, [], fault)

    def test_dead_cast_and_missing_core_do_not_schedule(self):
        for dead in (True, False):
            f = Projection()
            if dead: f.owner.alive = False
            else: f.core = None
            f.run(self.cast); self.assertEqual(f.scheduled, [])

    def test_timers_never_read_projectiles_or_loop_context(self):
        for n in p.walk(self.cast):
            if n.get('action_type') == 'RUN_ONCE_TIMER_NO_SAVE':
                nodes = list(p.walk(n['args_list'][1]))
                self.assertFalse(any(v.get('arg_type') in (100077, 100203) for v in nodes))
                self.assertFalse(any(v.get('sub_type') == 'ABILITY_OWNER' for v in nodes))

    def test_parameters_lifecycle_and_unknown_metadata_preserved(self):
        self.assertEqual(self.old['trigger_dict']['26066946'], self.fixed['trigger_dict']['26066946'])
        self.assertEqual(self.old['trigger_dict']['225054724'], self.fixed['trigger_dict']['225054724'])
        old_delay = p.one(self.old['trigger_dict'][p.CAST]['action'], 'RUN_ONCE_TIMER_NO_SAVE')
        old_sfx = p.one(old_delay, 'CREATE_SFX_ON_POINT_NEW')
        for n in p.walk(self.cast):
            if n.get('action_type') == 'RUN_ONCE_TIMER_NO_SAVE': self.assertEqual(n['args_list'][0], old_delay['args_list'][0])
            if n.get('action_type') == 'CREATE_SFX_ON_POINT_NEW':
                self.assertEqual(n['op_arg'], old_sfx['op_arg']); self.assertEqual(n['op_arg_enable'], old_sfx['op_arg_enable'])
        for data in self.fixed['local_variable'].values():
            for value in data['variable_dict'].get('POINT', {}).values():
                self.assertEqual(value, {'__tuple__': True, 'items': [0, 0, 0]})

    def test_input_not_mutated(self):
        original = deepcopy(self.old); p.patch(original); self.assertEqual(original, self.old)
