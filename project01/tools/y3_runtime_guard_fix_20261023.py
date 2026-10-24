"""Scoped native ECA repair, staged against the current map rather than old batches."""
from copy import deepcopy as cp
from pathlib import Path
from datetime import datetime
import argparse
import json
import math
import re
import shutil

import y3_skill_trace_manager as trace
from y3_sunshangxiang_orbit_fix import Builder, ex, lit, ref, global_int, walk

ROOT = Path('D:/littl/testTempFile/ProjectMonster02/maps/map3')
WORK = Path(__file__).resolve().parents[1] / 'tmp/runtime-guards-20261023'
FUNC = 'global_trigger/function/new/功能执行/'
LEGACY = 'global_trigger/function/业务逻辑/仆从召唤功能/主角单位更新赋值仆从伙伴属性.json'
FILES = [f'ability/{i}.json' for i in [134263515, 134228529, 134256840, 134263195]] + [
    FUNC + '根据升星属性给英雄队长赋值.json', LEGACY,
    FUNC + '根据升星属性给队伍小兵赋值.json',
    'global_trigger/function/new/参数返回/返回【兵种类型】根据存档编号.json', FUNC + '创建英雄队伍单位.json']


def builder(doc, slot):
    b = Builder(doc)
    b.index = 209996600100000 + slot * 10000
    return b


def boolean_var(kind, name, scope='local'):
    types = {'UNIT_NAME': (100116, 2), 'STRING': (100003, 2), 'INTEGER': (100002, 6)}
    t, s = types[kind]
    return ex(t, s, {'__tuple__': True, 'items': [kind, name, scope]})


def not_dead(b, unit):
    return b.cond('BOOL_NOT', ex(100001, 'UNIT_HAS_TAG', cp(unit), lit('已死亡', 100003)))


def eligible(b, unit, actions, owner=None, combat=False):
    checks = [b.cond('IS_UNIT_ALIVE', unit), not_dead(b, unit)]
    if owner is not None:
        checks.append(b.cond('IS_ALLY', unit, owner))
    if combat:
        checks.append(b.cmp(global_int('当前游戏进程阶段'), '==', lit(2)))
    return b.exists(unit, [b.branch(checks, actions)])


def with_else(branch, actions):
    branch['args_list'][2]['args_list'] = actions
    return branch


def declaration(doc, tid, kind, name):
    data = doc['local_variable'][tid]
    data['variable_dict'].setdefault(kind, {})[name] = None
    data['variable_length_dict'][name] = 0
    vd = doc['trigger_dict'][tid]['var_data']
    vd[0].setdefault(kind, {})[name] = None
    vd[1][name] = 0
    vd[2].append(name)
    return ref(kind, name)


def zhuge(source, slot=0):
    doc = cp(source); b = builder(doc, slot)
    tid = '58232837'; trigger = doc['trigger_dict'][tid]
    skill = ex(100014, 'CUR_ABILITY'); owner = ex(100006, 'ABILITY_OWNER')
    core = declaration(doc, tid, 'MODIFIER_ENTITY', '修复_空城谋略实例')
    body = trigger['action']; conditions = trigger['condition']
    lookup = ex(100076, 'GET_LAST_MODIFIER_INSTANCE', cp(owner), lit(134267407, 100046))
    for node in walk(body):
        if node.get('element_id') == 58232837974154:
            assert node['action_type'] == 'ADD_BUFF_STACK'
            node['args_list'][0] = cp(core)
        if node.get('action_type') == 'RUN_ONCE_TIMER_NO_SAVE':
            callback = next(a for a in node['args_list'] if isinstance(a, dict) and a.get('arg_type') == 100022)
            callback['args_list'] = [b.exists(skill, callback['args_list'])]
    body = patch_action_lists(body, lambda node: [b.exists(core, [node])]
        if node.get('element_id') == 58232837974154 else None)
    # Event conditions previously dereferenced the owner before validity checks.
    trigger['condition'] = []
    trigger['action'] = [b.exists(skill, [eligible(b, owner, [
        b.set(core, lookup), b.exists(core, [b.branch(conditions, body)])], combat=True)])]
    return doc


def patch_action_lists(value, transform):
    if isinstance(value, dict):
        if value.get('enable') is False:
            return cp(value)
        return {k: patch_action_lists(v, transform) for k, v in value.items()}
    if not isinstance(value, list):
        return value
    result = []
    for original in value:
        item = patch_action_lists(original, transform)
        replacement = transform(item) if isinstance(item, dict) and 'action_type' in item else None
        result.extend(replacement if replacement is not None else [item])
    return result


def liubei(source, resource, slot):
    doc = cp(source); b = builder(doc, slot)
    skill, owner = ex(100014, 'CUR_ABILITY'), ex(100006, 'ABILITY_OWNER')
    target, selected = ref('UNIT_ENTITY', '目标单位', 'actor'), ex(100006, 'FOR_EACH_SELECTED_UNIT')
    gain, cast = doc['trigger_dict']['1959489540'], doc['trigger_dict']['893440004']
    # Existing single-target search already checks existence before this tier.
    for node in walk(gain['action']):
        if node.get('action_type') != 'IF_THEN_ELSE':
            continue
        conditions = node['args_list'][0]['args_list']
        alive = [c for c in conditions if c.get('condition_type') == 'IS_UNIT_ALIVE']
        for condition in alive:
            unit = condition['args_list'][0]
            conditions += [not_dead(b, unit), b.cond('IS_ALLY', unit, owner)]

    def lowest_search(group):
        hp = lambda unit: ex(100000, 'ARITHMETIC_OPERATION',
            ex(100000, 'GET_HP_CUR', cp(unit)), lit('/', 100017),
            ex(100000, 'GET_UNIT_ATTR', cp(unit), lit('ATTR_RESULT', 100301), lit('hp_max', 100042)))
        assign = b.set(target, selected)
        choose = with_else(b.exists(target, [
            b.branch([b.cmp(hp(selected), '<', hp(target))], [b.fresh(assign)])]), [assign])
        tests = [b.cond('OR', ex(100021, 1,
            b.cond('UNIT_HAS_TAG', selected, lit('仆从伙伴', 100003)),
            b.cond('UNIT_HAS_TAG', selected, lit('阵型队长', 100003)))),
            b.cmp(ex(100000, 'GET_UNIT_ATTR', cp(selected), lit('ATTR_RESULT', 100301), lit('hp_max', 100042)), '>', lit(0.0, 100000))]
        return [b.set(target, ex(100006, 'NONE_UNIT')),
                b.node('PICK_UNIT_DO_ACTION', group,
                       ex(100022, 1, eligible(b, selected, [b.branch(tests, [choose])], owner=owner)))]

    if resource == 134263195:
        def replace_random(node):
            if node.get('element_id') == 1959489540974070:
                assert node['args_list'][1]['sub_type'] == 'RANDOM_UNIT_IN_UNIT_GROUP'
                return lowest_search(cp(node['args_list'][1]['args_list'][0]))
        gain['action'] = patch_action_lists(gain['action'], replace_random)

    def protect_command(node):
        if node.get('action_type') == 'IF_THEN_ELSE' and any(
            n.get('action_type') == 'UNIT_RELEASE_COMMAND' for n in walk(node['args_list'][1])):
            # Only the narrow final target gate, not the enclosing search/timer.
            if not any(n.get('action_type') == 'PICK_UNIT_DO_ACTION' for n in walk(node)):
                return [eligible(b, target, [node], owner=owner)]
    gain['action'] = patch_action_lists(gain['action'], protect_command)
    for node in walk(gain['action']):
        if node.get('action_type') == 'RUN_LOOP_TIMER':
            callback = node['args_list'][3]
            callback['args_list'] = [b.exists(skill, [eligible(b, owner, callback['args_list'], combat=True)])]

    actions = cast['action']
    manual = next(i for i, n in enumerate(actions) if n.get('element_id') == 893440004974041)
    prefix, effects = actions[:manual + 1], actions[manual + 1:]
    # Preserve base healing if a core was removed between selection and casting.
    for index, node in enumerate(effects):
        if node.get('element_id') == 893440004974050:
            lookup = ex(100076, 'GET_LAST_MODIFIER_INSTANCE', cp(owner), lit(134264323, 100046))
            effects[index] = with_else(b.exists(lookup, [node]), b.fresh(node['args_list'][2]['args_list']))
    if resource == 134263195:
        for node in walk(effects):
            if node.get('action_type') == 'PICK_UNIT_DO_ACTION':
                node['args_list'][1]['args_list'] = [eligible(b, selected, node['args_list'][1]['args_list'], owner=owner)]
                break
        guarded = effects
    else:
        guarded = [eligible(b, target, effects, owner=owner)]
    cast['action'] = [b.exists(skill, [eligible(b, owner, prefix + guarded, combat=True)])]
    return doc


def text_join(*parts):
    values = [lit(p, 100003) if isinstance(p, str) else ex(100003, 'ANY_VAR_TO_STR', cp(p)) for p in parts]
    while len(values) > 1:
        values = [ex(100003, 'STR_JOIN', values[i], values[i + 1]) if i + 1 < len(values) else values[i]
                  for i in range(0, len(values), 2)]
    for node in walk(values[0]):
        if node.get('sub_type') == 'STR_JOIN':
            node.update(op_arg=[None] * 8, op_arg_enable=[False] * 8)
    return values[0]


def notice(b, *parts):
    return b.node('PRINT_MESSAGE_ACTION_TO_DIALOG', lit(3, 100175), text_join('[配置校验] ', *parts))


def clamp_star(source, assignment_id, maximum, slot):
    doc = cp(source); b = builder(doc, slot); found = []
    def transform(node):
        if node.get('element_id') == assignment_id:
            variable = ex(100002, 6, cp(node['args_list'][0]['args_list'][0]))
            found.append(node)
            return [node, b.branch([b.cmp(variable, '>', lit(maximum))], [
                notice(b, '升星属性请求=', variable, '，当前配置最高=', lit(maximum), '；仅按最高配置档计算，不修改存档。'),
                b.set(variable, lit(maximum))])]
    doc['action'] = patch_action_lists(doc['action'], transform)
    assert len(found) == 1
    return doc


def minion_star(source, slot):
    doc = cp(source); b = builder(doc, slot)
    unit = ex(100006, 11, {'__tuple__': True, 'items': ['UNIT_ENTITY', '赋值小兵', 'local']})
    traversal = doc['action'][0]; original = traversal['args_list'][1]['args_list'][0]
    condition = original['args_list'][0]['args_list'].pop(0)
    assert condition['element_id'] == 1105785531000073
    condition['enable'] = True
    traversal['args_list'][1]['args_list'] = [b.branch([condition], [original])]
    doc['action'] = [b.exists(unit, doc['action'])]
    return doc


def minion_type(source, slot):
    doc = cp(source); b = builder(doc, slot)
    result = boolean_var('UNIT_NAME', 'result')
    current = cp(doc['action'][1]['args_list'][0]['args_list'][0]['args_list'][0])
    assert current['sub_type'] == 'GET_STRING_TABLE_VAR_ND'
    hero = ex(100116, 'GET_UNIT_NAME_TABLE_VAR_ND', cp(current['args_list'][0]),
              cp(current['args_list'][1]), lit('单位类型', 100003))
    fallback = ex(100116, 'GET_UNIT_NAME_KV', cp(hero), lit('队伍小兵类型', 100003))
    unknown = b.cmp(result, '==', ex(100116, 'NONE_UNIT_KEY'), 'UNIT_CLASS_COMPARE')
    hero_known = b.cmp(hero, '!=', ex(100116, 'NONE_UNIT_KEY'), 'UNIT_CLASS_COMPARE')
    doc['action'].insert(-1, b.branch([unknown], [b.branch([hero_known], [
        b.set(result, fallback), notice(b, '带领兵种=', current,
            ' 无法识别，改用该英雄物编默认兵种=', result, '；不修改存档。')])]))
    return doc


def create_team(source, slot):
    doc = cp(source); b = builder(doc, slot)
    unit = ex(100006, 11, {'__tuple__': True, 'items': ['UNIT_ENTITY', '小兵', 'local']})
    leader = ex(100006, 11, {'__tuple__': True, 'items': ['UNIT_ENTITY', '队长单位', 'local']})
    for node in walk(doc['action']):
        if node.get('action_type') == 'FOR_INT_DO_ACTION_NEW' and node.get('enable') is not False:
            body = node['args_list'][3]['args_list']
            index = next(i for i, a in enumerate(body) if a.get('element_id') == 551875248989014)
            body[index + 1:] = [with_else(b.exists(unit, body[index + 1:]), [
                notice(b, '创建小兵未得到有效单位，跳过后续赋值。')])]
            break
    doc['action'] = [b.exists(leader, doc['action'])]
    return doc


def highest_star(root):
    table = trace.read(root / 'tables/仆从升星属性提升表.json')['table_data']['data']
    columns = table[0]
    stars = [int(match.group(1)) for name in columns
             if isinstance(name, str) and (match := re.fullmatch(r'(\d+)星属性类型数组', name))
             and name.replace('类型', '数值') in columns]
    # Validate every configured positive-star pair, not just the broken hero.
    for row in table[2:]:
        if not row or not row[0]:
            continue
        for star in stars:
            if star == 0:
                continue
            types = str(row[columns.index(f'{star}星属性类型数组')]).split('-')
            values = str(row[columns.index(f'{star}星属性数值数组')]).split('-')
            assert len(types) == len(values)
            assert all(int(t) > 0 for t in types)
            assert all(math.isfinite(float(v)) for v in values)
    return max(stars)


def build(root):
    sources = {p: trace.read(root / p) for p in FILES}
    maximum = highest_star(root)
    candidates = {}
    candidates[FILES[0]] = zhuge(sources[FILES[0]])
    for slot, resource in enumerate([134228529, 134256840, 134263195], 1):
        path = f'ability/{resource}.json'
        candidates[path] = liubei(sources[path], resource, slot)
    candidates[FILES[4]] = clamp_star(sources[FILES[4]], 1115783868000144, maximum, 4)
    candidates[LEGACY] = clamp_star(sources[LEGACY], 1574691332000141, maximum, 5)
    candidates[FILES[6]] = minion_star(sources[FILES[6]], 6)
    candidates[FILES[7]] = minion_type(sources[FILES[7]], 7)
    candidates[FILES[8]] = create_team(sources[FILES[8]], 8)
    return candidates, maximum


def prepare():
    assert not WORK.exists(), 'Do not overwrite an earlier repair or backup'
    WORK.mkdir(parents=True)
    shutil.copytree(ROOT, WORK / 'map3-before', ignore=shutil.ignore_patterns('.git'))
    shutil.copy2(ROOT.parents[1] / 'header.project', WORK / 'header.project.before')
    baseline = {p.relative_to(ROOT).as_posix(): trace.sha(p) for p in trace.files(ROOT)}
    candidates, maximum = build(WORK / 'map3-before')
    registry = trace.read(trace.REGISTRY)
    entries = []
    for relative, document in candidates.items():
        if relative in registry['entries']:
            trace.checked_nodes(document, registry['entries'][relative]['logs'])
        trace.save(WORK / 'candidate' / relative, document)
        entries.append({'path': relative, 'before': baseline[relative],
                        'after': trace.sha(WORK / 'candidate' / relative),
                        'semantic_after': trace.digest(document)})
    manifest = {'map': str(ROOT), 'created': datetime.now().isoformat(), 'entries': entries,
                'baseline': baseline, 'highest_configured_star': maximum,
                'registry_sha': trace.sha(trace.REGISTRY),
                'scope': 'Zhuge lifecycle, Liu Bei living friendly targets, star bounds and minion assignment.'}
    trace.save(WORK / 'manifest.json', manifest)
    print(json.dumps({'prepared_files': len(entries), 'highest_configured_star': maximum,
                      'full_backup_files': len(baseline)}, ensure_ascii=False))


def verify():
    manifest = trace.read(WORK / 'manifest.json')
    def saved_semantics(document):
        document = cp(document)
        for node in walk(document):
            if node.get('sub_type') == 'STR_JOIN' and 'op_arg' not in node and 'op_arg_enable' not in node:
                node.update(op_arg=[None] * 8, op_arg_enable=[False] * 8)
        return trace.digest(document)
    for entry in manifest['entries']:
        candidate = WORK / 'candidate' / entry['path']
        assert trace.sha(candidate) == entry['after']
        assert saved_semantics(trace.read(ROOT / entry['path'])) == saved_semantics(trace.read(candidate)), entry['path']
    registry = trace.read(trace.REGISTRY)
    for relative, entry in registry['entries'].items():
        trace.checked_nodes(trace.read(ROOT / relative), entry['logs'])
    return {'files': len(manifest['entries']), 'candidate_semantics_preserved': True,
            'all_hero_trace_nodes_preserved': True}


def refresh():
    manifest = trace.read(WORK / 'manifest.json')
    assert not (WORK / 'published.json').exists(), 'Never refresh an already published repair'
    for relative, before in manifest['baseline'].items():
        assert trace.sha(ROOT / relative) == before, 'Map changed while refreshing candidates'
    candidates, maximum = build(WORK / 'map3-before')
    for entry in manifest['entries']:
        document = candidates[entry['path']]
        trace.save(WORK / 'candidate' / entry['path'], document)
        entry['after'] = trace.sha(WORK / 'candidate' / entry['path'])
        entry['semantic_after'] = trace.digest(document)
    manifest['draft_revision'] = manifest.get('draft_revision', 0) + 1
    manifest['highest_configured_star'] = maximum
    trace.save(WORK / 'manifest.json', manifest)
    print(json.dumps({'refreshed_candidates': len(candidates), 'revision': manifest['draft_revision']}))


def publish():
    manifest = trace.read(WORK / 'manifest.json')
    assert not (WORK / 'published.json').exists()
    assert trace.sha(trace.REGISTRY) == manifest['registry_sha']
    for relative, before in manifest['baseline'].items():
        assert trace.sha(ROOT / relative) == before, 'Concurrent change: ' + relative
    for entry in manifest['entries']:
        assert trace.sha(WORK / 'candidate' / entry['path']) == entry['after']
    for entry in manifest['entries']:
        shutil.copy2(WORK / 'candidate' / entry['path'], ROOT / entry['path'])
    changed = {e['path'] for e in manifest['entries']}
    for relative, before in manifest['baseline'].items():
        if relative not in changed:
            assert trace.sha(ROOT / relative) == before
    receipt = verify(); receipt['published'] = datetime.now().isoformat()
    trace.save(WORK / 'published.json', receipt)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'refresh', 'publish', 'verify'])
    action = parser.parse_args().action
    if action == 'prepare':
        prepare()
    elif action == 'publish':
        publish()
    elif action == 'refresh':
        refresh()
    else:
        result = verify(); trace.save(WORK / 'editor-verified.json', result)
        print(json.dumps(result, ensure_ascii=False))
