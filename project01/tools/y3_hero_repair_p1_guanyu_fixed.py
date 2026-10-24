"""Fixed Guan Yu critical settlement using documented native damage stages.

The pre-calculation event can override the critical result. BEFORE_APPLY runs
after engine critical/formula calculation and before shields, and can change
damage and the displayed critical flag. The three active skills already bind a
per-cast multiplier and one-time payment latch; do not multiply their requests.
"""
import copy
from pathlib import Path
from y3_hero_repair_p1_shared import Nodes, ex, load, walk

FILE = 'ability/134284051.json'
IDS = (2100200501, 2100200502)
ACTIVES = (134284050, 134284052, 134284054)


def patch(document):
    result = copy.deepcopy(document)
    n = Nodes(result)
    n.next = 2100200501000000
    ability = ex(100014, 'DAMAGE_ABILITY')

    def action(kind, *args):
        return dict(action_type=kind, args_list=list(args), element_id=n.id(), bp=False, enable=True)

    def condition(kind, *args):
        return dict(condition_type=kind, args_list=list(args), element_id=n.id(), enable=True)

    def kv(key):
        return ex(100000, 'GET_FLOAT_KV', copy.deepcopy(ability), ex(100003, 1, key))

    def skill_filter():
        resource = ex(100039, 'ABILITY_NAME_OF_ABILITY', copy.deepcopy(ability))
        checks = [condition('ABILITY_COMPARE', copy.deepcopy(resource), ex(100035, 1, '=='), ex(100039, 1, oid))
                  for oid in ACTIVES]
        return condition('OR', ex(100021, 1, *checks))

    def eligibility():
        return [condition('FLOAT_COMPARE', kv('关羽本次强化'), ex(100015, 1, '>'), ex(100000, 1, 0.0)),
                condition('FLOAT_COMPARE', kv('关羽本次已扣点'), ex(100015, 1, '=='), ex(100000, 1, 1.0))]

    post = [action('SET_CUR_DAMAGE', ex(100000, 'ARITHMETIC_OPERATION',
                    ex(100000, 'HURT_DAMAGE'), ex(100017, 1, '*'), kv('关羽强化倍率'))),
            action('SET_CUR_DAMAGE_IS_CRITICAL', ex(100001, 1, True))]
    pre = [action('SET_CUR_DAMAGE_IS_CRITICAL', ex(100001, 1, False))]
    gain = result['trigger_dict']['1959489540']
    loss = result['trigger_dict']['225054724']
    for tid, title, event, body in [
        (IDS[0], '武威强化-即将伤害禁止额外暴击', 'ET_UNIT_HURT_OTHER', pre),
        (IDS[1], '武威强化-计算加成固定三倍暴击', 'ET_UNIT_HURT_OTHER_BEFORE_APPLY', post),
    ]:
        assert str(tid) not in result['trigger_dict']
        handle_name = title + '监听'
        assert handle_name not in result['variable_length_dict']
        result['variable_dict'].setdefault('DYNAMIC_TRIGGER_INSTANCE', {})[handle_name] = 0
        result['variable_length_dict'][handle_name] = 0
        result['variable_group_info'].append({'__tuple__': True, 'items': [handle_name, handle_name]})
        handle = ex(100178, 'VARIABLE', {'__tuple__': True,
                                        'items': ['DYNAMIC_TRIGGER_INSTANCE', handle_name, 'actor']})
        registration = action('SET_VARIABLE', copy.deepcopy(handle),
                              ex(100178, 'REG_ABILITY_TRIGGER', ex(100068, 1, tid)))
        trigger = dict(action=[n.branch([n.exists(ability)], [
                            n.branch([skill_filter()], [n.branch(eligibility(), body)])])],
                       call_enabled=True, condition=[], enabled=False,
                       event=[dict(event_type='SPECIAL_UNIT_EVENT',
                                   args_list=[ex(100006, 'ABILITY_OWNER'), ex(100007, 1, event)],
                                   element_id=n.id(), enable=True)],
                       group_id=134284051, is_conf=True, p_trigger_id=1959489540,
                       sub_trigger_owner_set_var_action=registration, trigger_id=tid,
                       trigger_name=title, valid=True, var_data=[{}, {}, []])
        result['trigger_dict'][str(tid)] = trigger
        result['local_variable'][str(tid)] = dict(variable_dict={}, variable_length_dict={})
        result['trigger_group_info'][0]['group'].append({'__tuple__': True, 'items': [tid, title]})
        gain['action'].append(tid)
        loss['action'].insert(0, action('UNREG_TRIGGER', copy.deepcopy(handle)))
    return result


def build(root: Path):
    for oid in ACTIVES:
        active = load(root / f'ability/{oid}.json')
        reads = [n for _, n in walk(active) if n.get('sub_type') == 'GET_FLOAT_KV'
                 and n.get('args_list', [None])[-1] == ex(100003, 1, '关羽强化倍率')]
        assert not reads, 'Active already multiplies its request; review to prevent double multiplication'
        setters = [n for _, n in walk(active) if n.get('action_type') == 'SET_ENTITY_KV']
        keys = {n['args_list'][1]['args_list'][0] for n in setters}
        assert {'关羽本次强化', '关羽本次已扣点', '关羽强化倍率'} <= keys
    return {FILE: patch(load(root / FILE))}, [{'issue': 14, 'file': FILE,
        'new_dynamic_triggers': list(IDS), 'status': 'candidate',
        'effect': 'Only paid empowered active packets: pre disables native critical; post multiplies once then marks critical',
        'evidence': 'Official eca_index UNIT_HURT_OTHER, UNIT_HURT_OTHER_BEFORE_APPLY, SET_CUR_DAMAGE_IS_CRITICAL; engine gameplay pending'}]
