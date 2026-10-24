"""Bounded execution of the changed native ECA branches, not an engine emulator."""
from copy import deepcopy as cp
from pathlib import Path
from types import SimpleNamespace as NS
import collections
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import y3_hero_runtime_followup_20261024 as fix


class BreakIteration(Exception):
    pass


def unit(team=1, position=1, alive=True, dead=False, captain=True):
    return NS(team=team, alive=alive, tags=({'已死亡'} if dead else set()) |
              ({'阵型队长'} if captain else set()), kv={'归属阵型编号': position}, buffs={})


class Frame:
    def __init__(self, skill=None, owner=None, event=None, phase=2):
        self.skill, self.owner, self.event = skill, owner, event
        self.phase, self.wave = phase, 1
        self.vars, self.effects, self.commands = {}, [], []
        self.selected = None

    def value(self, n):
        if not isinstance(n, dict):
            raise AssertionError('Unsupported raw expression: ' + repr(n))
        kind, args = n.get('sub_type'), n.get('args_list', [])
        if kind == 1:
            if len(args) != 1 or isinstance(args[0], dict):
                raise AssertionError('Not a primitive literal')
            return args[0]
        if kind in [2, 6, 11, 14, 'VARIABLE']:
            raw = args[0]
            key = tuple(raw['items'] if isinstance(raw, dict) else raw)
            if key == ('INTEGER', '当前游戏进程阶段'):
                return self.phase
            if key == ('INTEGER', '当前进程所在波次编号'):
                return self.wave
            return self.vars.get(key, [] if key[0] == 'UNIT_GROUP' else 0)
        if kind == 'CUR_ABILITY': return self.skill
        if kind == 'ABILITY_OWNER': return self.owner
        if kind == 'FOR_EACH_SELECTED_UNIT': return self.selected
        if kind == 'GET_MODIFIER_FROM_EVENT': return self.event
        if kind == 'MODIFIER_OWNER': return self.event.owner
        if kind == 'GET_BUFF_SOURCE': return self.read(self.value(args[0])).source
        if kind == 'GET_MODIFIER_ENTITY_METATYPE': return self.event.resource
        if kind == 'GET_BUFF_TIME': return self.event.remaining
        if kind == 'GET_MOD_STACK': return self.read(self.value(args[0])).stack
        if kind == 'GET_MOD_STACK_MAX': return self.read(self.value(args[0])).maximum
        if kind == 'GET_MODIFIER_LAYER_CHANGE_VALUE': return self.event.delta
        if kind == 'GET_LAST_MODIFIER_INSTANCE':
            return self.read(self.value(args[0])).buffs.get(self.value(args[1]))
        if kind == 'ABILITY_CD_LEFT_TIME': return self.read(self.value(args[0])).cooldown
        if kind == '97642c3d802a5935a73289745a266ac8':
            return self.read(self.value(args[0])).can_act
        if kind in ['GET_INTEGER_KV', 'GET_BOOLEAN_KV', 'GET_UNIT_ENTITY_KV', 'GET_MODIFIER_ENTITY_KV']:
            obj = self.read(self.value(args[0])); key = self.value(args[1])
            return obj.kv.get(key, False if kind == 'GET_BOOLEAN_KV' else 0)
        if kind == 'UNIT_HAS_TAG': return self.value(args[1]) in self.read(self.value(args[0])).tags
        if kind == 'INT_PLUS_ONE': return self.value(args[0]) + 1
        if kind == 'UNIT_COMMAND_USE_SKILL':
            return ('cast', self.value(args[0]), self.value(n['op_arg'][2]))
        raise AssertionError('Unsupported expression: ' + str(kind))

    @staticmethod
    def read(obj):
        if not hasattr(obj, '__dict__'):
            raise AssertionError('Dereferenced missing object')
        return obj

    def condition(self, n):
        kind, args = n['condition_type'], n['args_list']
        if kind == 'TYPE_IS_EXIST': return hasattr(self.value(args[0]), '__dict__')
        if kind == 'BOOL_NOT': return not bool(self.value(args[0]))
        if kind == 'IS_UNIT_ALIVE': return self.read(self.value(args[0])).alive
        if kind == 'IS_ENEMY': return self.read(self.value(args[0])).team != self.read(self.value(args[1])).team
        if kind == 'UNIT_HAS_TAG': return self.value(args[1]) in self.read(self.value(args[0])).tags
        if kind == 'UNIT_HAS_MODIFIER': return self.value(args[1]) in self.read(self.value(args[0])).buffs
        if kind == 'HAS_KV_ANY': return self.value(args[1]) in self.read(self.value(args[0])).kv
        if kind == 'UNIT_IN_GROUP': return any(u is self.value(args[0]) for u in self.value(args[1]))
        if kind in ['AND', 'OR']:
            tests = [self.condition(c) for c in args[0]['args_list']]
            return all(tests) if kind == 'AND' else any(tests)
        if kind in ['FLOAT_COMPARE', 'BOOL_COMPARE', 'UNIT_COMPARE', 'MODIFIER_COMPARE', 'MODIFIER_CLASS_COMPARE']:
            a, op, b = [self.value(x) for x in args]
            if kind in ['UNIT_COMPARE', 'MODIFIER_COMPARE']:
                return (a is b) if op == '==' else (a is not b)
            return {'==': lambda: a == b, '!=': lambda: a != b, '<': lambda: a < b,
                    '<=': lambda: a <= b, '>': lambda: a > b, '>=': lambda: a >= b}[op]()
        raise AssertionError('Unsupported condition: ' + kind)

    def run(self, actions):
        for n in actions:
            if n.get('enable') is False: continue
            kind, args = n['action_type'], n['args_list']
            if kind == 'PRINT_MESSAGE_ACTION_TO_DIALOG': continue
            if kind == 'IF_THEN_ELSE':
                checks = [self.condition(c) for c in args[0]['args_list'] if c.get('enable') is not False]
                self.run(args[1 if all(checks) else 2]['args_list'])
            elif kind == 'SET_VARIABLE':
                self.vars[tuple(args[0]['args_list'][0]['items'])] = self.value(args[1])
            elif kind == 'SET_ENTITY_KV':
                self.read(self.value(args[0])).kv[self.value(args[1])] = self.value(args[2])
            elif kind == 'PICK_UNIT_DO_ACTION':
                previous = self.selected
                for candidate in self.value(args[0]):
                    self.selected = candidate
                    try: self.run(args[1]['args_list'])
                    except BreakIteration: break
                self.selected = previous
            elif kind == 'BREAK_LOOP': raise BreakIteration()
            elif kind == 'UNIT_RELEASE_COMMAND': self.commands.append(self.value(args[1]))
            elif kind == 'GROUP_ADD_UNIT': self.value(args[1]).append(self.value(args[0]))
            elif kind == 'CLEAR_GROUP': self.value(args[0]).clear()
            elif kind == 'ADD_MODIFIER': self.effects.append((self.value(args[0]), self.value(args[1])))
            else: raise AssertionError('Unsupported action: ' + str(kind))


class RepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = {p: fix.trace.read(fix.WORK / 'map3-before' / p) for p in fix.FILES}
        cls.new = fix.build(fix.WORK / 'map3-before')

    def summer(self, positions=(1, 4), **kwargs):
        owner = unit(); owner.can_act = kwargs.get('can_act', True); owner.kv['自动施法'] = True
        skill = NS(cooldown=kwargs.get('cooldown', 0), kv={})
        targets = [unit(team=2, position=p) for p in positions]
        if targets:
            targets[0].buffs[134232159] = NS(source=owner)
        frame = Frame(skill, owner, phase=kwargs.get('phase', 2))
        frame.vars[('UNIT_GROUP', '搜索组', 'actor')] = targets
        timer = fix.one(self.new[fix.FILES[0]]['trigger_dict']['1959489540']['action'], 'RUN_LOOP_TIMER')
        return frame, targets, timer['args_list'][3]['args_list']

    def test_summer_three_living_same_lane_casts(self):
        f, targets, actions = self.summer(); f.run(actions)
        self.assertEqual(len(f.commands), 1)
        self.assertIs(f.commands[0][2], targets[0])

    def test_summer_three_rejects_cooldown_busy_and_preparation(self):
        for args in [{'cooldown': 1}, {'can_act': False}, {'phase': 1}]:
            f, _, actions = self.summer(**args); f.run(actions); self.assertFalse(f.commands)

    def test_summer_three_requires_two_in_same_lane(self):
        for positions in [(1,), (1, 2), (0, 0)]:
            f, _, actions = self.summer(positions); f.run(actions); self.assertFalse(f.commands)

    def test_summer_three_rejects_engine_dead_and_fake_dead(self):
        for tag in ['native', 'fake']:
            f, targets, actions = self.summer()
            if tag == 'native': targets[0].alive = False
            else: targets[0].tags.add('已死亡')
            f.run(actions); self.assertFalse(f.commands)

    def test_summer_three_missing_skill_owner_and_mark_are_safe(self):
        for missing in ['skill', 'owner', 'mark']:
            f, targets, actions = self.summer()
            if missing == 'mark': targets[0].buffs.clear()
            else: setattr(f, missing, None)
            f.run(actions); self.assertFalse(f.commands)

    def six(self, remaining=0, dead=False):
        owner, target = unit(), unit(team=2, dead=dead)
        skill = NS(kv={})
        core = NS()
        owner.buffs[134282266] = core
        mark = NS(resource=134232159, remaining=remaining, source=owner, owner=target,
                  kv={'修复_猎印波次': 1, '修复_猎印来源核心': core})
        f = Frame(skill, owner, mark)
        f.vars[('UNIT_GROUP', '修复_识破已触发目标组', 'actor')] = []
        t = self.new[fix.FILES[1]]['trigger_dict']['1051000836']
        return f, target, t['action']

    def test_summer_six_uses_native_loss_event_not_remaining_ge_four(self):
        old = self.old[fix.FILES[1]]['trigger_dict']['1051000836']
        new = self.new[fix.FILES[1]]['trigger_dict']['1051000836']
        self.assertEqual(old['event'][0]['args_list'][0]['args_list'], ['ET_MODIFIER_LAYER_CHANGE'])
        self.assertEqual(new['event'][0]['args_list'][0]['args_list'], ['ET_LOSS_MODIFIER'])
        self.assertEqual([n['args_list'][1]['args_list'][0] for n in fix.walk(new['action'])
                          if n.get('condition_type') == 'FLOAT_COMPARE'
                          and n['args_list'][0].get('sub_type') == 'GET_BUFF_TIME'], ['<='])

    def test_summer_six_natural_expiry_living_target_once_per_target(self):
        f, target, actions = self.six(); f.run(actions); f.run(actions)
        self.assertEqual(f.effects, [(target, 134269505)])
        other = unit(team=2); f.event.owner = other; f.run(actions)
        self.assertEqual(len(f.effects), 2)

    def test_summer_six_early_removal_and_fake_death_do_not_grant(self):
        for remaining, dead in [(2, False), (0, True)]:
            f, _, actions = self.six(remaining, dead); f.run(actions); self.assertFalse(f.effects)
        f, target, actions = self.six(); target.alive = False; f.run(actions); self.assertFalse(f.effects)

    def test_summer_six_new_wave_can_grant_again(self):
        f, _, actions = self.six(); f.run(actions); f.wave = 2
        f.event.kv['修复_猎印波次'] = 2
        f.run(actions)
        self.assertEqual(len(f.effects), 2)

    def test_summer_six_old_wave_and_replaced_core_do_not_grant(self):
        f, _, actions = self.six(); f.wave = 2; f.run(actions)
        self.assertFalse(f.effects)
        f, _, actions = self.six(); f.owner.buffs[134282266] = NS(); f.run(actions)
        self.assertFalse(f.effects)

    def test_zhang_six_requires_explicit_five_star_consumption(self):
        def conditions(doc):
            return next(n['args_list'][0]['args_list'] for n in fix.walk(doc)
                        if n.get('action_type') == 'IF_THEN_ELSE' and any(
                            x.get('sub_type') == 'GET_MODIFIER_LAYER_CHANGE_VALUE'
                            for x in fix.walk(n['args_list'][0])))
        core = NS(stack=1, delta=-3, kv={})
        owner = unit(); owner.buffs[134259689] = core
        f = Frame(NS(), owner, core)
        self.assertTrue(all(f.condition(n) for n in conditions(self.old[fix.FILES[3]])))
        self.assertFalse(all(f.condition(n) for n in conditions(self.new[fix.FILES[3]])))
        core.kv[fix.CONSUMING] = True
        self.assertTrue(all(f.condition(n) for n in conditions(self.new[fix.FILES[3]])))

    def test_zhang_five_marker_brackets_native_consume(self):
        d = self.new[fix.FILES[2]]
        action = fix.one(d['trigger_dict']['893440004']['action'], 'SET_BUFF_STACK')
        lists = []
        def visit(x):
            if isinstance(x, list):
                if action in x: lists.append(x)
                for n in x:visit(n)
            elif isinstance(x, dict):
                for n in x.values():visit(n)
        visit(d['trigger_dict']['893440004']['action'])
        items = lists[0]; index = items.index(action)
        self.assertEqual(items[index - 1]['action_type'], 'SET_ENTITY_KV')
        self.assertEqual(items[index - 1]['args_list'][2]['args_list'], [True])
        self.assertEqual(items[index + 1]['action_type'], 'IF_THEN_ELSE')

    def test_sunce_diagnostics_do_not_change_any_gameplay(self):
        document = self.new[fix.FILES[4]]
        def clean(x):
            if isinstance(x, list):
                return [clean(n) for n in x if not (isinstance(n, dict)
                    and n.get('action_type') == 'PRINT_MESSAGE_ACTION_TO_DIALOG'
                    and isinstance(n['args_list'][1]['args_list'][0], str)
                    and n['args_list'][1]['args_list'][0].startswith(fix.PREFIX))]
            if isinstance(x, dict):return {k:clean(v) for k,v in x.items()}
            return x
        self.assertEqual(clean(document), self.old[fix.FILES[4]])

    def test_original_trace_nodes_and_triggers_preserved(self):
        registry = fix.trace.read(fix.trace.REGISTRY)
        for path, doc in self.new.items():
            if path in registry['entries']:
                fix.trace.checked_nodes(doc, registry['entries'][path]['logs'])
            self.assertEqual(set(doc['trigger_dict']), set(self.old[path]['trigger_dict']))

    def test_no_new_element_id_duplicates(self):
        for path, doc in self.new.items():
            old = collections.Counter(n['element_id'] for n in fix.walk(self.old[path]) if 'element_id' in n)
            new = collections.Counter(n['element_id'] for n in fix.walk(doc) if 'element_id' in n)
            self.assertFalse({k:v for k,v in new.items() if v > max(1, old[k])}, path)

    def test_xuchu_loss_missing_auxiliary_buff_is_safe(self):
        f = Frame(NS(), unit(), NS(owner=unit()))
        actions = self.new[fix.FILES[6]]['trigger_dict']['594665475']['action']
        f.run(actions[:1])

    def test_xunyu_missing_core_skips_layer_comparison(self):
        d = self.new[fix.FILES[5]]
        timer = fix.one(d['trigger_dict']['1959489540']['action'], 'RUN_LOOP_TIMER')
        wrappers = [n for n in fix.walk(timer) if n.get('action_type') == 'IF_THEN_ELSE'
                    and n['element_id'] in range(209996700160000, 209996700170000)]
        outer = next(n for n in wrappers if n['args_list'][0]['args_list'][0]['args_list'][0]
                     .get('sub_type') == 'ABILITY_OWNER')
        Frame(NS(), unit()).run([outer])


if __name__ == '__main__':
    unittest.main()
