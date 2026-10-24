"""Limited ECA interpreter: passive direction and asynchronous projectile boundaries."""
from copy import deepcopy as cp
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import y3_hero_runtime_followup_r7_20261024 as fix


def entity(kind, **kw):
    return dict(kind=kind, exists=True, alive=True, dead=False, kv={}, **kw)


class Model:
    """Only supports the inspected projectile payload, not a Y3 engine simulation."""
    def __init__(self):
        self.core = entity('buff')
        self.owner = entity('unit', attrs={'attack_phy': 100})
        self.target = entity('unit', attrs={})
        self.skill = entity('ability')
        self.skill['kv'].update(援射系数=1.2, 张郃齐射系数=1.1, 小兵齐射系数=1.0)
        self.owner['buff'] = self.core
        self.actor = {fix.SKILL: self.skill, fix.OWNER: self.owner, '目标单位': self.target}
        self.local = {}
        self.phase, self.wave = 2, 3
        self.projectile = None
        self.created, self.damage, self.effects, self.logs = [], [], [], []
        self.deleted = 0

    def ev(self, x):
        sub, args = x['sub_type'], x.get('args_list', [])
        if sub in (1, 2, 6, 11, 14, 'VARIABLE'):
            if args and isinstance(args[0], dict) and args[0].get('__tuple__'):
                tag = args[0]['items']
                if len(tag) == 2:
                    return {'当前游戏进程阶段': self.phase, '当前进程所在波次编号': self.wave}[tag[1]]
                return (self.actor if tag[2] == 'actor' else self.local)[tag[1]]
            return args[0] if args else None
        if sub == 'CUR_ABILITY': return self.skill
        if sub == 'ABILITY_OWNER': return self.owner
        if sub == 'GET_MOVER_OWNER_PROJECTILE': return self.projectile
        if sub == 'PROJECTILE_OWNER': return self.valid(self.ev(args[0]))['owner']
        if sub == 'GET_LAST_MODIFIER_INSTANCE': return self.valid(self.ev(args[0])).get('buff')
        if sub in ('GET_UNIT_ENTITY_KV', 'GET_MODIFIER_ENTITY_KV', 'GET_INTEGER_KV', 'GET_FLOAT_KV'):
            return self.valid(self.ev(args[0]))['kv'].get(self.ev(args[1]))
        if sub in ('UNIT_ENTITY_POINT', 'PROJECTILE_ENTITY_POINT'):
            return ('point', id(self.valid(self.ev(args[0]))))
        if sub == 'GET_UNIT_ATTR': return self.valid(self.ev(args[0]))['attrs'][self.ev(args[2])]
        if sub == 'ARITHMETIC_OPERATION':
            a, op, b = map(self.ev, args)
            assert op == '*'
            return a * b
        if sub == 'UNIT_HAS_TAG': return self.valid(self.ev(args[0]))['dead']
        if sub == 'GET_ABILITY_RELEASE_DIRECTION':
            raise ValueError('Passive has no cast-direction context')
        if sub == 'CREATE_PROJECTILE_NEW':
            for value, enabled in zip(x.get('op_arg', []), x.get('op_arg_enable', [])):
                if enabled: self.ev(value)
            self.ev(args[1])
            p = entity('projectile', owner=self.valid(self.ev(args[2])))
            self.created.append(p)
            return p
        raise AssertionError(('Unmodeled expression', sub))

    @staticmethod
    def valid(value):
        if not isinstance(value, dict) or not value.get('exists'):
            raise ValueError('Invalid entity dereference')
        return value

    def check(self, n):
        k, a = n['condition_type'], n['args_list']
        if k == 'TYPE_IS_EXIST':
            value = self.ev(a[0])
            return isinstance(value, dict) and value.get('exists', False)
        if k == 'HAS_KV_ANY': return self.ev(a[1]) in self.valid(self.ev(a[0]))['kv']
        if k == 'IS_UNIT_ALIVE': return self.valid(self.ev(a[0]))['alive']
        if k == 'BOOL_NOT': return not self.ev(a[0])
        if k == 'IS_ENEMY': return self.ev(a[0]) is not self.ev(a[1])
        if k in ('FLOAT_COMPARE', 'MODIFIER_COMPARE'):
            left, op, right = map(self.ev, a)
            assert op == '=='
            return left is right if k == 'MODIFIER_COMPARE' else left == right
        raise AssertionError(('Unmodeled condition', k))

    def run(self, actions):
        for n in actions:
            if n.get('enable') is False: continue
            k, a = n['action_type'], n['args_list']
            if k == 'IF_THEN_ELSE':
                # Eager AND deliberately rejects unsafe same-level dereferences.
                checks = [self.check(c) for c in a[0]['args_list'] if c.get('enable') is not False]
                self.run(a[1 if all(checks) else 2]['args_list'])
            elif k == 'PRINT_MESSAGE_ACTION_TO_DIALOG': self.logs.append(self.ev(a[1]))
            elif k == 'SET_VARIABLE':
                tag = a[0]['args_list'][0]['items']
                (self.actor if tag[2] == 'actor' else self.local)[tag[1]] = self.ev(a[1])
            elif k == 'SET_ENTITY_KV': self.valid(self.ev(a[0]))['kv'][self.ev(a[1])] = self.ev(a[2])
            elif k == 'SET_PROJECTILE_DURATION': self.valid(self.ev(a[0]))['duration'] = self.ev(a[1])
            elif k == 'CREATE_SFX_ON_POINT_NEW': self.effects.append(self.ev(a[1]))
            elif k == 'APPLY_DAMAGE':
                self.valid(self.ev(a[0])); self.valid(self.ev(a[1]))
                self.damage.append((self.valid(self.ev(a[2])), self.ev(a[4])))
            elif k == 'PROJECTILE_DELETE':
                self.valid(self.ev(a[0]))['exists'] = False
                self.deleted += 1
            else: raise AssertionError(('Unmodeled action', k))

    def shot(self, target=None, shooter=None):
        self.projectile = entity('projectile', owner=shooter or self.owner)
        self.projectile['kv'] = {fix.TARGET: target or self.target, fix.CORE: self.core, fix.WAVE: self.wave}
        self.local['projectile'] = self.projectile
        return self.projectile


class FollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = {p: fix.base.trace.read(fix.WORK / 'map3-before' / p) for p in fix.FILES}
        cls.new = fix.build(fix.WORK / 'map3-before')

    def movers(self, doc):
        return [n for n in fix.base.walk(doc) if n.get('action_type') == 'CREATE_CHASING_MOVER']

    def callbacks(self):
        return [m['args_list'][5]['args_list'] for d in self.new.values() for m in self.movers(d)]

    def test_old_passive_direction_warning_reproduced(self):
        for d in self.old.values():
            creates = [n for n in fix.base.walk(d) if n.get('sub_type') == 'CREATE_PROJECTILE_NEW']
            for n in creates:
                with self.assertRaisesRegex(ValueError, 'cast-direction'):
                    Model().ev(n)

    def test_new_creation_has_no_passive_cast_direction_read(self):
        for d in self.new.values():
            creates = [n for n in fix.base.walk(d) if n.get('sub_type') == 'CREATE_PROJECTILE_NEW']
            self.assertEqual(len(creates), 2)
            for n in creates:
                if any(x.get('sub_type') == 'FOR_EACH_SELECTED_UNIT' for x in fix.base.walk(n)): continue
                m = Model(); self.assertTrue(m.ev(n)['exists'])
                self.assertEqual(n['op_arg_enable'][:2], [False, True])

    def test_old_hit_loses_target_when_actor_is_reassigned(self):
        old = self.movers(self.old[fix.FILES[0]])[0]['args_list'][5]['args_list']
        m = Model(); m.shot(); m.actor['目标单位'] = None
        with self.assertRaisesRegex(ValueError, 'Invalid entity'):
            m.run(old)

    def test_new_hit_uses_projectile_target_not_mutable_actor(self):
        for hit in self.callbacks():
            m = Model(); target = m.target; m.shot(); m.actor['目标单位'] = None
            m.run(hit)
            self.assertEqual(len(m.damage), 1)
            self.assertIs(m.damage[0][0], target)
            self.assertEqual(m.deleted, 1)

    def test_positive_hit_keeps_hero_and_soldier_damage_formulas(self):
        expected = [120, 120, 110, 50]
        for i, hit in enumerate(self.callbacks()):
            m = Model()
            source = entity('unit', attrs={'attack_phy': 50}) if i == 3 else m.owner
            m.shot(shooter=source); m.run(hit)
            self.assertAlmostEqual(m.damage[0][1], expected[i])

    def test_two_overlapping_shots_keep_their_own_targets(self):
        for hit in self.callbacks():
            m = Model(); one = m.shot(); second = entity('unit', attrs={})
            two = m.shot(second); m.actor['目标单位'] = second
            for p in (one, two): m.projectile = p; m.run(hit)
            self.assertIs(m.damage[0][0], m.target)
            self.assertIs(m.damage[1][0], second)
            self.assertEqual(m.deleted, 2)

    def test_invalid_target_skips_effects_but_cleans_projectile(self):
        for state in ('missing', 'native_dead', 'fake_dead'):
            for hit in self.callbacks():
                m = Model(); m.shot()
                if state == 'missing': m.target['exists'] = False
                elif state == 'native_dead': m.target['alive'] = False
                else: m.target['dead'] = True
                m.run(hit)
                self.assertEqual((m.damage, m.effects, m.deleted), ([], [], 1))

    def test_wave_and_core_and_skill_boundaries(self):
        for state in ('phase', 'wave', 'replaced_core', 'removed_core', 'skill', 'owner', 'owner_fake_dead'):
            for hit in self.callbacks():
                m = Model(); m.shot()
                if state == 'phase': m.phase = 1
                elif state == 'wave': m.wave += 1
                elif state == 'replaced_core': m.owner['buff'] = entity('buff')
                elif state == 'removed_core': m.core['exists'] = False
                elif state == 'skill': m.skill['exists'] = False
                elif state == 'owner': m.owner['exists'] = False
                else: m.owner['dead'] = True
                m.run(hit)
                self.assertEqual((m.damage, m.effects, m.deleted), ([], [], 1), state)

    def test_dead_soldier_and_already_removed_projectile(self):
        for hit in self.callbacks():
            m = Model(); soldier = entity('unit', attrs={'attack_phy': 50}); m.shot(shooter=soldier)
            soldier['alive'] = False; m.run(hit)
            self.assertEqual((m.damage, m.deleted), ([], 1))
            m.run(hit)
            self.assertEqual(m.deleted, 1)

    def test_missing_snapshot_keys_skips_safely(self):
        for hit in self.callbacks():
            m = Model(); m.shot(); del m.projectile['kv'][fix.TARGET]
            m.run(hit); self.assertEqual((m.damage, m.deleted), ([], 1))

    def test_original_trace_nodes_and_gameplay_constants_preserved(self):
        registry = fix.base.trace.read(fix.base.trace.REGISTRY)['entries']
        for p, d in self.new.items():
            old = self.old[p]
            fix.base.trace.checked_nodes(d, registry[p]['logs'])
            for tid in ('26066946', '225054724'):
                self.assertEqual(d['trigger_dict'][tid], old['trigger_dict'][tid])
            for kind in ('APPLY_DAMAGE', 'SET_BUFF_STACK', 'ADD_MODIFIER'):
                original = {n['element_id']: n for n in fix.base.walk(old) if n.get('action_type') == kind}
                changed = {n['element_id']: n for n in fix.base.walk(d) if n.get('action_type') == kind}
                self.assertEqual(set(original), set(changed))
            for mover in self.movers(d):
                self.assertEqual(mover['args_list'][2:5], self.movers(old)[0]['args_list'][2:5])
                self.assertFalse(any(n.get('sub_type') == 'CUR_ABILITY' for n in fix.base.walk(mover)))

    def test_scoped_files_native_timeout_and_no_new_triggers(self):
        self.assertEqual(set(self.new), set(fix.FILES))
        for p, d in self.new.items():
            self.assertEqual(set(d['trigger_dict']), set(self.old[p]['trigger_dict']))
            timeouts = [n for n in fix.base.walk(d) if n.get('action_type') == 'SET_PROJECTILE_DURATION']
            self.assertEqual(len(timeouts), 2)
            expected = 8.0 if p == fix.FILES[0] else 4.0
            self.assertTrue(all(n['args_list'][1]['args_list'] == [expected] for n in timeouts))

    def test_callbacks_never_read_overwritten_target_or_local_projectile(self):
        for hit in self.callbacks():
            for n in fix.base.walk(hit):
                self.assertNotEqual(n, fix.actor('UNIT_ENTITY', '目标单位'))
                self.assertNotEqual(n.get('args_list'), [
                    {'__tuple__': True, 'items': ['PROJECTILE_ENTITY', 'projectile', 'local']}])

    def test_handang_interval_clock_remains_outside_combat_only_gate(self):
        d = self.new[fix.FILES[0]]
        timer = next(n for n in fix.base.walk(d) if n.get('action_type') == 'RUN_LOOP_TIMER')
        root = timer['args_list'][3]['args_list'][0]
        # Exists skill -> exists owner -> native alive/not-fake-dead -> old clock then combat block.
        body = root['args_list'][1]['args_list'][0]['args_list'][1]['args_list'][0]['args_list'][1]['args_list']
        self.assertEqual(len(body), 2)
        self.assertNotIn('当前游戏进程阶段', str(body[0]))
        self.assertIn('当前游戏进程阶段', str(body[1]['args_list'][0]))


if __name__ == '__main__':
    unittest.main()
