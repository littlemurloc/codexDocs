"""Repair the separately logged Huang Zhong four-star cooldown callback."""
import copy
from pathlib import Path
from y3_hero_repair_p1_shared import Nodes, ex, load

FILE = 'ability/134237143.json'
TIMER = '守位恢复计时器'


def patch(document):
    fixed = copy.deepcopy(document)
    n = Nodes(fixed)
    n.next = 2100200004000000
    assert TIMER not in fixed['variable_length_dict']
    fixed['variable_dict'].setdefault('NEW_TIMER', {})[TIMER] = -1
    fixed['variable_length_dict'][TIMER] = 0
    fixed['variable_group_info'].append({'__tuple__': True, 'items': [TIMER, TIMER]})
    handle = ex(100181, 'VARIABLE', {'__tuple__': True, 'items': ['NEW_TIMER', TIMER, 'actor']})
    ability = ex(100014, 'CUR_ABILITY')

    def delete():
        return dict(action_type='DELETE_TIMER', args_list=[copy.deepcopy(handle)],
                    element_id=n.id(), bp=False, enable=True)

    gain = fixed['trigger_dict']['1959489540']
    init = dict(action_type='SET_ENTITY_KV',
                args_list=[copy.deepcopy(ability), ex(100003, 1, '内置CD'), ex(100001, 1, False)],
                element_id=n.id(), bp=False, enable=True)
    gain['action'].insert(0, init)
    hit = fixed['trigger_dict']['1340796934']
    setter, timer = hit['action']
    assert timer['action_type'] == 'RUN_ONCE_TIMER_NO_SAVE'
    assert timer['args_list'][0] == ex(100000, 1, 3)
    reset = timer['args_list'][1]['args_list'][0]
    for action in (setter, reset):
        assert action['action_type'] == 'SET_ENTITY_KV'
        assert action['args_list'][0] == ex(100006, 'ABILITY_OWNER')
        action['args_list'][0] = copy.deepcopy(ability)
    timer['action_type'] = 'RUN_ONCE_TIMER'
    timer['args_list'] = [copy.deepcopy(handle), timer['args_list'][0],
                          ex(100022, 1, n.branch([n.exists(ability)], [reset]))]
    old_checks = hit['condition']
    hit['condition'] = []
    hit['action'] = [n.branch([n.exists(ex(100014, 'DAMAGE_ABILITY'))], [
        n.branch(old_checks, [delete(), setter, timer])])]
    # A release event with no ability must not evaluate ability type/cast fields.
    release = fixed['trigger_dict']['2111275013']
    core = ex(100076, 'GET_LAST_MODIFIER_INSTANCE', ex(100006, 'ABILITY_OWNER'), ex(100046, 1, 134242511))
    release['action'] = [n.branch([n.exists(ex(100014, 'DAMAGE_ABILITY'))], [
        n.branch(release['condition'], [n.branch([n.exists(core)], release['action'])])])]
    release['condition'] = []
    fixed['trigger_dict']['225054724']['action'].insert(0, delete())
    return fixed


def build(root: Path):
    return {FILE: patch(load(root / FILE))}, [{'issue': 'P1-log-additional', 'file': FILE,
        'effect': 'Cooldown reads/writes use this skill; timer restart/cancel; invalid ability/core guards'}]
