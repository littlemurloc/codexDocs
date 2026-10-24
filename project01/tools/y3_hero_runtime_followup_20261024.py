"""Scoped repairs and literal diagnostics; never regenerate an old hero batch."""
from copy import deepcopy as cp
from datetime import datetime
from pathlib import Path
import argparse
import json
import shutil

import y3_skill_trace_manager as trace
from y3_sunshangxiang_orbit_fix import Builder, ex, lit, ref, global_int, walk

ROOT = Path('D:/littl/testTempFile/ProjectMonster02/maps/map3')
WORK = Path(__file__).resolve().parents[1] / 'tmp/hero-followup-20261024'
FILES = ['ability/134256160.json', 'ability/134255446.json',
         'ability/134240904.json', 'ability/134259902.json',
         'ability/134283925.json', 'ability/134260801.json',
         'modifier/134283902.json', 'modifier/134232159.json']
PREFIX = '[技能排查/20261024] '
CONSUMING = '修复_张辽五星彩消耗中'


def builder(doc, slot):
    b = Builder(doc)
    b.index = 209996700100000 + slot * 10000
    return b


def var(kind, name, scope='local'):
    if kind == 'UNIT_GROUP':
        return ex(100026, 14, {'__tuple__': True, 'items': [kind, name, scope]})
    return ref(kind, name, scope)


def declare(doc, tid, kind, name, default=0, actor=False):
    if actor:
        doc['variable_dict'].setdefault(kind, {})[name] = cp(default)
        doc['variable_length_dict'][name] = 0
        doc['variable_group_info'].append({'__tuple__': True, 'items': [name, name]})
        return var(kind, name, 'actor')
    d = doc['local_variable'][tid]
    d['variable_dict'].setdefault(kind, {})[name] = cp(default)
    d['variable_length_dict'][name] = 0
    vd = doc['trigger_dict'][tid]['var_data']
    vd[0].setdefault(kind, {})[name] = cp(default)
    vd[1][name] = 0
    vd[2].append(name)
    return var(kind, name)


def otherwise(branch, body):
    branch['args_list'][2]['args_list'] = body
    return branch


def not_dead(b, unit):
    return b.cond('BOOL_NOT', ex(100001, 'UNIT_HAS_TAG', cp(unit), lit('已死亡', 100003)))


def live(b, unit, body, owner=None):
    checks = [b.cond('IS_UNIT_ALIVE', unit), not_dead(b, unit)]
    if owner is not None:
        checks.append(b.cond('IS_ENEMY', unit, owner))
    return b.exists(unit, [b.branch(checks, body)])


def kv(kind, entity, key):
    sub = {100002: 'GET_INTEGER_KV', 100001: 'GET_BOOLEAN_KV'}[kind]
    return ex(kind, sub, cp(entity), lit(key, 100003))


def write(b, entity, key, value):
    return b.node('SET_ENTITY_KV', cp(entity), lit(key, 100003), cp(value))


def note(b, message):
    return trace.log_node(b.node('unused')['element_id'], PREFIX + message)


def one(value, kind, eid=None):
    nodes = [n for n in walk(value) if n.get('action_type') == kind
             and (eid is None or n.get('element_id') == eid)]
    assert len(nodes) == 1, (kind, eid, len(nodes))
    return nodes[0]


def replace_action(value, eid, replacement):
    if isinstance(value, dict):
        for child in value.values():
            replace_action(child, eid, replacement)
    elif isinstance(value, list):
        for i in range(len(value) - 1, -1, -1):
            child = value[i]
            if isinstance(child, dict) and child.get('element_id') == eid:
                value[i:i + 1] = replacement
            else:
                replace_action(child, eid, replacement)


def lane_assignment(b, unit, result, captain):
    def direct(source, key):
        return b.branch([b.cond('HAS_KV_ANY', source, lit(key, 100003))],
                        [b.set(result, kv(100002, source, key))])
    body = [b.set(result, lit(0)), direct(unit, '归属阵型编号'),
            b.branch([b.cmp(result, '<=', lit(0))], [direct(unit, '阵型编号')])]
    fallback = [b.set(captain, ex(100006, 'GET_UNIT_ENTITY_KV', cp(unit), lit('所属英雄', 100003))),
                b.exists(captain, [direct(captain, '归属阵型编号'),
                    b.branch([b.cmp(result, '<=', lit(0))], [direct(captain, '阵型编号')])])]
    body.append(b.branch([b.cmp(result, '<=', lit(0)),
                         b.cond('HAS_KV_ANY', unit, lit('所属英雄', 100003))], fallback))
    return body


def same_lane(b, left, right):
    # The map groups 1/4/7, 2/5/8 and 3/6/9 as its three lanes.
    groups = []
    for numbers in ((1, 4, 7), (2, 5, 8), (3, 6, 9)):
        def inside(value):
            return b.cond('OR', ex(100021, 1, *[b.cmp(value, '==', lit(n)) for n in numbers]))
        groups.append(b.cond('AND', ex(100021, 1, inside(left), inside(right))))
    return b.cond('OR', ex(100021, 1, *groups))


def summer_three(source):
    d = cp(source); b = builder(d, 0); tid = '1959489540'
    timer = one(d['trigger_dict'][tid]['action'], 'RUN_LOOP_TIMER')
    pick = one(timer, 'PICK_UNIT_DO_ACTION')
    original_condition = pick['args_list'][1]['args_list'][0]
    body = original_condition['args_list'][1]['args_list']
    skill, owner = ex(100014, 'CUR_ABILITY'), ex(100006, 'ABILITY_OWNER')
    selected = ex(100006, 'FOR_EACH_SELECTED_UNIT')
    target = declare(d, tid, 'UNIT_ENTITY', '修复_贯阵猎印目标')
    core = declare(d, tid, 'MODIFIER_ENTITY', '修复_贯阵猎印')
    lane = declare(d, tid, 'INTEGER', '修复_贯阵目标阵位')
    other_lane = declare(d, tid, 'INTEGER', '修复_贯阵候选阵位')
    captain = declare(d, tid, 'UNIT_ENTITY', '修复_贯阵候选队长')
    count = declare(d, tid, 'INTEGER', '修复_贯阵同路人数')
    group = cp(pick['args_list'][0])
    # A nested unit iterator changes FOR_EACH_SELECTED_UNIT; snapshot the target.
    for n in walk(body):
        if n.get('action_type') == 'SET_VARIABLE':
            n['args_list'][1] = cp(target)
    count_body = [*lane_assignment(b, selected, other_lane, captain),
        b.branch([same_lane(b, lane, other_lane)],
                 [b.set(count, ex(100002, 'INT_PLUS_ONE', cp(count)))])]
    count_pick = b.node('PICK_UNIT_DO_ACTION', cp(group),
                       ex(100022, 1, live(b, selected, count_body, owner)))
    chosen = [b.set(target, selected), b.set(core, ex(100076, 'GET_LAST_MODIFIER_INSTANCE',
              cp(target), lit(134232159, 100046))), b.exists(core, [b.branch([
                  b.cmp(ex(100006, 'GET_BUFF_SOURCE', cp(core)), '==', owner, 'UNIT_COMPARE')], [
                      *lane_assignment(b, target, lane, captain), b.set(count, lit(0)),
                      count_pick, b.branch([b.cmp(count, '>=', lit(2))], body)])])]
    pick['args_list'][1]['args_list'] = [live(b, selected, [b.branch([
        b.cond('UNIT_HAS_MODIFIER', selected, lit(134232159, 100046))], chosen)], owner)]
    helper = ex(100001, '97642c3d802a5935a73289745a266ac8', cp(owner))
    helper.update(call_rt_index=0, op_arg=[], op_arg_enable=[])
    guards = [b.cmp(ex(100000, 'ABILITY_CD_LEFT_TIME', cp(skill)), '==', lit(0)),
              b.cmp(global_int('当前游戏进程阶段'), '==', lit(2)),
              b.cmp(kv(100001, owner, '自动施法'), '==', lit(True, 100001), 'BOOL_COMPARE'),
              b.cmp(helper, '==', lit(True, 100001), 'BOOL_COMPARE')]
    timer['args_list'][3]['args_list'] = [b.exists(skill, [live(b, owner, [b.branch(guards, [pick])])])]
    return d


def summer_six(source):
    d = cp(source); b = builder(d, 1); tid = '1051000836'
    t = d['trigger_dict'][tid]
    assert t['event'][0]['args_list'][0]['args_list'] == ['ET_MODIFIER_LAYER_CHANGE']
    t['event'][0]['args_list'][0]['args_list'] = ['ET_LOSS_MODIFIER']
    history = declare(d, tid, 'UNIT_GROUP', '修复_识破已触发目标组', [], actor=True)
    wave = declare(d, tid, 'INTEGER', '修复_识破波次', -1, actor=True)
    skill, owner = ex(100014, 'CUR_ABILITY'), ex(100006, 'ABILITY_OWNER')
    event_buff = ex(100076, 'GET_MODIFIER_FROM_EVENT')
    target = declare(d, tid, 'UNIT_ENTITY', '修复_识破目标')
    source_unit = declare(d, tid, 'UNIT_ENTITY', '修复_识破来源')
    source_core = declare(d, tid, 'MODIFIER_ENTITY', '修复_识破原核心')
    old = t['action']
    # Keep all original trace nodes and the original six-second effect payload.
    add = one(old, 'ADD_MODIFIER')
    add['args_list'][0] = cp(target)
    assert old[0]['action_type'] == 'PRINT_MESSAGE_ACTION_TO_DIALOG'
    head, effect = old[:1], old[1:]
    effect.insert(0, b.node('GROUP_ADD_UNIT', cp(target), cp(history)))
    reset = [b.node('CLEAR_GROUP', cp(history)), b.set(wave, global_int('当前进程所在波次编号'))]
    fresh_wave = b.branch([b.cmp(wave, '!=', global_int('当前进程所在波次编号'))], cp(reset))
    unseen = otherwise(b.branch([b.cond('UNIT_IN_GROUP', target, history)], []), effect)
    # Loss events provide the departing Buff. Do not re-look it up on the unit.
    qualified = [b.set(target, ex(100006, 'MODIFIER_OWNER')),
                 b.set(source_unit, ex(100006, 'GET_BUFF_SOURCE', cp(event_buff))),
                 b.exists(source_unit, [b.branch([
                    b.cmp(source_unit, '==', owner, 'UNIT_COMPARE'),
                    b.cond('HAS_KV_ANY', event_buff, lit('修复_猎印波次', 100003)),
                    b.cond('HAS_KV_ANY', event_buff, lit('修复_猎印来源核心', 100003))], [
                      b.set(source_core, ex(100076, 'GET_MODIFIER_ENTITY_KV', cp(event_buff),
                                            lit('修复_猎印来源核心', 100003))),
                      b.exists(source_core, [b.branch([
                        b.cmp(kv(100002, event_buff, '修复_猎印波次'), '==', global_int('当前进程所在波次编号')),
                        b.cmp(ex(100076, 'GET_LAST_MODIFIER_INSTANCE', cp(owner), lit(134282266, 100046)),
                              '==', source_core, 'MODIFIER_COMPARE')], [live(b, target, [
                      b.branch([b.cond('OR', ex(100021, 1,
                        b.cond('UNIT_HAS_TAG', target, lit('仆从伙伴', 100003)),
                        b.cond('UNIT_HAS_TAG', target, lit('阵型队长', 100003)))),
                        b.cmp(ex(100000, 'GET_BUFF_TIME', cp(event_buff)), '<=', lit(0))],
                        [fresh_wave, unseen])], owner)])])])])]
    t['condition'] = []
    t['action'] = [b.exists(skill, [live(b, owner, [b.branch([
        b.cmp(global_int('当前游戏进程阶段'), '==', lit(2)),
        b.cmp(ex(100046, 'GET_MODIFIER_ENTITY_METATYPE', cp(event_buff)),
              '==', lit(134232159, 100046), 'MODIFIER_CLASS_COMPARE')], [*head, *qualified])])])]
    d['trigger_dict']['1444225029']['action'] += b.fresh(reset)
    return d


def mark_snapshot(source):
    d = cp(source); b = builder(d, 8)
    current, owner = ex(100076, 'CUR_MODIFIER'), ex(100006, 'MODIFIER_RELEASER')
    core = ex(100076, 'GET_LAST_MODIFIER_INSTANCE', cp(owner), lit(134282266, 100046))
    d['trigger_dict']['1485688834']['action'] += [
        write(b, current, '修复_猎印波次', global_int('当前进程所在波次编号')),
        b.exists(owner, [write(b, current, '修复_猎印来源核心', core)])]
    return d


def zhang_consume(source):
    d = cp(source); b = builder(d, 2)
    consume = one(d['trigger_dict']['893440004']['action'], 'SET_BUFF_STACK')
    core = cp(consume['args_list'][0])
    replace_action(d['trigger_dict']['893440004']['action'], consume['element_id'], [
        write(b, core, CONSUMING, lit(True, 100001)), consume,
        b.exists(core, [write(b, core, CONSUMING, lit(False, 100001))])])
    return d


def zhang_six(source):
    d = cp(source); b = builder(d, 3)
    t = d['trigger_dict']['1051000836']
    matches = [n for n in walk(t['action']) if n.get('action_type') == 'IF_THEN_ELSE'
               and any(c.get('condition_type') == 'FLOAT_COMPARE'
                       and any(x.get('sub_type') == 'GET_MODIFIER_LAYER_CHANGE_VALUE' for x in walk(c))
                       for c in n['args_list'][0]['args_list'])]
    assert len(matches) == 1
    matches[0]['args_list'][0]['args_list'] += [
        b.cmp(kv(100001, ex(100076, 'GET_MODIFIER_FROM_EVENT'), CONSUMING),
              '==', lit(True, 100001), 'BOOL_COMPARE'),
        b.cmp(global_int('当前游戏进程阶段'), '==', lit(2))]
    return d


def guard_buff_read(source, slot, trigger_id, node_id, modifier_id, owner):
    d = cp(source); b = builder(d, slot); t = d['trigger_dict'][trigger_id]
    target = [n for n in walk(t) if n.get('element_id') == node_id]
    assert len(target) == 1
    # An ordered outer branch protects the existing inner layer comparison.
    matches = [n for n in walk(t['action']) if n.get('action_type') == 'IF_THEN_ELSE'
               and target[0] in n['args_list'][0]['args_list']]
    assert len(matches) == 1
    old = matches[0]
    lookup = ex(100076, 'GET_LAST_MODIFIER_INSTANCE', cp(owner), lit(modifier_id, 100046))
    wrapped = b.exists(owner, [b.exists(lookup, [cp(old)])])
    replace_action(t['action'], old['element_id'], [wrapped])
    return d


def diagnose_zhang(source):
    d = cp(source); b = builder(d, 4); tid = '1959489540'
    timer = one(d['trigger_dict'][tid]['action'], 'RUN_LOOP_TIMER')
    body = timer['args_list'][3]['args_list']
    # The first search is disabled; instrument only the active marked-target scan.
    picks = [n for n in walk(body) if n.get('action_type') == 'PICK_UNIT_DO_ACTION']
    pick = next(n for n in picks if n['args_list'][0].get('sub_type') == 14)
    total = declare(d, tid, 'INTEGER', '排查_张辽5候选数')
    full = declare(d, tid, 'INTEGER', '排查_张辽5满层数')
    last = declare(d, tid, 'INTEGER', '排查_张辽5上次状态', -1, actor=True)
    current = declare(d, tid, 'INTEGER', '排查_张辽5本次状态')
    selected = ex(100006, 'FOR_EACH_SELECTED_UNIT')
    mark = ex(100076, 'GET_LAST_MODIFIER_INSTANCE', cp(selected), lit(134259870, 100046))
    pick['args_list'][1]['args_list'].insert(0, b.set(total, ex(100002, 'INT_PLUS_ONE', cp(total))))
    pick['args_list'][1]['args_list'].insert(1, b.exists(selected, [b.branch([
        b.cond('UNIT_HAS_MODIFIER', selected, lit(134259870, 100046))], [b.exists(mark, [b.branch([
            b.cmp(ex(100002, 'GET_MOD_STACK', cp(mark)), '>=',
                  ex(100002, 'GET_MOD_STACK_MAX', cp(mark)))],
            [b.set(full, ex(100002, 'INT_PLUS_ONE', cp(full)))])])])]))
    body[:0] = [b.set(total, lit(0)), b.set(full, lit(0))]
    choose = otherwise(b.branch([b.cmp(total, '==', lit(0))], [b.set(current, lit(0))]), [
        otherwise(b.branch([b.cmp(full, '==', lit(0))], [b.set(current, lit(1))]), [b.set(current, lit(2))])])
    messages = [b.branch([b.cmp(current, '==', lit(code))], [note(b, text)]) for code, text in [
        (0, '张辽5星/缓存搜索组为空'), (1, '张辽5星/缓存组有单位但没有满层震慑'),
        (2, '张辽5星/缓存组存在满层震慑目标')]]
    body += [choose, b.branch([b.cmp(current, '!=', last)], [*messages, b.set(last, current)])]
    return d


def diagnose_sunce(source):
    d = cp(source); b = builder(d, 5)
    t = d['trigger_dict']['1051000836']
    mover = one(t['action'], 'CREATE_STRAIGHT_MOVER')
    consume = one(t['action'], 'SET_BUFF_STACK')
    replace_action(t['action'], consume['element_id'], [consume, note(b, '孙策2星/扣点动作已返回')])
    # Label each native callback slot without assuming undocumented slot ordering.
    for slot in (5, 6, 7):
        mover['args_list'][slot]['args_list'].insert(0, note(b, f'孙策2星/运动器回调槽{slot}进入'))
    replace_action(t['action'], mover['element_id'], [note(b, '孙策2星/即将创建运动器'), mover,
                                                     note(b, '孙策2星/创建运动器动作已返回')])
    guards = [n for n in walk(t['action']) if n.get('action_type') == 'IF_THEN_ELSE'
              and any(x.get('action_type') == 'CREATE_STRAIGHT_MOVER'
                      for x in walk(n['args_list'][1]))
              and not n['args_list'][2]['args_list']]
    # Do not log unrelated global Buff changes. Only guards after consumption.
    for n in guards:
        checks = n['args_list'][0]['args_list']
        text = json.dumps(checks, ensure_ascii=False)
        if 'P2_latest_' in text:
            n['args_list'][2]['args_list'] = [note(b, f'孙策2星/运动器前置检查未通过#{n["element_id"]}')]
    return d


def build(root):
    src = {p: trace.read(root / p) for p in FILES}
    out = {FILES[0]: summer_three(src[FILES[0]]), FILES[1]: summer_six(src[FILES[1]]),
           FILES[2]: diagnose_zhang(zhang_consume(src[FILES[2]])),
           FILES[3]: zhang_six(src[FILES[3]]), FILES[4]: diagnose_sunce(src[FILES[4]])}
    out[FILES[5]] = guard_buff_read(src[FILES[5]], 6, '1959489540', 1959489540974493,
                                  134242622, ex(100006, 'ABILITY_OWNER'))
    out[FILES[6]] = guard_buff_read(src[FILES[6]], 7, '594665475', 594665475000091,
                                  134283923, ex(100006, 'MODIFIER_OWNER'))
    out[FILES[7]] = mark_snapshot(src[FILES[7]])
    return out


def prepare(resume=False):
    if resume:
        assert not (WORK / 'manifest.json').exists(), 'Do not replace a completed stage'
        assert (WORK / 'header.project.before').is_file()
        before = {p.relative_to(WORK / 'map3-before').as_posix(): trace.sha(p)
                  for p in trace.files(WORK / 'map3-before')}
        current = {p.relative_to(ROOT).as_posix(): trace.sha(p) for p in trace.files(ROOT)}
        assert before == current, 'Map changed after the incomplete preparation'
    else:
        assert not WORK.exists(), 'Never overwrite a previous recovery backup'
        WORK.mkdir(parents=True)
        shutil.copytree(ROOT, WORK / 'map3-before', ignore=shutil.ignore_patterns('.git'))
        shutil.copy2(ROOT.parents[1] / 'header.project', WORK / 'header.project.before')
    baseline = {p.relative_to(ROOT).as_posix(): trace.sha(p) for p in trace.files(ROOT)}
    candidates = build(WORK / 'map3-before')
    registry = trace.read(trace.REGISTRY)
    entries, diagnostics = [], {}
    for relative, document in candidates.items():
        if relative in registry['entries']:
            trace.checked_nodes(document, registry['entries'][relative]['logs'])
        trace.save(WORK / 'candidate' / relative, document)
        entries.append({'path': relative, 'before': baseline[relative],
                        'after': trace.sha(WORK / 'candidate' / relative)})
        logs = [{'element_id': n['element_id'], 'message': n['args_list'][1]['args_list'][0]}
                for n in walk(document) if n.get('action_type') == 'PRINT_MESSAGE_ACTION_TO_DIALOG'
                and isinstance(n['args_list'][1]['args_list'][0], str)
                and n['args_list'][1]['args_list'][0].startswith(PREFIX)]
        if logs:
            diagnostics[relative] = logs
    trace.save(WORK / 'manifest.json', {'map': str(ROOT), 'entries': entries, 'baseline': baseline,
        'created': datetime.now().isoformat(), 'registry_sha': trace.sha(trace.REGISTRY)})
    trace.save(WORK / 'diagnostics.json', diagnostics)
    print(json.dumps({'prepared': len(entries), 'backup_files': len(baseline),
                      'diagnostic_nodes': sum(map(len, diagnostics.values()))}))


def verify():
    manifest = trace.read(WORK / 'manifest.json')
    for entry in manifest['entries']:
        assert trace.sha(WORK / 'candidate' / entry['path']) == entry['after']
        assert trace.digest(trace.read(ROOT / entry['path'])) == trace.digest(
            trace.read(WORK / 'candidate' / entry['path'])), entry['path']
    for relative, entry in trace.read(trace.REGISTRY)['entries'].items():
        trace.checked_nodes(trace.read(ROOT / relative), entry['logs'])
    return {'files': len(manifest['entries']), 'semantics_match': True, 'original_trace_nodes_preserved': True}


def refresh():
    manifest = trace.read(WORK / 'manifest.json')
    assert not (WORK / 'published.json').exists()
    for relative, sha in manifest['baseline'].items():
        assert trace.sha(ROOT / relative) == sha, 'Concurrent edit: ' + relative
    candidates = build(WORK / 'map3-before')
    entries, diagnostics = [], {}
    registry = trace.read(trace.REGISTRY)
    for relative, document in candidates.items():
        if relative in registry['entries']:
            trace.checked_nodes(document, registry['entries'][relative]['logs'])
        trace.save(WORK / 'candidate' / relative, document)
        entries.append({'path': relative, 'before': manifest['baseline'][relative],
                        'after': trace.sha(WORK / 'candidate' / relative)})
        logs = [{'element_id': n['element_id'], 'message': n['args_list'][1]['args_list'][0]}
                for n in walk(document) if n.get('action_type') == 'PRINT_MESSAGE_ACTION_TO_DIALOG'
                and isinstance(n['args_list'][1]['args_list'][0], str)
                and n['args_list'][1]['args_list'][0].startswith(PREFIX)]
        if logs:
            diagnostics[relative] = logs
    manifest['entries'] = entries
    manifest['draft_revision'] = manifest.get('draft_revision', 0) + 1
    trace.save(WORK / 'manifest.json', manifest)
    trace.save(WORK / 'diagnostics.json', diagnostics)
    print(json.dumps({'refreshed': len(entries), 'revision': manifest['draft_revision']}))


def publish():
    manifest = trace.read(WORK / 'manifest.json')
    assert not (WORK / 'published.json').exists()
    assert trace.sha(trace.REGISTRY) == manifest['registry_sha']
    for relative, sha in manifest['baseline'].items():
        assert trace.sha(ROOT / relative) == sha, 'Concurrent edit: ' + relative
    for entry in manifest['entries']:
        assert trace.sha(WORK / 'candidate' / entry['path']) == entry['after']
    for entry in manifest['entries']:
        shutil.copy2(WORK / 'candidate' / entry['path'], ROOT / entry['path'])
    changed = {e['path'] for e in manifest['entries']}
    for relative, sha in manifest['baseline'].items():
        if relative not in changed:
            assert trace.sha(ROOT / relative) == sha
    result = verify()
    trace.save(WORK / 'published.json', {**result, 'published': datetime.now().isoformat()})
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'resume', 'refresh', 'publish', 'verify'])
    action = parser.parse_args().action
    if action == 'prepare':
        prepare()
    elif action == 'resume':
        prepare(resume=True)
    elif action == 'refresh':
        refresh()
    elif action == 'publish':
        publish()
    else:
        result = verify()
        trace.save(WORK / 'editor-verified.json', result)
        print(json.dumps(result))
