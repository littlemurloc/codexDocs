"""Bounded native-AST protocol tests. Mover timing/closure capture are fixtures."""
from copy import deepcopy as cp
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import y3_sunshangxiang_loop_fix as fix

spec = importlib.util.spec_from_file_location('ssx_base_vm', ROOT / 'tests/test_y3_hero_repair_p2_state.py')
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)
Entity = base.Entity


class VM(base.VM):
    def __init__(self, doc, owner=None, core=None):
        super().__init__(doc, owner=owner, current=core)
        self.scheduled, self.events, self.chases = [], [], []
        self.event_target = None
        self.skill.kv['伤害系数'] = 1.25

    def ev(self, node):
        s, a = node['sub_type'], node['args_list']
        if s == 'CREATE_PROJECTILE_GOURP' or s == 'NONE_UNIT_GROUP':
            return []
        if s == 'UNIT_ENTITY_POINT':
            return self.require(self.ev(a[0]), 'unit')  # Position fixture only.
        if s == 'CREATE_PROJECTILE_NEW':
            return Entity('projectile', source=self.ev(a[2]))
        if s == 'UNIT_HAS_TAG':
            return self.ev(a[1]) in self.require(self.ev(a[0]), 'unit').tags
        if s == 'GET_NEW_TIMER_KV':
            return self.require(self.ev(a[0])).kv[self.ev(a[1])]
        if s == 'GET_TIMER_REMAINING_TIME':
            timer = self.require(self.ev(a[0]), 'timer')
            return max(0, timer.due - self.now)
        if s == 'DAMAGE_TARGET_UNIT':
            assert self.context == 'hurt'
            return self.event_target
        if s == 'DAMAGE_ABILITY' and self.context == 'hurt':
            return self.event_skill
        if s == 'GET_CUS_EVENT_PARAM':
            key = self.ev(a[0])
            if key == '阶段编号':
                return self.global_values['当前游戏进程阶段']
            if key == '目标单位':
                return self.event_target
        return super().ev(node)

    def cond(self, node):
        k, a = node['condition_type'], node['args_list']
        if k == 'TYPE_IS_EXIST':
            assert a[0]['arg_type'] in (100004, 100006, 100014, 100076, 100077, 100181)
            obj = self.ev(a[0])
            return isinstance(obj, Entity) and obj.valid
        if k == 'BOOL_NOT':
            return not self.ev(a[0])
        if k == 'NOT':
            return not all([self.cond(c) for c in a[0]['args_list']])
        if k == 'UNIT_IN_GROUP':
            return self.ev(a[0]) in self.ev(a[1])
        if k == 'GET_IS_NORMAL_HIT_FROM_EVENT':
            return self.context == 'hurt'
        return super().cond(node)

    def schedule(self, delay, actions, period=0):
        t = Entity('timer')
        t.due, t.actions, t.period = self.now + delay, actions, period
        # Preserve entity handles, unlike deepcopy's value copies.
        t.env, t.context = dict(self.local), self.context
        t.core, t.owner = self.current, self.owner
        self.scheduled.append(t)
        return t

    def run(self, actions):
        for node in actions:
            if isinstance(node, int):
                super().run([node])
                continue
            if node.get('enable') is False:
                continue
            k, a = node['action_type'], node['args_list']
            if k == 'RUN_LOOP_TIMER':
                assert self.ev(a[2]) is False
                t = self.schedule(self.ev(a[1]), a[3]['args_list'], self.ev(a[1]))
                self.assign(a[0], t)
            elif k == 'RUN_ONCE_TIMER':
                self.assign(a[0], self.schedule(self.ev(a[1]), a[2]['args_list']))
            elif k == 'RUN_ONCE_TIMER_NO_SAVE':
                self.schedule(self.ev(a[0]), a[1]['args_list'])
            elif k == 'DELETE_TIMER':
                self.require(self.ev(a[0]), 'timer').valid = False
            elif k == 'GROUP_ADD_PROJECTILE':
                self.ev(a[1]).append(self.require(self.ev(a[0]), 'projectile'))
            elif k == 'GROUP_ADD_UNIT':
                self.ev(a[1]).append(self.require(self.ev(a[0]), 'unit'))
            elif k == 'PROJECTILE_DELETE':
                self.require(self.ev(a[0]), 'projectile').valid = False
            elif k == 'CREATE_CHASING_MOVER':
                projectile, target = self.ev(a[0]), self.ev(a[1])
                self.chases.append((projectile, target))
                self.schedule(0.1, a[5]['args_list'])  # Explicit visual-arrival fixture.
            elif k == 'SEND_CUSTOM_EVENT':
                self.events.append([self.ev(v) for v in a])
            else:
                super().run([node])

    def advance(self, until):
        while True:
            pending = [t for t in self.scheduled if t.valid and t.due <= until + 1e-9]
            if not pending:
                break
            t = min(pending, key=lambda t: t.due)
            self.now = t.due
            if t.period:
                t.due += t.period
            else:
                t.valid = False
            old = self.current, self.owner, self.context, self.local
            self.current, self.owner, self.context, self.local = t.core, t.owner, t.context, dict(t.env)
            self.run(t.actions)
            self.current, self.owner, self.context, self.local = old
        self.now = until


class LoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = {}
        for rel in (fix.CORE, 'ability/134219157.json', 'ability/134222169.json',
                    'ability/134219344.json', 'ability/134276381.json'):
            p = fix.pub.WORK / fix.PHASE / 'original' / rel
            cls.old[rel] = json.loads((p if p.exists() else fix.pub.MAP / rel).read_text('utf8'))
        cls.core_doc = fix.patch_core(cls.old[fix.CORE])
        cls.skills = {oid: fix.guard_skill(cls.old[f'ability/{oid}.json'], oid)
                      for oid in (134222169, 134219344, 134276381)}
        cls.four = fix.patch_four(cls.old['ability/134219157.json'])

    def core(self):
        core = Entity('buff', resource=134248740, maximum=4)
        vm = VM(cp(self.core_doc), core=core)
        vm.owner.modifiers.append(core)
        vm.dispatch(1485688834, 'obtain')
        vm.dispatch(938414084, 'phase')
        return vm

    def attack(self, vm, target):
        vm.event_target, vm.event_skill = target, None
        vm.dispatch(1878966277, 'hurt')

    def group(self, vm):
        return vm.current.kv['游剑-组']

    def skill(self, oid, core_vm):
        vm = VM(cp(self.skills[oid]), owner=core_vm.owner, core=core_vm.current)
        vm.skill.source = core_vm.owner
        vm.now = core_vm.now
        vm.skill.kv['伤害系数'] = {134222169: 0.9, 134219344: 1.25, 134276381: 1.1}[oid]
        vm.registered.add(1756393476)
        return vm

    def test_gain_and_dispatch_cooldown(self):
        vm = self.core()
        self.assertEqual((len(self.group(vm)), vm.current.stack), (3, 4))
        target = Entity(team=2, tags={'阵型队长'})
        self.attack(vm, target)
        self.assertEqual(vm.current.stack, 3)
        self.attack(vm, target)
        self.assertEqual(vm.current.stack, 3)
        vm.advance(1.49)
        self.attack(vm, target)
        self.assertEqual(vm.current.stack, 3)
        vm.advance(1.5)
        self.attack(vm, target)
        self.assertEqual(vm.current.stack, 2)

    def test_six_second_expiry_returns_once(self):
        vm = self.core()
        self.attack(vm, Entity(team=2))
        vm.advance(5.9)
        self.assertEqual(vm.current.stack, 3)
        vm.advance(6.2)
        self.assertEqual(vm.current.stack, 4)
        vm.advance(10)
        self.assertEqual(vm.current.stack, 4)

    def test_real_and_pseudo_target_death_return(self):
        for pseudo in (False, True):
            vm = self.core()
            target = Entity(team=2)
            self.attack(vm, target)
            if pseudo:
                target.tags.add('已死亡')
            else:
                target.alive = False
            vm.advance(0.2)
            self.assertEqual(vm.current.stack, 4)

    def test_three_star_damages_without_recall(self):
        core = self.core()
        target = Entity(team=2)
        self.attack(core, target)
        vm = self.skill(134222169, core)
        vm.dispatch(893440004, 'spell')
        vm.advance(1)
        self.assertEqual([v for _, v in vm.hits], [90])
        self.assertEqual(self.group(core)[0].kv['目标单位'], target)
        self.assertEqual(core.current.stack, 3)

    def test_five_star_recalls_before_damage_and_cancels_expiries(self):
        core = self.core()
        target = Entity(team=2, tags={'阵型队长'})
        for t in (0, 1.5, 3):
            core.advance(t)
            self.attack(core, target)
        self.assertEqual(core.current.stack, 1)
        vm = self.skill(134219344, core)
        vm.dispatch(893440004, 'spell')
        self.assertEqual(core.current.stack, 4)
        self.assertTrue(all(p.kv['目标单位'] is core.owner for p in self.group(core)))
        vm.advance(4)
        self.assertEqual(sum(v for _, v in vm.hits), 375)
        core.advance(10)
        self.assertEqual(core.current.stack, 4)

    def test_four_star_uses_event_unit_without_attack_ability_once_per_target(self):
        core = self.core()
        target = Entity(team=2)
        self.attack(core, target)
        core.advance(1.5)
        self.attack(core, target)
        vm = VM(cp(self.four), owner=core.owner, core=core.current)
        vm.event_unit, vm.event_target, vm.event_skill = core.owner, target, None
        vm.registered.add(1756393476)
        vm.dispatch(1756393476, 'custom')
        vm.dispatch(1756393476, 'custom')
        self.assertEqual(len(vm.created), 1)

    def test_six_star_split_once_and_no_recall(self):
        core = self.core()
        a, b = Entity(team=2), Entity(team=2)
        for t, target in ((0, a), (1.5, a), (3, b)):
            core.advance(t)
            self.attack(core, target)
        vm = self.skill(134276381, core)
        vm.event_unit, vm.event_skill = core.owner, None
        vm.dispatch(1756393476, 'custom')
        vm.dispatch(1756393476, 'custom')
        vm.advance(4)
        self.assertAlmostEqual(sum(v for _, v in vm.hits), 330)
        self.assertEqual(core.current.stack, 1)

    def test_loss_cancels_timers_and_cleans_projectiles(self):
        vm = self.core()
        self.attack(vm, Entity(team=2))
        swords = list(self.group(vm))
        vm.dispatch(594665475, 'loss')
        vm.current.valid = False
        vm.advance(10)
        self.assertTrue(all(not p.valid for p in swords))
        self.assertFalse(any(t.valid and t.kind == 'timer' and t.period for t in vm.scheduled))

    def test_phase_reset_does_not_add_more_swords(self):
        vm = self.core()
        self.attack(vm, Entity(team=2))
        for _ in range(5):
            vm.dispatch(938414084, 'phase')
        self.assertEqual((len(self.group(vm)), vm.current.stack), (3, 4))

    def test_old_expiry_cannot_return_a_redeployed_sword(self):
        vm = self.core()
        first, second = Entity(team=2), Entity(team=2)
        self.attack(vm, first)
        first.alive = False
        vm.advance(0.2)
        vm.advance(1.5)
        self.attack(vm, second)
        vm.advance(6.2)
        self.assertEqual(vm.current.stack, 3)
        self.assertIs(self.group(vm)[0].kv['目标单位'], second)
        vm.advance(7.7)
        self.assertEqual(vm.current.stack, 4)

    def test_five_star_does_not_relax_same_target_gate(self):
        core = self.core()
        a, b = Entity(team=2, tags={'阵型队长'}), Entity(team=2, tags={'阵型队长'})
        for t, target in ((0, a), (1.5, a), (3, b)):
            core.advance(t)
            self.attack(core, target)
        vm = self.skill(134219344, core)
        vm.dispatch(893440004, 'spell')
        vm.advance(4)
        self.assertEqual(vm.hits, [])
        self.assertEqual(core.current.stack, 1)

    def test_owner_pseudo_death_suppresses_dispatch_and_clears_active_count(self):
        core = self.core()
        core.owner.tags.add('已死亡')
        self.attack(core, Entity(team=2))
        self.assertEqual(core.chases, [])
        core.advance(0.2)
        self.assertEqual(core.current.stack, 1)

    def test_native_templates_and_level_payloads_preserved(self):
        for oid in (134219157, 134222169, 134219344, 134276381):
            rel = f'ability/{oid}.json'
            new = self.four if oid == 134219157 else self.skills[oid]
            self.assertEqual(self.old[rel]['trigger_dict']['26066946'], new['trigger_dict']['26066946'])
        # The creator's resource and enabled options are unchanged.
        original = next(n for n in fix.walk(self.old[fix.CORE])
                        if n.get('element_id') == 1485688834000621)
        created = [n for n in fix.active_walk(self.core_doc)
                   if n.get('action_type') == 'SET_VARIABLE'
                   and len(n.get('args_list', [])) > 1
                   and n['args_list'][1].get('sub_type') == 'CREATE_PROJECTILE_NEW']
        self.assertEqual(len(created), 3)
        self.assertTrue(all(n['args_list'] == original['args_list'] for n in created))
        old_delete = next(n for n in fix.walk(self.old[fix.CORE])
                          if n.get('element_id') == 1485688834000495)
        new_delete = next(n for n in fix.active_walk(self.core_doc)
                          if n.get('action_type') == 'PROJECTILE_DELETE')
        self.assertEqual(old_delete['op_arg'], new_delete['op_arg'])
        self.assertEqual(old_delete['op_arg_enable'], new_delete['op_arg_enable'])

    def test_old_five_and_six_star_damage_does_not_cross_loop_rebuild(self):
        for oid in (134219344, 134276381):
            core = self.core()
            a, b = Entity(team=2, tags={'阵型队长'}), Entity(team=2, tags={'阵型队长'})
            targets = [a, a, a] if oid == 134219344 else [a, a, b]
            for t, target in zip((0, 1.5, 3), targets):
                core.advance(t)
                self.attack(core, target)
            vm = self.skill(oid, core)
            vm.event_unit, vm.event_skill = core.owner, None
            vm.dispatch(893440004 if oid == 134219344 else 1756393476,
                        'spell' if oid == 134219344 else 'custom')
            core.current.valid = False
            core.owner.modifiers.append(Entity('buff', resource=134248740, maximum=4))
            vm.advance(4)
            self.assertEqual(vm.hits, [])

    def test_four_star_record_resets_with_new_loop_instance(self):
        core = self.core()
        target = Entity(team=2)
        self.attack(core, target)
        core.advance(1.5)
        self.attack(core, target)
        vm = VM(cp(self.four), owner=core.owner, core=core.current)
        vm.event_unit, vm.event_target, vm.event_skill = core.owner, target, None
        vm.registered.add(1756393476)
        vm.dispatch(1756393476, 'custom')
        core.current.valid = False
        new = Entity('buff', resource=134248740,
                     kv={'游剑-组': [Entity('projectile', kv={'目标单位': target}) for _ in range(2)]})
        core.owner.modifiers.append(new)
        vm.dispatch(1756393476, 'custom')
        self.assertEqual(len(vm.created), 2)


if __name__ == '__main__':
    unittest.main()
