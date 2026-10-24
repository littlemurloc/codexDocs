"""Small P2 passive repairs with explicit ownership and contribution scopes."""
import copy
from pathlib import Path
from y3_hero_repair_p1_shared import Nodes, ex, load, walk


def nodes(document):
    result = Nodes(document)
    result.next = 2100200003000000
    return result


def patch_lubu_core(document):
    result = copy.deepcopy(document)
    trigger = result['trigger_dict']['762560516']
    assert trigger['event'][0]['args_list'][1] == ex(100007, 1, 'ET_KILL_UNIT')
    tags = [n for _, n in walk(trigger['condition']) if n.get('condition_type') == 'UNIT_HAS_TAG']
    assert len(tags) == 2
    for tag in tags:
        assert tag['args_list'][0] == ex(100006, 'MODIFIER_OWNER')
        tag['args_list'][0] = ex(100006, 'KILLED_UNIT')
    return result


def patch_lubu_six(document):
    result = copy.deepcopy(document)
    n = nodes(result)
    trigger = result['trigger_dict']['58232837']
    assert trigger['condition'][0]['condition_type'] == 'BOOL_COMPARE'
    core = ex(100076, 'GET_LAST_MODIFIER_INSTANCE', ex(100006, 'ABILITY_OWNER'), ex(100046, 1, 134274222))
    stacked = dict(condition_type='FLOAT_COMPARE',
                   args_list=[ex(100002, 'GET_MOD_STACK', core), ex(100015, 1, '>'), ex(100002, 1, 1)],
                   element_id=n.id(), enable=True)
    trigger['action'] = [n.branch([n.exists(core)], [n.branch([stacked], trigger['action'])])]
    return result


def patch_zhaoyun_contribution(document):
    result = copy.deepcopy(document)
    n = nodes(result)
    name = 'P2已应用游龙闪避'
    assert name not in result['variable_length_dict']
    result['variable_dict'].setdefault('FLOAT', {})[name] = 0
    result['variable_length_dict'][name] = 0
    result['variable_group_info'].append({'__tuple__': True, 'items': [name, name]})
    ref = ex(100000, 2, {'__tuple__': True, 'items': ['FLOAT', name, 'actor']})
    lhs = ex(100030, 1, {'__tuple__': True, 'items': ['FLOAT', name, 'actor']})
    level = result['trigger_dict']['26066946']
    subtract, switch, add = level['action']
    assert subtract['action_type'] == add['action_type'] == 'ADD_ATTR'
    assert subtract['args_list'][2] == ex(100042, 1, 'dodge_rate')
    subtract['args_list'][3]['args_list'][0] = copy.deepcopy(ref)
    set_contribution = dict(action_type='SET_VARIABLE', args_list=[copy.deepcopy(lhs), copy.deepcopy(add['args_list'][3])],
                            element_id=n.id(), bp=False, enable=True)
    ability = ex(100014, 'CUR_ABILITY')
    owner = copy.deepcopy(add['args_list'][0])
    level['action'] = [n.branch([n.exists(ability)], [n.branch([n.exists(owner)],
                       [subtract, switch, add, set_contribution])])]
    remove = n.fresh(subtract)
    clear = dict(action_type='SET_VARIABLE', args_list=[copy.deepcopy(lhs), ex(100000, 1, 0)],
                 element_id=n.id(), bp=False, enable=True)
    result['trigger_dict']['225054724']['action'].append(n.branch([n.exists(ability)], [
        n.branch([n.exists(owner)], [remove, clear])]))
    return result


def patch_zhuge_cooldown(document):
    result = copy.deepcopy(document)
    timer = result['trigger_dict']['58232837']['action'][4]
    assert timer['action_type'] == 'RUN_ONCE_TIMER_NO_SAVE'
    assert timer['args_list'][0] == ex(100000, 1, 6)
    timer['args_list'][0]['args_list'][0] = 12
    return result


def patch_lumeng_owner(document):
    result = copy.deepcopy(document)
    n = nodes(result)
    trigger = result['trigger_dict']['58232837']
    assert trigger['event'][0]['args_list'][0] == ex(100129, 1, 'ET_LOSS_MODIFIER')
    # Official ECA: MODIFIER_OWNER reads data.modifier:get_owner(), i.e. this
    # global modifier event's carrier, not the ability's owner.
    trigger['condition'].append(dict(condition_type='UNIT_COMPARE',
        args_list=[ex(100006, 'MODIFIER_OWNER'), ex(100035, 1, '=='), ex(100006, 'ABILITY_OWNER')],
        element_id=n.id(), enable=True))
    return result


FIXES = {'modifier/134274222.json': (36, patch_lubu_core),
         'ability/134275485.json': (37, patch_lubu_six),
         'ability/134263318.json': (44, patch_zhaoyun_contribution),
         'ability/134263515.json': (45, patch_zhuge_cooldown),
         'ability/134243085.json': (39, patch_lumeng_owner)}


def build(root: Path):
    payload, notes = {}, []
    for relative, (issue, patch) in FIXES.items():
        payload[relative] = patch(load(root / relative))
        notes.append({'issue': issue, 'file': relative, 'status': 'candidate'})
    return payload, notes
