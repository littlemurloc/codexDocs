"""Repair the proven post-damage fault; probe remaining engine-only failures.

Stages one and two are historical snapshots, not generators for this stage.
This stage deliberately does not change Zhang Liao or Xiahou Yuan's gameplay.
"""
from copy import deepcopy as cp
from pathlib import Path
import argparse
import collections
import json
import shutil

import y3_hero_runtime_followup_20261024 as base

ROOT = base.ROOT
WORK = base.WORK.parent / 'hero-followup-20261024-r3'
FILES = ['ability/134235373.json', 'ability/134256160.json',
         'ability/134240904.json', 'modifier/134259689.json',
         'modifier/134259870.json']
PREFIX = '[技能排查/20261024-r3] '
LOG = Path('D:/Program Files/y3/games/2.0/game/LocalData/trigger_log/map3/Log/'
           'littlemurloc_2026_10_24_09_57_03.log')
ex, lit, walk = base.ex, base.lit, base.walk


def builder(document, slot):
    b = base.Builder(document)
    b.index = 209996900100000 + slot * 10000
    return b


def note(b, label, *values):
    result = base.trace.log_node(b.node('unused')['element_id'], PREFIX + label)
    if values:
        pieces = [lit(PREFIX + label, 100003)]
        for label, value in values:
            pieces += [lit(' | ' + label + '=', 100003),
                       ex(100003, 'ANY_VAR_TO_STR', cp(value))]
        # Native STR_JOIN has two required and eight optional string operands.
        assert len(pieces) <= 10
        joined = ex(100003, 'STR_JOIN', *pieces[:2])
        joined.update(op_arg=pieces[2:] + [None] * (10-len(pieces)),
                      op_arg_enable=[True] * (len(pieces)-2) + [False] * (10-len(pieces)))
        result['args_list'][1] = joined
    return result


def stack(entity):
    return ex(100002, 'GET_MOD_STACK', cp(entity))


def xun_one(source):
    d = cp(source); b = builder(d, 0); tid = '893440004'
    t = d['trigger_dict'][tid]
    target = base.declare(d, tid, 'UNIT_ENTITY', '修复3_筹策结算目标')
    actor = base.var('UNIT_ENTITY', '目标单位', 'actor')
    owner, skill = ex(100006, 'ABILITY_OWNER'), ex(100014, 'CUR_ABILITY')
    # Manual input is resolved by the existing first IF, before this snapshot.
    head, effects = t['action'][:2], t['action'][2:]
    damage = base.one(effects, 'APPLY_DAMAGE', 893440004975729)
    add = base.one(effects, 'ADD_MODIFIER', 892944388000009)
    damage['args_list'][2] = cp(target)
    add['args_list'][0] = cp(target)
    target_sfx = next(n for n in walk(effects) if n.get('element_id') == 893440004975613)
    target_sfx['args_list'][1] = cp(target)
    idx = effects.index(add)
    status = effects[idx-1:idx+2]
    assert all(n['action_type'] == 'PRINT_MESSAGE_ACTION_TO_DIALOG' for n in (status[0], status[2]))
    guarded = base.live(b, target, [base.trace.log_node(
        b.node('unused')['element_id'], PREFIX+'荀彧1星/伤后目标仍有效，施加状态'), *status], owner)
    guarded['args_list'][2]['args_list'] = [note(b, '荀彧1星/伤后目标已移除，跳过状态')]
    inner = guarded['args_list'][1]['args_list'][0]
    inner['args_list'][2]['args_list'] = [note(b, '荀彧1星/伤后目标死亡或阵营改变，跳过状态')]
    effects[idx-1:idx+2] = [b.exists(skill, [base.live(b, owner, [guarded])])]
    t['action'] = [*head, b.set(target, actor),
                   b.exists(skill, [base.live(b, owner, [base.live(b, target, effects, owner)])])]
    return d


def summer_probe(source):
    d = cp(source); b = builder(d, 1)
    timer = base.one(d['trigger_dict']['1959489540']['action'], 'RUN_LOOP_TIMER')
    command = base.one(timer, 'UNIT_RELEASE_COMMAND')
    target = base.var('UNIT_ENTITY', '目标单位', 'actor')
    payload = [note(b, '夏侯渊3星/最终校验已通过，实际提交命令',
                    ('目标', target), ('猎印目标', base.var('UNIT_ENTITY', '修复_贯阵猎印目标', 'actor')),
                    ('同路人数', base.var('INTEGER', '修复_贯阵同路人数', 'actor'))),
               cp(command), note(b, '夏侯渊3星/实际命令动作已返回')]
    base.replace_action(timer, command['element_id'], payload)
    # The old registry logs surround this whole guard, not the real command.
    guard = next(n for n in walk(timer) if n.get('element_id') == 209996800120006)
    guard['args_list'][2]['args_list'] = [note(b, '夏侯渊3星/最终目标不存在，未提交命令')]
    inner = guard['args_list'][1]['args_list'][0]
    inner['args_list'][2]['args_list'] = [note(b, '夏侯渊3星/最终目标死亡或非敌方，未提交命令')]
    for offset, event in enumerate(['ABILITY_CS_START', 'ABILITY_PS_START', 'ABILITY_END']):
        tid = 2099969101 + offset
        name = '排查3_贯阵_' + event
        template = cp(d['trigger_dict']['225054724'])
        template.update(trigger_id=tid, trigger_name=name, condition=[], var_data=[{}, {}, []],
                        enabled=True, valid=True,
                        event=[dict(event_type=event, args_list=[], enable=True,
                                    element_id=b.node('unused')['element_id'])],
                        action=[note(b, '夏侯渊3星/生命周期/' + event)])
        d['trigger_dict'][str(tid)] = template
        d['local_variable'][str(tid)] = dict(variable_dict={}, variable_length_dict={})
        d['trigger_group_info'][0]['group'].append({'__tuple__': True, 'items': [tid, name]})
    return d


def zhang_five_probe(source):
    d = cp(source); b = builder(d, 2)
    core = base.var('MODIFIER_ENTITY', '修复2_破阵核心', 'actor')
    mark = base.var('MODIFIER_ENTITY', '修复2_破阵震慑', 'actor')
    timer = base.one(d['trigger_dict']['1959489540']['action'], 'RUN_LOOP_TIMER')
    command = base.one(timer, 'UNIT_RELEASE_COMMAND')
    base.replace_action(timer, command['element_id'], [
        note(b, '张辽5星/提交前层数', ('自身核心', stack(core)), ('敌方震慑', stack(mark))), cp(command)])
    t = d['trigger_dict']['893440004']
    current = ex(100076, 'GET_LAST_MODIFIER_INSTANCE', ex(100006, 'ABILITY_OWNER'), lit(134259689, 100046))
    t['action'].insert(1, b.exists(current, [note(b, '张辽5星/出手时核心层数', ('核心', stack(current)))]))
    return d


def zhang_core_probe(source):
    d = cp(source); b = builder(d, 3); current = ex(100076, 'CUR_MODIFIER')
    t = d['trigger_dict']['1418035204']
    for action in list(walk(t['action'])):
        if action.get('action_type') == 'ADD_BUFF_STACK':
            base.replace_action(t['action'], action['element_id'], [
                note(b, '张辽核心/加点前', ('核心', stack(current))), cp(action),
                note(b, '张辽核心/加点后', ('核心', stack(current)))])
        elif action.get('action_type') == 'SET_VARIABLE' and any(
                n.get('sub_type') == 'ADD_MODIFIER' for n in walk(action['args_list'][1])):
            base.replace_action(t['action'], action['element_id'], [cp(action),
                note(b, '张辽核心/添加震慑后', ('核心', stack(current)))])
    return d


def zhang_mark_probe(source):
    d = cp(source); b = builder(d, 4)
    t = d['trigger_dict']['1726324738']
    reset = base.one(t['action'], 'SET_BUFF_STACK')
    base.replace_action(t['action'], reset['element_id'], [
        note(b, '张辽震慑/失去触发核心重置', ('原核心层数', stack(reset['args_list'][0])),
             ('震慑剩余时间', ex(100000, 'GET_BUFF_TIME', ex(100076, 'CUR_MODIFIER')))), cp(reset)])
    return d


def build(root):
    patches = [xun_one, summer_probe, zhang_five_probe, zhang_core_probe, zhang_mark_probe]
    return {p: patch(base.trace.read(root/p)) for p, patch in zip(FILES, patches)}


def diagnostic_registry():
    records = {}
    for path in FILES:
        records[path] = [cp(n) for n in walk(base.trace.read(WORK/'candidate'/path))
                         if n.get('action_type') == 'PRINT_MESSAGE_ACTION_TO_DIALOG'
                         and PREFIX in json.dumps(n, ensure_ascii=False)]
    base.trace.save(WORK/'diagnostic-expressions.json', records)


def structural_check():
    manifest = base.trace.read(WORK/'manifest.json')
    original = set()
    for p in base.trace.files(WORK/'map3-before'):
        if p.suffix.lower() == '.json':
            try: doc = base.trace.read(p)
            except (ValueError, UnicodeError): continue
            original.update(n['element_id'] for n in walk(doc) if 'element_id' in n)
    added = set()
    for path in FILES:
        old = collections.Counter(n['element_id'] for n in walk(base.trace.read(WORK/'map3-before'/path)) if 'element_id' in n)
        new = collections.Counter(n['element_id'] for n in walk(base.trace.read(WORK/'candidate'/path)) if 'element_id' in n)
        assert all(v <= max(1, old[k]) for k, v in new.items()), path
        fresh = set(new)-set(old)
        assert not fresh & (original | added), path
        added |= fresh
    return dict(files=len(manifest['entries']), added_elements=len(added), no_id_collisions=True,
                gameplay_changed=['荀彧1星：统一结算目标，伤害后再校验目标'],
                diagnostic_only=['夏侯渊3星', '张辽5星、核心与震慑失去'])


def configure():
    base.WORK, base.FILES, base.build, base.PREFIX = WORK, FILES, build, PREFIX


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'refresh', 'publish', 'verify'])
    action = parser.parse_args().action
    configure()
    if action == 'prepare':
        base.prepare()
        shutil.copy2(LOG, WORK/'runtime-before.log')
        diagnostic_registry()
        print(json.dumps(structural_check(), ensure_ascii=False))
    elif action == 'refresh':
        base.refresh(); diagnostic_registry()
        print(json.dumps(structural_check(), ensure_ascii=False))
    elif action == 'publish':
        structural_check(); base.publish()
    else:
        result = base.verify()
        documents = [base.trace.read(ROOT/p) for p in FILES]
        result['all_triggers_valid'] = all(t.get('valid') for d in documents for t in d['trigger_dict'].values())
        assert result['all_triggers_valid']
        base.trace.save(WORK/'editor-verified.json', result)
        print(json.dumps(result))
