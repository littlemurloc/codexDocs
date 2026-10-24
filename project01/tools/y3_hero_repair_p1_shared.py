"""Scoped P1 target-scope and two-sided team resolution repair.

This is a candidate builder, not a live migration command. Object identifiers,
cast predicates and PVP behavior are retained. Runtime acceptance is separate.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

TEAM = 'global_trigger/function/new/参数返回/返回【敌方or己方队伍】通过持有技能.json'


def walk(value, path=()):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from walk(child, path + (key,))
    elif isinstance(value, list):
        for key, child in enumerate(value):
            yield from walk(child, path + (key,))


def load(path):
    return json.loads(path.read_text(encoding='utf8'))


def enabled_walk(value, path=()):
    if isinstance(value, dict):
        if value.get('enable') is False:
            return
        yield path, value
        for key, child in value.items():
            yield from enabled_walk(child, path + (key,))
    elif isinstance(value, list):
        for key, child in enumerate(value):
            yield from enabled_walk(child, path + (key,))


def ex(kind, sub, *args):
    return dict(arg_type=kind, sub_type=sub, args_list=list(args))


class Nodes:
    def __init__(self, document):
        self.used = {n['element_id'] for _, n in walk(document) if 'element_id' in n}
        self.next = 2100200001000000

    def fresh(self, node):
        node = copy.deepcopy(node)
        for _, child in walk(node):
            if 'element_id' in child:
                child['element_id'] = self.id()
        return node

    def id(self):
        self.next += 1
        assert self.next not in self.used
        self.used.add(self.next)
        return self.next

    def branch(self, conditions, actions):
        return dict(action_type='IF_THEN_ELSE',
                    args_list=[ex(100021, 1, *conditions), ex(100022, 1, *actions), ex(100022, 1)],
                    element_id=self.id(), bp=False, enable=True, fake_op=[])

    def exists(self, ref):
        return dict(condition_type='TYPE_IS_EXIST', args_list=[copy.deepcopy(ref)],
                    element_id=self.id(), enable=True)


def patch_scope(document):
    """Align only auto-target reads whose search writes the actor slot."""
    result = copy.deepcopy(document)
    changes = []
    for tid, trigger in result.get('trigger_dict', {}).items():
        if tid != '1959489540':
            continue
        actor_writes = [n for _, n in enabled_walk(trigger)
                        if n.get('action_type') == 'SET_VARIABLE' and n.get('enable', True)
                        and n['args_list'][0].get('args_list') == [
                            {'__tuple__': True, 'items': ['UNIT_ENTITY', '目标单位', 'actor']}]]
        if not actor_writes:
            continue
        local_writes = [n for _, n in enabled_walk(trigger) if n.get('action_type') == 'SET_VARIABLE'
                        and n['args_list'][0].get('args_list') == [
                            {'__tuple__': True, 'items': ['UNIT_ENTITY', '目标单位', 'local']}]]
        assert not local_writes, 'Target local has an assignment; review before scope migration'
        for pointer, node in enabled_walk(trigger):
            if node.get('arg_type') == 100006 and node.get('sub_type') == 11 and node.get('args_list') == [
                    {'__tuple__': True, 'items': ['UNIT_ENTITY', '目标单位', 'local']}]:
                node['args_list'][0]['items'][2] = 'actor'
                changes.append({'issue': 1, 'trigger': tid, 'pointer': list(pointer)})
    return result, changes


def patch_team(document):
    result = patch_player_membership(document)
    n = Nodes(result)
    assert result['func_id'] == '869622f5961411f1933a3fb31c846afd'
    pve, pvp = result['action'][2:4]
    inner = pve['args_list'][1]['args_list'][0]
    yes, no = inner['args_list'][1]['args_list'], inner['args_list'][2]['args_list']
    assert len(yes) == len(no) == 1
    enemy_global = copy.deepcopy(no[0]['args_list'][1])
    to_enemy = n.fresh(no[0])
    to_enemy['args_list'][1] = enemy_global
    yes.append(to_enemy)
    # The NPC branch used to leave its own return empty and return itself as enemy.
    no[0]['args_list'][0] = copy.deepcopy(yes[0]['args_list'][0])
    no.append(n.fresh(pvp['args_list'][1]['args_list'][1]))
    ability = ex(100014, 2, {'__tuple__': True, 'items': ['ABILITY', '持有技能', 'local']})
    owner = ex(100006, 'GET_ABILITY_OWNER', ability)
    result['action'][2:4] = [n.branch([n.exists(ability)], [
        n.branch([n.exists(owner)], [pve, pvp])])]
    result['func_comment'] = (result.get('func_comment', '') +
        '\nP1修复：PVE始终同时返回己方和敌方；NPC己方为敌人队伍，敌方从敌对玩家队伍取得。'
        '先校验技能和拥有者；PVP沿用原敌对玩家选择。')
    return result


def patch_player_membership(document):
    """DICT_HAS_VALUE searches values, not the indexes of a team array."""
    result = copy.deepcopy(document)
    assert result['func_id'] == '869622f5961411f1933a3fb31c846afd'
    checks = [node for _, node in walk(result.get('action', []))
              if node.get('condition_type') == 'DICT_HAS_VALUE']
    assert len(checks) == 1, 'Review changed player-classification branches'
    array, player = checks[0]['args_list']
    assert array['arg_type'] == 100081 and array['sub_type'] == 1
    assert player['sub_type'] == 'OWNER_PLAYER'
    reference = array['args_list'][0]
    assert reference.get('__tuple__') is True
    assert reference['items'] in (['UNIT_GROUP', '玩家队伍'], ['PLAYER', 'playersDetail'])
    reference['items'] = ['PLAYER', 'playersDetail']
    return result


def build(root: Path, overlay=None):
    overlay = overlay or {}
    payload, details = {}, []
    table = load(root / 'tables/单位技能配置表.json')['table_data']['data']
    active_ids = {oid for row in table[2:] if row and row[0] and row[0] != '玩家'
                  for oid in row[2:5] if isinstance(oid, int) and oid != 134255698}
    for oid in sorted(active_ids):
        file = root / 'ability' / f'{oid}.json'
        relative = 'ability/' + file.name
        original = overlay.get(relative)
        if original is None:
            original = load(file)
        fixed, changes = patch_scope(original)
        if changes:
            payload[relative] = fixed
            details.append({'issue': 1, 'file': relative, 'reads': len(changes)})
    original = overlay.get(TEAM)
    payload[TEAM] = patch_team(original if original is not None else load(root / TEAM))
    details.append({'issue': 2, 'file': TEAM})
    return payload, details
