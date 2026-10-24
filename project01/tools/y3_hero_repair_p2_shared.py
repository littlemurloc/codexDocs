"""P2 shared knockback safeguard, preserving existing displacement rules."""
import copy
from pathlib import Path
from y3_hero_repair_p1_shared import Nodes, ex, load, walk

KNOCKBACK = 'global_trigger/function/业务逻辑/功能执行/单位受击击退效果.json'
LEVEL_KEYS = {134259221: '伤害系数', 134223239: '伤害系数', 134239928: '伤害系数',
              134223225: '额外系数', 134238829: '伤害系数', 134232470: '伤害系数',
              134232552: '伤害系数'}


def patch_knockback(document):
    fixed = copy.deepcopy(document)
    nodes = Nodes(fixed)
    nodes.next = 2100200002000000
    actions = fixed['action'][0]['args_list'][1]['args_list']
    magnitude_index = next(i for i, a in enumerate(actions)
                           if a['element_id'] == 1754329234000241)
    magnitude = copy.deepcopy(actions[magnitude_index]['args_list'][0])
    magnitude['arg_type'] = 100000
    magnitude['sub_type'] = 2
    following = actions[magnitude_index + 1:]
    assert {1311690899000648, 1311690899000661} <= {
        a['element_id'] for a in following}
    condition = dict(condition_type='FLOAT_COMPARE',
                     args_list=[magnitude, ex(100015, 1, '>'), ex(100000, 1, 0.000001)],
                     element_id=nodes.id(), enable=True)
    actions[magnitude_index + 1:] = [nodes.branch([condition], following)]
    fixed['func_comment'] = (fixed.get('func_comment', '') +
                            '\nP2修复：两单位平面重合时无合法击退方向，跳过归一化及位移，防止除零。')
    return fixed


def patch_levels(document, key):
    fixed = copy.deepcopy(document)
    level = fixed['trigger_dict']['26066946']
    assert any(e['event_type'] == 'ABILITY_LEVEL_CHANGED' for e in level['event'])
    switches = [n for _, n in walk(level['action']) if n.get('action_type') == 'SWITCH']
    assert len(switches) == 1
    cases = switches[0]['args_list'][1]['args_list']
    assert [c['args_list'][0]['args_list'][0] for c in cases] == [1, 2, 3, 4, 5]
    before, after, maximum = [], [], None
    for case in cases:
        values = [n for _, n in walk(case) if n.get('action_type') == 'SET_ENTITY_KV'
                  and n['args_list'][1] == ex(100003, 1, key)]
        assert len(values) == 1
        value = values[0]['args_list'][2]
        assert value['sub_type'] == 1 and isinstance(value['args_list'][0], (int, float))
        number = value['args_list'][0]
        before.append(number)
        maximum = number if maximum is None else max(maximum, number)
        value['args_list'][0] = maximum
        after.append(maximum)
    return fixed, before, after


def build(root: Path, overlay=None):
    overlay = overlay or {}
    payload = {KNOCKBACK: patch_knockback(load(root / KNOCKBACK))}
    notes = [{'issue': 48, 'file': KNOCKBACK,
              'effect': 'zero-length displacement skips normalization'}]
    for oid, key in LEVEL_KEYS.items():
        relative = f'ability/{oid}.json'
        original = overlay.get(relative)
        fixed, before, after = patch_levels(original if original is not None else load(root / relative), key)
        if before != after:
            payload[relative] = fixed
        notes.append({'issue': 47, 'file': relative, 'key': key, 'before': before,
                      'after': after, 'policy': 'user-approved nondecreasing prefix maximum'})
    return payload, notes
