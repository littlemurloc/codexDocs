"""Exercise generated ECA branches with a small model, not the Y3 runtime."""
import copy
import json
import math
import operator
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'staged'
SKILLS = list(range(134284040, 134284046))
FIRST, HEALED = 2099456002, 2099456003


class Model:
    def __init__(self, hps, unlocked=(1, 3, 5)):
        self.units = [dict(id=i, hp=hp, hp_max=100., attack_phy=100., kv={}, player=1, alive=hp > 0)
                      for i, hp in enumerate(hps)]
        self.owner = self.units[0]
        self.skills = {aid: dict(kv={}, owner=self.owner) for aid in SKILLS}
        self.eca = {aid: json.loads((ROOT / f'ability/{aid}.json').read_bytes()) for aid in SKILLS}
        self.core_eca = json.loads((ROOT / 'modifier/134284046.json').read_bytes())
        self.core = dict(kv={'凝露冷却': 0.}, stack=2, owner=self.owner)
        self.unlocked = unlocked
        self.cures, self.buffs, self.damages = [], [], []
        self.cancelled = 0
        self.pending = []
        self.owner['kv']['自动施法'] = True
        self.env = {}
        for aid in SKILLS:
            self.env = {'ability': self.skills[aid], 'owner': self.owner, 'vars': {}}
            for action in self.eca[aid]['trigger_dict']['1959489540']['action']:
                if isinstance(action, dict) and action['action_type'] == 'SET_ENTITY_KV':
                    self.action(action)

    def val(self, n):
        a, s = n.get('args_list', []), n['sub_type']
        if s == 1: return a[0] if a else None
        if s == 6: return 2
        if s == 11: return self.env['vars'].get(a[0]['items'][1])
        if s == 'CUR_ABILITY': return self.env['ability']
        if s == 'ABILITY_OWNER': return self.env['owner']
        if s == 'CUR_MODIFIER': return self.core
        if s == 'MODIFIER_OWNER': return self.owner
        if s == 'NONE_UNIT': return None
        if s == 'FOR_EACH_SELECTED_UNIT': return self.env['selected']
        if s == 'GET_ABILITY_TARGET_UNIT_FROM_EVENT': return self.env.get('event_target')
        if s == 'GET_UNIT_FROM_EVENT': return self.env['event_unit']
        if s == 'DAMAGE_ABILITY': return self.env['event_ability']
        if s == 'GET_ABILITY_CAST_TYPE': return self.val(a[0])['cast_type']
        if s == 'GET_CUS_EVENT_PARAM': return self.env['params'][self.val(a[0])]
        if s == 'OWNER_PLAYER': return self.val(a[0])['player']
        if s == 'GET_UNIT_ATTR': return self.val(a[0])[self.val(a[2])]
        if s == 'GET_HP_CUR': return self.val(a[0])['hp']
        if s in ('GET_FLOAT_KV', 'GET_UNIT_ENTITY_KV', 'GET_BOOLEAN_KV'): return self.val(a[0])['kv'].get(self.val(a[1]))
        if s == 'GET_LAST_MODIFIER_INSTANCE': return self.core
        if s == 'GET_MOD_STACK': return self.val(a[0])['stack']
        if s == 'GET_ABILITY_BY_AID': return self.skills[self.val(a[2])]
        if s == '6570be50be1a11f1916d7b0e2885c54e': return [u for u in self.units if u['player'] == self.owner['player']]
        if s == 'UNIT_LIST_IN_SHAPE': return [u for u in self.units if u['player'] != self.owner['player']]
        if s == 'ARITHMETIC_OPERATION':
            return {'+': operator.add, '-': operator.sub, '*': operator.mul, '/': operator.truediv}[self.val(a[1])](self.val(a[0]), self.val(a[2]))
        raise ValueError('Unsupported value ' + str(s))

    def condition(self, n):
        k, a = n['condition_type'], n['args_list']
        if k == 'TYPE_IS_EXIST': return self.val(a[0]) is not None
        if k == 'IS_UNIT_ALIVE': return self.val(a[0])['alive']
        if k == 'GET_IS_NORMAL_HIT_FROM_EVENT': return True
        x, y, op = self.val(a[0]), self.val(a[2]), self.val(a[1])
        if k == 'UNIT_COMPARE': return (x is y) if op == '==' else (x is not y)
        return {'==': operator.eq, '!=': operator.ne, '<': operator.lt, '>': operator.gt,
                '<=': operator.le, '>=': operator.ge}[op](x, y)

    def actions(self, actions):
        for n in actions:
            if isinstance(n, dict): self.action(n)

    def action(self, n):
        k, a = n['action_type'], n['args_list']
        if k == 'SET_ENTITY_KV': self.val(a[0])['kv'][self.val(a[1])] = self.val(a[2])
        elif k == 'SET_VARIABLE': self.env['vars'][a[0]['args_list'][0]['items'][1]] = self.val(a[1])
        elif k == 'SET_BUFF_STACK': self.val(a[0])['stack'] = self.val(a[1])
        elif k == 'RUN_ONCE_TIMER': self.pending.append([self.val(a[1]), copy.deepcopy(a[2]['args_list'])])
        elif k == 'IF_THEN_ELSE': self.actions(a[1 if all(self.condition(c) for c in a[0]['args_list']) else 2]['args_list'])
        elif k == 'PICK_UNIT_DO_ACTION':
            old = self.env.get('selected')
            for u in self.val(a[0]):
                self.env['selected'] = u
                self.actions(a[1]['args_list'])
            self.env['selected'] = old
        elif k == 'CURE_UNIT':
            u, amount = self.val(a[0]), self.val(a[1])
            self.cures.append((u['id'], amount))
            u['hp'] = min(u['hp_max'], u['hp'] + amount)
        elif k == 'ADD_MODIFIER': self.buffs.append((self.val(a[0])['id'], self.val(a[1]), self.val(n['op_arg'][2])))
        elif k == 'APPLY_DAMAGE': self.damages.append((self.val(a[2])['id'], self.val(a[3]), self.val(a[4])))
        elif k == 'IMMEDIATELY_CLEAR_CD': self.cancelled += 1
        elif k == 'SEND_CUSTOM_EVENT':
            eid, owner, patient = map(self.val, a)
            index = 3 if eid == HEALED else 5
            if index in self.unlocked:
                old = self.env
                self.env = dict(ability=self.skills[SKILLS[index]], owner=self.owner, vars={},
                                params={'触发单位': owner, '治疗单位': patient})
                trigger = self.eca[SKILLS[index]]['trigger_dict']['1051000836']
                if all(self.condition(c) for c in trigger['condition']): self.actions(trigger['action'])
                self.env = old
        elif k in ('CREATE_SFX_ON_POINT_NEW', 'BREAK_LOOP', 'PLAY_ANIMATION'): pass
        else: raise ValueError('Unsupported action ' + k)

    def hit(self):
        self.env = dict(ability=self.skills[SKILLS[1]], owner=self.owner, vars={})
        trigger = self.eca[SKILLS[1]]['trigger_dict']['1051000836']
        if all(self.condition(c) for c in trigger['condition']): self.actions(trigger['action'])

    def cast(self, unit, cast_type=2):
        self.env = dict(owner=self.owner, vars={}, event_unit=unit, event_ability={'cast_type': cast_type})
        trigger = self.core_eca['trigger_dict']['2011996165']
        if all(self.condition(c) for c in trigger['condition']): self.actions(trigger['action'])

    def tick(self):
        self.env = dict(owner=self.owner, vars={})
        for timer in list(self.pending):
            timer[0] -= .25
            if timer[0] <= 0:
                self.pending.remove(timer)
                self.actions(timer[1])

    def active_cast(self, index, target):
        self.env = dict(ability=self.skills[SKILLS[index]], owner=self.owner,
                        vars={'目标单位': target})
        self.actions(self.eca[SKILLS[index]]['trigger_dict']['893440004']['action'])


m = Model([100., 100.]); m.hit(); assert m.core['stack'] == 2 and not m.cures
m = Model([100., 40., 10.], unlocked=(1,)); m.hit(); assert m.cures == [(2, 5.)] and m.core['stack'] == 1
m = Model([100., 40., 10.]); m.hit(); assert m.cures == [(2, 5.), (1, 5.)]; assert m.buffs == [(2, 134284048, 4.), (1, 134284048, 4.)]
m = Model([100., 100., 10.]); m.hit(); assert m.cures == [(2, 5.)]
m = Model([100., 0., 10.]); m.hit(); assert m.cures == [(2, 5.)]
m = Model([100., 50.]); m.core['stack'] = 1; m.cast(m.units[1]); assert m.core['stack'] == 2 and m.core['kv']['凝露冷却'] == 2.
m.hit(); m.cast(m.units[1]); assert m.core['stack'] == 1
for _ in range(8): m.tick()
m.cast(m.owner); assert m.core['stack'] == 2
m = Model([100., 50.]); m.core['stack'] = 1; m.cast(m.units[1], cast_type=1); assert m.core['stack'] == 1
m = Model([100., 40.]); m.active_cast(0, m.units[1]); assert len(m.cures) == 1 and m.cures[0][0] == 1 and math.isclose(m.cures[0][1], 14.)
m = Model([100., 100.]); m.active_cast(0, m.units[1]); assert not m.cures and m.cancelled == 1
m = Model([100., 69.]); m.active_cast(4, m.units[1]); assert m.buffs == [(0, 134284049, 6.), (1, 134284049, 6.)]
m = Model([100., 70.]); m.active_cast(4, m.units[1]); assert not m.buffs and m.cancelled == 1
m = Model([100.]); m.units += [dict(id=i, hp=100., hp_max=100., attack_phy=100., kv={}, player=2, alive=True) for i in range(1, 6)]
m.active_cast(2, m.units[1]); assert m.damages == [(1, 1, 120.), (2, 1, 120.), (3, 1, 120.)]; assert len(m.buffs) == 3
print('13 generated-ECA model scenarios passed; this does not simulate Y3 range, timing, visuals or engine event dispatch')
