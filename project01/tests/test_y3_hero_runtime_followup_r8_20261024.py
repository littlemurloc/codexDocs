"""Bounded ECA regressions, not a native Y3 simulation or damage-number verdict."""
from copy import deepcopy as cp
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import y3_hero_runtime_followup_r8_20261024 as fix
from test_y3_hero_runtime_followup_r7_20261024 import Model as ProjectileModel, entity


class BreakLoop(Exception):
    pass


class Model(ProjectileModel):
    def __init__(self):
        super().__init__()
        self.owner.update(team=1, pos=0, hate=self.target)
        self.owner['kv']['自动施法'] = True
        self.target.update(team=2, pos=500)
        self.skill.update(cd=0, cast_range=700)
        self.skill['kv'].update(伤害系数=1.8, 炎种时长=5)
        self.actor.update({fix.SKILL: self.skill, fix.OWNER: self.owner, fix.LAST: -1,
                           'R8_扇火仇恨目标': None, 'R8_马超五星彩冲势': None})
        self.selected = None
        self.enemies = [self.target]
        self.commands, self.seeds = [], []
        self.allowed = True
        self.end_wave_on_damage = False
        self.kill_target_on_damage = False

    def ev(self, x):
        sub, a = x['sub_type'], x.get('args_list', [])
        if sub == 'GET_ABILITY_OWNER': self.valid(self.ev(a[0])); return self.owner
        if sub == 'NONE_UNIT': return None
        if sub == 'GET_BOOLEAN_KV': return self.valid(self.ev(a[0]))['kv'].get(self.ev(a[1]), False)
        if sub == 'GET_MOD_STACK': return self.valid(self.ev(a[0])).get('stack', 0)
        if sub == 'ABILITY_CD_LEFT_TIME': return self.valid(self.ev(a[0]))['cd']
        if sub == 'GET_ABILITY_FLOAT_ATTR':
            self.assert_field(a[1], 'ability_cast_range')
            return self.valid(self.ev(a[0]))['cast_range']
        if sub == '97642c3d802a5935a73289745a266ac8': self.valid(self.ev(a[0])); return self.allowed
        if sub == 'GET_UNIT_AI_BATTLE_TARGET_UNIT': return self.valid(self.ev(a[0])).get('hate')
        if sub == 'UNIT_ENTITY_POINT': return ('point', self.valid(self.ev(a[0]))['pos'])
        if sub == 'GET_POINTS_DIS': return abs(self.ev(a[0])[1] - self.ev(a[1])[1])
        if sub == 'CONST_CIRCULAR_SHAPE': return self.ev(a[0])
        if sub == 'UNIT_LIST_IN_SHAPE':
            enabled = x.get('op_arg_enable', [])
            assert enabled[0] is True and enabled[11] is True
            assert x['op_arg'][0]['sub_type'] == 'PLAYER_ENEMY'
            center, radius = self.ev(a[0])[1], self.ev(a[1])
            return [u for u in self.enemies if u['exists'] and u['alive']
                    and u['team'] != self.owner['team'] and abs(u['pos'] - center) <= radius]
        if sub == 'FOR_EACH_SELECTED_UNIT': return self.selected
        if sub == 'UNIT_HAS_TAG':
            unit, tag = self.valid(self.ev(a[0])), self.ev(a[1])
            return unit['dead'] if tag == '已死亡' else tag in unit.get('tags', [])
        if sub == 'UNIT_HAS_MODIFIER':
            return self.ev(a[1]) in self.valid(self.ev(a[0])).get('modifiers', set())
        if sub == 'ANY_VAR_TO_STR': return str(self.ev(a[0]))
        if sub == 'STR_JOIN':
            parts = [self.ev(v) for v in a]
            parts += [self.ev(v) for v, enabled in zip(x.get('op_arg', []), x.get('op_arg_enable', [])) if enabled]
            return ''.join(parts)
        return super().ev(x)

    @staticmethod
    def assert_field(expr, value):
        assert expr['args_list'] == [value]

    def check(self, n):
        k, a = n['condition_type'], n['args_list']
        if k == 'IS_ENEMY': return self.valid(self.ev(a[0]))['team'] != self.valid(self.ev(a[1]))['team']
        if k in ('FLOAT_COMPARE', 'UNIT_COMPARE', 'BOOL_COMPARE', 'MODIFIER_COMPARE'):
            left, op, right = map(self.ev, a)
            if k in ('UNIT_COMPARE', 'MODIFIER_COMPARE'):
                assert op in ['==', '!=']
                return (left is right) if op == '==' else (left is not right)
            if op == '==': return left == right
            if op == '!=': return left != right
            if op == '>=': return left >= right
            if op == '<=': return left <= right
            raise AssertionError(('Unmodeled comparison', op))
        if k == 'OR': return any([self.check(c) for c in a[0]['args_list'] if c.get('enable') is not False])
        if k == 'UNIT_HAS_TAG':
            return self.ev(dict(arg_type=100001, sub_type=k, args_list=a))
        return super().check(n)

    def run(self, actions):
        for n in actions:
            if n.get('enable') is False: continue
            k, a = n['action_type'], n['args_list']
            if k == 'PICK_UNIT_DO_ACTION':
                previous = self.selected
                try:
                    for self.selected in self.ev(a[0]):
                        try: self.run(a[1]['args_list'])
                        except BreakLoop: break
                finally: self.selected = previous
            elif k == 'BREAK_LOOP': raise BreakLoop
            elif k == 'UNIT_RELEASE_COMMAND':
                self.valid(self.ev(a[0])); self.commands.append(self.actor['目标单位'])
            elif k == 'ADD_MODIFIER':
                target = self.valid(self.ev(a[0]))
                for value, enabled in zip(n.get('op_arg', []), n.get('op_arg_enable', [])):
                    if enabled: self.ev(value)
                target.setdefault('modifiers', set()).add(self.ev(a[1]))
                self.seeds.append(target)
            else:
                super().run([n])
                if k == 'APPLY_DAMAGE':
                    if self.end_wave_on_damage: self.phase = 1
                    if self.kill_target_on_damage: self.target['alive'] = False

    def shot(self, had=True):
        self.projectile = entity('projectile', owner=self.owner)
        self.projectile['kv'] = {fix.TARGET: self.target, fix.CORE: self.core,
                                 fix.WAVE: self.wave, fix.HAD: had}
        self.local['projectile'] = self.projectile
        return self.projectile


class FollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = {p: fix.base.trace.read(fix.WORK / 'map3-before' / p) for p in fix.FILES}
        cls.new = fix.build(fix.WORK / 'map3-before')

    def hit(self, new=True):
        d = (self.new if new else self.old)[fix.FILES[0]]
        return fix.base.one(d, 'CREATE_CHASING_MOVER')['args_list'][5]['args_list']

    def search(self, new=True):
        d = (self.new if new else self.old)[fix.FILES[1]]
        return next(n for n in fix.base.walk(d) if n.get('element_id') == 1959489540000007)['args_list'][1]['args_list']

    def ma_gate(self, new=True):
        d = cp((self.new if new else self.old)[fix.FILES[2]])
        timer = fix.base.one(d['trigger_dict']['1959489540']['action'], 'RUN_LOOP_TIMER')
        ready = next(n for n in fix.base.walk(timer) if n.get('element_id') == 1959489540974074)
        # Test only the guard; target search and native command execution are outside this model.
        ready['args_list'][1]['args_list'] = [fix.base.trace.log_node(1, 'READY')]
        return timer['args_list'][3]['args_list']

    def test_old_flying_fire_target_dereference_reproduced(self):
        m = Model(); m.shot(); m.actor['目标单位'] = None
        with self.assertRaisesRegex(ValueError, 'Invalid entity'): m.run(self.hit(False))

    def test_flying_fire_lands_on_its_original_target(self):
        m = Model(); m.shot(); original = m.target; m.actor['目标单位'] = None
        m.run(self.hit())
        self.assertEqual(len(m.damage), 1); self.assertIs(m.damage[0][0], original)
        self.assertAlmostEqual(m.damage[0][1], 180)
        self.assertEqual(m.seeds, [original]); self.assertEqual(m.deleted, 1)

    def test_one_star_does_not_require_two_star_core(self):
        m = Model(); m.owner['buff'] = None; m.shot(had=False)
        del m.projectile['kv'][fix.CORE]
        m.run(self.hit()); self.assertEqual(len(m.damage), 1); self.assertEqual(m.deleted, 1)

    def test_flying_fire_stale_boundaries_and_cleanup(self):
        for state in ['phase', 'wave', 'target_removed', 'target_dead', 'target_fake_dead',
                      'owner_removed', 'owner_fake_dead', 'skill_removed', 'core_removed', 'core_replaced']:
            m = Model(); m.shot()
            if state == 'phase': m.phase = 1
            elif state == 'wave': m.wave += 1
            elif state == 'target_removed': m.target['exists'] = False
            elif state == 'target_dead': m.target['alive'] = False
            elif state == 'target_fake_dead': m.target['dead'] = True
            elif state == 'owner_removed': m.owner['exists'] = False
            elif state == 'owner_fake_dead': m.owner['dead'] = True
            elif state == 'skill_removed': m.skill['exists'] = False
            elif state == 'core_removed': m.core['exists'] = False
            else: m.owner['buff'] = entity('buff')
            m.run(self.hit())
            self.assertEqual((m.damage, m.seeds, m.effects, m.deleted), ([], [], [], 1), state)

    def test_damage_ending_wave_or_killing_target_cannot_add_seed(self):
        for state in ['end_wave_on_damage', 'kill_target_on_damage']:
            m = Model(); m.shot(); setattr(m, state, True)
            m.run(self.hit()); self.assertEqual(len(m.damage), 1)
            self.assertEqual(m.seeds, []); self.assertEqual(m.deleted, 1)

    def test_old_search_misses_ordinary_enemy_without_hero_tags(self):
        m = Model(); m.actor['目标单位'] = None
        m.run(self.search(False)); self.assertEqual(m.commands, [])

    def test_current_hate_target_is_preferred(self):
        m = Model(); m.actor['目标单位'] = None
        other = entity('unit', team=2, pos=200)
        m.enemies = [other, m.target]
        m.run(self.search()); self.assertEqual(len(m.commands), 1)
        self.assertIs(m.commands[0], m.target)

    def test_fallback_accepts_living_soldier_not_fake_dead_hero(self):
        m = Model(); m.owner['hate'] = None
        dead = entity('unit', team=2, pos=100); dead['dead'] = True
        m.enemies = [dead, m.target]
        m.run(self.search()); self.assertIs(m.commands[0], m.target)

    def test_out_of_range_does_not_reuse_last_target(self):
        m = Model(); m.target['pos'] = 900
        m.actor['目标单位'] = m.target
        m.run(self.search()); self.assertEqual(m.commands, [])
        self.assertIsNone(m.actor['目标单位'])
        self.assertTrue(any('范围内无合法目标' in s for s in m.logs))

    def test_friendly_hate_target_is_not_selected(self):
        m = Model(); m.owner['hate'] = entity('unit', team=1, pos=100)
        m.run(self.search()); self.assertIs(m.commands[0], m.target)

    def test_old_ma_chao_missing_core_warning_reproduced(self):
        m = Model(); m.owner['buff'] = None
        with self.assertRaisesRegex(ValueError, 'Invalid entity'): m.run(self.ma_gate(False))

    def test_ma_chao_missing_or_removed_core_safely_skips(self):
        for core in [None, entity('buff')]:
            if core: core['exists'] = False
            m = Model(); m.owner['buff'] = core
            m.run(self.ma_gate()); self.assertNotIn('READY', m.logs)

    def test_ma_chao_keeps_existing_three_layer_threshold(self):
        for layers, permitted in [(2, False), (3, True), (4, True)]:
            m = Model(); m.core['stack'] = layers
            m.run(self.ma_gate()); self.assertEqual('READY' in m.logs, permitted)

    def test_ma_chao_owner_native_fake_death_and_noncombat_skip(self):
        for state in ['removed', 'dead', 'fake_dead', 'phase', 'skill_removed']:
            m = Model(); m.core['stack'] = 3
            if state == 'removed': m.owner['exists'] = False
            elif state == 'dead': m.owner['alive'] = False
            elif state == 'fake_dead': m.owner['dead'] = True
            elif state == 'phase': m.phase = 1
            else: m.skill['exists'] = False
            m.run(self.ma_gate()); self.assertNotIn('READY', m.logs)

    def test_existing_effect_ids_traces_and_unrelated_phases_preserved(self):
        registry = fix.base.trace.read(fix.base.trace.REGISTRY)['entries']
        for p, d in self.new.items():
            fix.base.trace.checked_nodes(d, registry[p]['logs'])
            self.assertEqual(set(d['trigger_dict']), set(self.old[p]['trigger_dict']))
            for tid in ['26066946', '225054724']:
                self.assertEqual(d['trigger_dict'][tid], self.old[p]['trigger_dict'][tid])
        self.assertEqual(self.new[fix.FILES[1]]['trigger_dict']['893440004'],
                         self.old[fix.FILES[1]]['trigger_dict']['893440004'])
        self.assertEqual(self.new[fix.FILES[2]]['trigger_dict']['893440004'],
                         self.old[fix.FILES[2]]['trigger_dict']['893440004'])
        for p in fix.FILES:
            original = {n['element_id'] for n in fix.base.walk(self.old[p]) if n.get('action_type') == 'APPLY_DAMAGE'}
            changed = {n['element_id'] for n in fix.base.walk(self.new[p]) if n.get('action_type') == 'APPLY_DAMAGE'}
            self.assertEqual(original, changed)

    def test_range_and_configs_not_part_of_payload(self):
        self.assertEqual(set(self.new), set(fix.FILES))
        self.assertTrue(all(p.startswith('ability/') for p in self.new))


if __name__ == '__main__': unittest.main()
