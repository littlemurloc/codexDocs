"""Restricted AST regression tests; these are not Y3 engine simulations."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import y3_hero_repair_p1_shared as repair

MAP = Path('D:/littl/testTempFile/ProjectMonster02/maps/map3')
BASELINE = Path(__file__).resolve().parents[1] / 'tmp/hero-repair-20261020/p1/original'


class BreakLoop(Exception):
    pass


class TeamModel:
    """Only operations used by this existing function; unknown API fails."""
    def __init__(self, mode, player):
        self.values = {'当前关卡模式': mode, '持有技能': None if player is None else {'owner': player},
                       '玩家队伍': {1: 'left', 2: 'player2'}, '敌人队伍': 'right',
                       'playersDetail': {1: 1, 2: 2},
                       'playerList': [1, 2], '己队伍': None, '敌队伍': None}
        self.picked = None
        self.returned = None

    def ev(self, x):
        typ, sub, args = x['arg_type'], x['sub_type'], x['args_list']
        if sub in (1, 2, 14, 'VARIABLE'):
            if args and isinstance(args[0], dict) and args[0].get('__tuple__'):
                value = self.values[args[0]['items'][1]]
                return value[self.ev(args[1])] if len(args) == 2 else value
            if args and isinstance(args[0], list) and len(args[0]) == 3:
                return self.values[args[0][1]]
            if sub == 1:
                return args[0]
        if sub == 'NONE_UNIT_GROUP':
            return None
        if sub == 'GET_ABILITY_OWNER':
            ability = self.ev(args[0])
            assert ability is not None, 'Invalid ability dereference'
            return ability['owner']
        if sub == 'OWNER_PLAYER':
            return self.ev(args[0])
        if sub == 'PICKED_PLAYER':
            return self.picked
        if sub == '9384d061198e11ef967be8c829c05699':
            return self.ev(args[0])
        raise AssertionError(('Unsupported expression', typ, sub))

    def check(self, x):
        args, typ = x['args_list'], x['condition_type']
        if typ == 'TYPE_IS_EXIST':
            assert args[0]['arg_type'] in (100014, 100006)
            return self.ev(args[0]) is not None
        if typ == 'STRING_COMPARE':
            assert self.ev(args[1]) == '=='
            return self.ev(args[0]) == self.ev(args[2])
        if typ == 'DICT_HAS_VALUE':
            values = self.ev(args[0])
            assert isinstance(values, dict), 'Only native array-dictionary values are modeled'
            return self.ev(args[1]) in values.values()
        if typ == 'PLAYERS_IS_ENEMY_RELATION':
            return (self.ev(args[0]) == 31) != (self.ev(args[1]) == 31)
        raise AssertionError(('Unsupported condition', typ))

    def run(self, actions):
        for node in actions:
            if not node.get('enable', True):
                continue
            kind, args = node['action_type'], node['args_list']
            if kind == 'SET_VARIABLE':
                raw = args[0]['args_list'][0]
                name = raw['items'][1] if isinstance(raw, dict) else raw[1]
                self.values[name] = self.ev(args[1])
            elif kind == 'IF_THEN_ELSE':
                # Eager conditions expose dereferences that rely on short-circuiting.
                checks = [self.check(c) for c in args[0]['args_list'] if c.get('enable', True)]
                self.run(args[1 if all(checks) else 2]['args_list'])
            elif kind == 'PICK_PLAYER_DO_ACTION':
                for self.picked in self.ev(args[0]):
                    try:
                        self.run(args[1]['args_list'])
                    except BreakLoop:
                        break
            elif kind == 'BREAK_LOOP':
                raise BreakLoop
            elif kind == 400342:
                self.returned = tuple(self.ev(a) for a in args)
            else:
                raise AssertionError(('Unsupported action', kind))


class SharedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # This migration test must not reapply the old migration to the live map.
        cls.original_team = repair.load(BASELINE / repair.TEAM)
        cls.fixed_team = repair.patch_team(cls.original_team)

    def test_old_pve_misclassifies_player_with_wrong_value_array(self):
        human = TeamModel('PVE', 1)
        human.run(self.original_team['action'])
        self.assertEqual(human.returned, (None, 'right'))
        npc = TeamModel('PVE', 31)
        npc.run(self.original_team['action'])
        self.assertEqual(npc.returned, (None, 'right'))

    def test_pve_returns_both_sides(self):
        for player, expected in [(1, ('left', 'right')), (31, ('right', 'left'))]:
            model = TeamModel('PVE', player)
            model.run(self.fixed_team['action'])
            self.assertEqual(model.returned, expected)

    def test_second_human_uses_own_group(self):
        model = TeamModel('PVE', 2)
        model.run(self.fixed_team['action'])
        self.assertEqual(model.returned, ('player2', 'right'))

    def test_pvp_existing_result_preserved(self):
        for player in (1, 2):
            old, new = TeamModel('PVP', player), TeamModel('PVP', player)
            old.run(self.original_team['action'])
            new.run(self.fixed_team['action'])
            self.assertEqual(new.returned, old.returned)

    def test_missing_skill_does_not_dereference(self):
        model = TeamModel('PVE', None)
        model.run(self.fixed_team['action'])
        self.assertEqual(model.returned, (None, None))

    def test_unknown_api_rejected(self):
        with self.assertRaises(AssertionError):
            TeamModel('PVE', 1).ev(repair.ex(100001, 'UNSUPPORTED'))

    def test_target_scope_exact_repair(self):
        original = repair.load(BASELINE / 'ability/134283918.json')
        fixed, changes = repair.patch_scope(original)
        self.assertTrue(changes)
        old = [n for _, n in repair.walk(original['trigger_dict']['1959489540'])
               if n.get('arg_type') == 100006 and n.get('args_list') == [
                   {'__tuple__': True, 'items': ['UNIT_ENTITY', '目标单位', 'local']}]]
        self.assertTrue(old)
        self.assertEqual(len(changes), len(old))
        self.assertEqual(fixed['trigger_dict']['893440004'], original['trigger_dict']['893440004'])
        self.assertEqual(fixed['variable_dict'], original['variable_dict'])
        self.assertEqual(repair.patch_scope(fixed)[1], [])

    def test_batch_exactly_65_hero_actives(self):
        overlay = {p.relative_to(BASELINE).as_posix(): repair.load(p)
                   for p in (BASELINE / 'ability').glob('*.json')}
        overlay[repair.TEAM] = repair.load(BASELINE / repair.TEAM)
        _, notes = repair.build(MAP, overlay)
        self.assertEqual(len([x for x in notes if x['issue'] == 1]), 65)


if __name__ == '__main__':
    unittest.main()
