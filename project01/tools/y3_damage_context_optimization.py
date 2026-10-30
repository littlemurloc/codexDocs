"""Maintained damage-context transformation and regression helpers.

The 2026-10-30 one-time map deployment is retired; use frozen test fixtures.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

MAP = Path('D:/littl/testTempFile/ProjectMonster02/maps/map3')
REL = 'global_trigger/trigger/关卡初始化内容/universe05.json'
TID = '1404961588'
TARGET_ID = 2099992001000013
SOURCE = '伤害上下文_来源单位'
TARGET = '站位判定_受伤单位'
SOURCE_ID = 2099947001000001
SECTION_ID = 2099947001000002


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def encode(doc):
    return (json.dumps(doc, ensure_ascii=True, indent=4) + '\n').encode('utf-8')


def walk(node, path=(), active=False):
    if isinstance(node, dict):
        if active and node.get('enable') is False:
            return
        yield path, node
        for key, value in node.items():
            yield from walk(value, path + (key,), active)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk(value, path + (index,), active)


def at(doc, path):
    for key in path:
        doc = doc[key]
    return doc


def var(name):
    return dict(arg_type=100006, sub_type=11,
                args_list=[{'__tuple__': True, 'items': ['UNIT_ENTITY', name, 'local']}])


def expr(typ, sub, *args):
    return dict(arg_type=typ, sub_type=sub, args_list=list(args))


def build(before):
    after = copy.deepcopy(before)
    trigger = after['sub_trigger'][TID]
    assert trigger['trigger_name'] == '最终伤害加成结算_3'
    assert SOURCE not in trigger['var_data'][1], 'Already patched; do not restage live output'
    used = {n.get('element_id') for _, n in walk(after)}
    assert not {SOURCE_ID, SECTION_ID} & used
    hits = [(p, n) for p, n in walk(trigger['action'], active=True)
            if n.get('element_id') == TARGET_ID]
    assert len(hits) == 1
    target_path, target_init = hits[0]
    assert target_init['action_type'] == 'SET_VARIABLE'
    assert target_init['args_list'][0]['args_list'] == var(TARGET)['args_list']
    assert target_init['args_list'][1] == expr(100006, 'DAMAGE_TARGET_UNIT')
    # Move the existing target assignment; retain its ID and variable declaration.
    at(trigger['action'], target_path[:-1]).pop(target_path[-1])
    replacements = []
    for path, node in list(walk(trigger['action'], active=True)):
        sub = node.get('sub_type')
        if sub not in ('DAMAGE_SOURCE_UNIT', 'DAMAGE_TARGET_UNIT'):
            continue
        assert node == expr(100006, sub), 'Unexpected operand metadata; inspect before changing'
        original = copy.deepcopy(node)
        node.clear()
        node.update(var(SOURCE if sub == 'DAMAGE_SOURCE_UNIT' else TARGET))
        replacements.append(dict(path=list(path), original=original))
    assert collections_count(replacements) == {'DAMAGE_SOURCE_UNIT': 13, 'DAMAGE_TARGET_UNIT': 8}
    trigger['var_data'][0].setdefault('UNIT_ENTITY', {})[SOURCE] = 0
    trigger['var_data'][1][SOURCE] = 0
    trigger['var_data'][2].append(SOURCE)
    source_init = dict(action_type='SET_VARIABLE', element_id=SOURCE_ID,
                       bp=False, enable=True,
                       args_list=[expr(100030, 1, *var(SOURCE)['args_list']),
                                  expr(100006, 'DAMAGE_SOURCE_UNIT')])
    section = dict(action_type='STORAGE_BOX', element_id=SECTION_ID,
                   bp=False, enable=True,
                   args_list=[expr(100021, 1), expr(100022, 1, source_init, target_init),
                              expr(100022, 1), expr(100003, 1,
                              '① 本次伤害上下文：来源与目标各读取一次；仅本次回调复用')])
    trigger['action'].insert(0, section)
    edits = dict(target_path=list(target_path), replacements=replacements)
    assert restore(after, edits) == before, 'Unrelated content changed'
    return after, edits


def collections_count(replacements):
    counts = {}
    for item in replacements:
        key = item['original']['sub_type']
        counts[key] = counts.get(key, 0) + 1
    return counts


def restore(after, edits):
    """Exact structural inverse, used to prove the scope of this transformation."""
    result = copy.deepcopy(after)
    trigger = result['sub_trigger'][TID]
    section = trigger['action'].pop(0)
    assert section['element_id'] == SECTION_ID
    target_init = section['args_list'][1]['args_list'][1]
    for item in edits['replacements']:
        node = at(trigger['action'], item['path'])
        expected = var(SOURCE if item['original']['sub_type'] == 'DAMAGE_SOURCE_UNIT' else TARGET)
        assert node == expected
        node.clear()
        node.update(copy.deepcopy(item['original']))
    path = edits['target_path']
    at(trigger['action'], path[:-1]).insert(path[-1], target_init)
    del trigger['var_data'][0]['UNIT_ENTITY'][SOURCE]
    del trigger['var_data'][1][SOURCE]
    trigger['var_data'][2].remove(SOURCE)
    return result

if __name__ == '__main__':
    raise SystemExit('Initial map deployment retired; use maintained helpers and read-only regression fixtures.')
