"""Second, separately backed-up stage after the 09:40 real-game retest."""
from copy import deepcopy as cp
from pathlib import Path
import argparse
import json

import y3_hero_runtime_followup_20261024 as first

ROOT = first.ROOT
FIRST_WORK = first.WORK
WORK = first.WORK.parent / 'hero-followup-20261024-r2'
FILES = ['ability/134240904.json', 'ability/134283925.json',
         'ability/134256160.json', 'ability/134263364.json']
PREFIX = '[技能排查/20261024-r2] '
ex, lit, ref, walk = first.ex, first.lit, first.ref, first.walk


def builder(doc, slot):
    b = first.Builder(doc)
    b.index = 209996800100000 + slot * 10000
    return b


def log(b, message):
    return first.trace.log_node(b.node('unused')['element_id'], PREFIX + message)


def promote(doc, tid, names):
    """Callbacks and nested dispatch must not rely on an outer local frame."""
    local = doc['local_variable'][tid]
    declarations = doc['trigger_dict'][tid]['var_data']
    for kind, variables in list(local['variable_dict'].items()):
        for name in list(variables):
            if name not in names:
                continue
            default = variables.pop(name)
            doc['variable_dict'].setdefault(kind, {})[name] = cp(default)
            doc['variable_length_dict'][name] = 0
            doc['variable_group_info'].append({'__tuple__': True, 'items': [name, name]})
            local['variable_length_dict'].pop(name)
            declarations[0][kind].pop(name)
            declarations[1].pop(name)
            declarations[2].remove(name)
    for node in walk(doc):
        if '__tuple__' in node:
            items = node.get('items', [])
            if len(items) == 3 and items[1] in names and items[2] == 'local':
                items[2] = 'actor'


def zhang_five(source):
    d = cp(source); b = builder(d, 0); tid = '1959489540'
    # Remove only the exactly registered temporary probe, not prior skill logs.
    records = first.trace.read(FIRST_WORK / 'diagnostics.json')[FILES[0]]
    d = first.trace.remove_registered(d, records)
    timer = first.one(d['trigger_dict'][tid]['action'], 'RUN_LOOP_TIMER')
    old = timer['args_list'][3]['args_list']
    release = next(n for n in walk(old) if n.get('action_type') == 'UNIT_RELEASE_COMMAND'
                   and n.get('element_id') == 1959489540974337)
    prints = [cp(n) for n in walk(old) if n.get('action_type') == 'PRINT_MESSAGE_ACTION_TO_DIALOG']
    traces = [n for n in prints if isinstance(n['args_list'][1]['args_list'][0], str)
              and n['args_list'][1]['args_list'][0].startswith(first.trace.PREFIX)]
    native_prints = [n for n in prints if n not in traces]
    # Keep every original command trace ID; only the authoritative target source changes.
    before = [n for n in traces if '调用前' in n['args_list'][1]['args_list'][0]]
    after = [n for n in traces if n not in before]
    owner, skill = ex(100006, 'ABILITY_OWNER'), ex(100014, 'CUR_ABILITY')
    core = first.declare(d, tid, 'MODIFIER_ENTITY', '修复2_破阵核心', actor=True)
    mark = first.declare(d, tid, 'MODIFIER_ENTITY', '修复2_破阵震慑', actor=True)
    target = first.var('UNIT_ENTITY', '目标单位', 'actor')
    for node in walk(native_prints):
        if node.get('sub_type') == 'FOR_EACH_SELECTED_UNIT':
            node.clear(); node.update(cp(target))
    last = first.var('INTEGER', '排查_张辽5上次状态', 'actor')
    def state(number, text):
        return b.branch([b.cmp(last, '!=', lit(number))], [log(b, text), b.set(last, lit(number))])
    lookup = ex(100076, 'GET_LAST_MODIFIER_INSTANCE', cp(owner), lit(134259689, 100046))
    get_mark = ex(100076, 'GET_LAST_MODIFIER_INSTANCE', cp(target), lit(134259870, 100046))
    full = b.cmp(ex(100002, 'GET_MOD_STACK', cp(mark)), '>=', ex(100002, 'GET_MOD_STACK_MAX', cp(mark)))
    helper = ex(100001, '97642c3d802a5935a73289745a266ac8', cp(owner))
    helper.update(call_rt_index=0, op_arg=[], op_arg_enable=[])
    ready = [b.cmp(ex(100000, 'ABILITY_CD_LEFT_TIME', cp(skill)), '==', lit(0)),
             b.cmp(first.kv(100001, owner, '自动施法'), '==', lit(True, 100001), 'BOOL_COMPARE'),
             b.cmp(helper, '==', lit(True, 100001), 'BOOL_COMPARE')]
    dispatch = first.otherwise(b.branch(ready, [state(5, '张辽5星/核心目标满层，提交施法命令'),
                                                *before, cp(release), *after,
                                                b.exists(mark, native_prints)]),
                               [state(4, '张辽5星/目标满层但冷却或动作状态未就绪')])
    has_mark = [b.set(mark, get_mark), b.exists(mark, [first.otherwise(b.branch([full], [dispatch]),
                               [state(3, '张辽5星/核心目标震慑尚未满层')])])]
    selected = first.live(b, target, [first.otherwise(b.branch([
        b.cond('UNIT_HAS_MODIFIER', target, lit(134259870, 100046))], has_mark),
        [state(2, '张辽5星/核心目标已无震慑')])], owner)
    body = [b.set(core, lookup), first.otherwise(b.exists(core, [first.otherwise(b.branch([
        b.cond('HAS_KV_ANY', core, lit('震慑单位', 100003))], [
            b.set(target, ex(100006, 'GET_UNIT_ENTITY_KV', cp(core), lit('震慑单位', 100003))),
            selected]), [state(1, '张辽5星/核心尚未记录震慑目标')])]),
        [state(0, '张辽5星/核心不存在')])]
    timer['args_list'][3]['args_list'] = [b.exists(skill, [first.live(b, owner, [b.branch([
        b.cmp(first.global_int('当前游戏进程阶段'), '==', lit(2))], body)])])]
    # The old stage-event cache is no longer used; do not clear an aliased team group.
    phase = d['trigger_dict']['1016573957']
    phase['action'] = [n for n in phase['action'] if isinstance(n, dict)
                       and n.get('action_type') == 'PRINT_MESSAGE_ACTION_TO_DIALOG']
    return d


def sunce(source):
    d = cp(source); b = builder(d, 1); tid = '1051000836'
    t = d['trigger_dict'][tid]
    owner = ex(100006, 'ABILITY_OWNER')
    event = ex(100076, 'GET_MODIFIER_FROM_EVENT')
    names = {name for values in d['local_variable'][tid]['variable_dict'].values()
             for name in values if name.startswith('P2_latest_')}
    assert len(names) == 9
    promote(d, tid, names)
    # Filter the layer=1 event raised synchronously by consumption before entering
    # the action body. Previously every global layer event entered this body.
    t['condition'] += [
        b.cmp(ex(100046, 'GET_MODIFIER_ENTITY_METATYPE', cp(event)),
              '==', lit(134279388, 100046), 'MODIFIER_CLASS_COMPARE'),
        b.cmp(ex(100002, 'GET_MOD_STACK', cp(event)), '>=', lit(3)),
        b.cond('BOOL_NOT', ex(100001, 'GET_BOOLEAN_KV', cp(event),
                             lit('孙策潮势冲斩处理中', 100003)))]
    return d


def summer_three(source):
    d = cp(source); b = builder(d, 2); tid = '1959489540'
    names = {name for values in d['local_variable'][tid]['variable_dict'].values()
             for name in values if name.startswith('修复_贯阵')}
    assert len(names) == 6
    promote(d, tid, names)
    timer = first.one(d['trigger_dict'][tid]['action'], 'RUN_LOOP_TIMER')
    release = first.one(timer, 'UNIT_RELEASE_COMMAND')
    target = first.var('UNIT_ENTITY', '目标单位', 'actor')
    # Native commands can return without casting when their actual target is empty.
    guarded = first.live(b, target, [cp(release)], ex(100006, 'ABILITY_OWNER'))
    first.replace_action(timer, release['element_id'], [guarded])
    return d


def summer_five(source):
    d = cp(source); b = builder(d, 3)
    t = d['trigger_dict']['1959489540']
    old = next(n for n in walk(t['action']) if n.get('action_type') == 'IF_THEN_ELSE'
               and any(c.get('element_id') == 1959489540974493 for c in n['args_list'][0]['args_list']))
    owner = ex(100006, 'ABILITY_OWNER')
    core = ex(100076, 'GET_LAST_MODIFIER_INSTANCE', cp(owner), lit(134282266, 100046))
    first.replace_action(t['action'], old['element_id'], [b.exists(owner, [b.exists(core, [cp(old)])])])
    return d


def build(root):
    patches = [zhang_five, sunce, summer_three, summer_five]
    return {path: patch(first.trace.read(root / path)) for path, patch in zip(FILES, patches)}


def configure():
    first.WORK = WORK
    first.FILES = FILES
    first.build = build
    first.PREFIX = PREFIX


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'resume', 'refresh', 'publish', 'verify'])
    action = parser.parse_args().action
    configure()
    if action == 'prepare':
        first.prepare()
    elif action == 'resume':
        first.prepare(resume=True)
    elif action == 'refresh':
        first.refresh()
    else:
        if action == 'publish': first.publish()
        else:
            result = first.verify()
            first.trace.save(WORK / 'editor-verified.json', result)
            print(json.dumps(result))
