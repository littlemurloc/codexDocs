import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import y3_hero_repair_p1_guanyu_fixed as repair

MAP = Path('D:/littl/testTempFile/ProjectMonster02/maps/map3')


class CriticalModel:
    """Contract model of the documented pre -> engine -> BEFORE_APPLY order."""
    def __init__(self, resource=134284050, armed=1, paid=1, multiplier=3):
        self.ability = dict(resource=resource, 关羽本次强化=armed, 关羽本次已扣点=paid,
                            关羽强化倍率=multiplier)
        self.damage = 0
        self.critical = False

    def ev(self, node):
        typ, sub, args = node['arg_type'], node['sub_type'], node['args_list']
        if sub == 1:
            return args[0]
        if sub == 'DAMAGE_ABILITY':
            return self.ability
        if sub == 'ABILITY_NAME_OF_ABILITY':
            return self.ev(args[0])['resource']
        if sub == 'GET_FLOAT_KV':
            return self.ev(args[0])[self.ev(args[1])]
        if sub == 'HURT_DAMAGE':
            return self.damage
        if sub == 'ARITHMETIC_OPERATION':
            assert self.ev(args[1]) == '*'
            return self.ev(args[0]) * self.ev(args[2])
        raise AssertionError(('Unsupported expression', typ, sub))

    def check(self, node):
        typ, args = node['condition_type'], node['args_list']
        if typ == 'TYPE_IS_EXIST':
            return self.ev(args[0]) is not None
        if typ == 'OR':
            return any([self.check(c) for c in args[0]['args_list']])
        if typ in ('ABILITY_COMPARE', 'FLOAT_COMPARE'):
            a, op, b = map(self.ev, args)
            return a == b if op == '==' else a > b if op == '>' else self.fail(op)
        raise AssertionError(('Unsupported condition', typ))

    def run(self, actions):
        for node in actions:
            if not node.get('enable', True):
                continue
            kind, args = node['action_type'], node['args_list']
            if kind == 'IF_THEN_ELSE':
                checks = [self.check(c) for c in args[0]['args_list']]
                self.run(args[1 if all(checks) else 2]['args_list'])
            elif kind == 'SET_CUR_DAMAGE_IS_CRITICAL':
                self.critical = self.ev(args[0])
            elif kind == 'SET_CUR_DAMAGE':
                self.damage = self.ev(args[0])
            else:
                raise AssertionError(('Unsupported action', kind))

    def settle(self, document, base, critical_roll, critical_multiplier, mitigation):
        self.damage, self.critical = base, critical_roll
        self.run(document['trigger_dict'][str(repair.IDS[0])]['action'])
        self.damage *= (critical_multiplier if self.critical else 1) * mitigation
        self.run(document['trigger_dict'][str(repair.IDS[1])]['action'])
        return self.damage, self.critical


class GuanYuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = repair.load(MAP / repair.FILE)
        cls.fixed = repair.patch(cls.original)

    def test_no_request_amount_multiplier_is_published(self):
        payload, _ = repair.build(MAP)
        self.assertEqual(set(payload), {repair.FILE})
        self.assertFalse(any(n.get('action_type') == 'APPLY_DAMAGE' for _, n in repair.walk(self.fixed)))

    def test_empowered_every_hit_fixed_three_even_huge_native_critical(self):
        for resource in repair.ACTIVES:
            for roll in (False, True):
                for native in (1.5, 2, 3, 99):
                    for _ in range(5):
                        model = CriticalModel(resource)
                        self.assertEqual(model.settle(self.fixed, 100, roll, native, .7), (210, True))

    def test_unarmed_unpaid_other_ability_are_unchanged(self):
        for options in [dict(armed=0), dict(paid=0), dict(resource=134284051)]:
            model = CriticalModel(**options)
            self.assertEqual(model.settle(self.fixed, 100, True, 2, .7), (140, True))
            self.assertEqual(model.settle(self.fixed, 100, False, 2, .7), (70, False))

    def test_missing_event_ability_safe(self):
        model = CriticalModel()
        model.ability = None
        self.assertEqual(model.settle(self.fixed, 100, False, 2, 1), (100, False))

    def test_other_skill_has_no_guanyu_keys(self):
        model = CriticalModel()
        model.ability = {'resource': 999}
        self.assertEqual(model.settle(self.fixed, 100, False, 2, 1), (100, False))

    def test_registration_and_loss_cleanup_are_paired(self):
        gain = self.fixed['trigger_dict']['1959489540']
        loss = self.fixed['trigger_dict']['225054724']
        self.assertEqual(gain['action'][-2:], list(repair.IDS))
        self.assertEqual([a['action_type'] for a in loss['action'][:2]], ['UNREG_TRIGGER', 'UNREG_TRIGGER'])
        for tid in repair.IDS:
            trigger = self.fixed['trigger_dict'][str(tid)]
            self.assertFalse(trigger['enabled'])
            self.assertTrue(trigger['call_enabled'])
            self.assertEqual(trigger['p_trigger_id'], 1959489540)
            self.assertIn(str(tid), self.fixed['local_variable'])

    def test_old_trigger_payloads_retained(self):
        self.assertEqual(self.fixed['trigger_dict']['26066946'], self.original['trigger_dict']['26066946'])
        self.assertEqual(self.fixed['trigger_dict']['225054724']['action'][2:],
                         self.original['trigger_dict']['225054724']['action'])


if __name__ == '__main__':
    unittest.main()
