"""Zhu Rong projectile/target selection and Ma Chao missing-loop guards."""
from copy import deepcopy as cp
from pathlib import Path
import argparse
import json
import shutil

import y3_hero_runtime_followup_20261024 as base
from y3_hero_runtime_followup_r7_20261024 import actor, declare, get, substitute

ROOT = base.ROOT
WORK = base.WORK.parent / 'hero-followup-20261024-r8'
FILES = ['ability/134284030.json', 'ability/134284032.json', 'ability/134222927.json']
PREFIX = '[技能排查/20261024-r8] '
LOG = Path('D:/Program Files/y3/games/2.0/game/LocalData/trigger_log/map3/Log/littlemurloc_2026_10_24_16_00_32.log')
SKILL, OWNER, HANDLE = 'R8_飞火技能', 'R8_飞火拥有者', 'R8_创建飞火'
TARGET, CORE, WAVE, HAD, PERMIT = 'R8_飞火目标', 'R8_飞火来源循环', 'R8_飞火波次', 'R8_飞火原有循环', 'R8_飞火可结算'
LAST = 'R8_扇火上次状态'


def note(b, label, *values):
    result = base.trace.log_node(b.node('unused')['element_id'], PREFIX + label)
    if values:
        pieces = [base.lit(PREFIX + label, 100003)]
        for key, value in values:
            pieces += [base.lit(' | ' + key + '=', 100003), base.ex(100003, 'ANY_VAR_TO_STR', cp(value))]
        assert len(pieces) <= 10
        expr = base.ex(100003, 'STR_JOIN', *pieces[:2])
        expr.update(op_arg=pieces[2:] + [None] * (10 - len(pieces)),
                    op_arg_enable=[True] * (len(pieces) - 2) + [False] * (10 - len(pieces)))
        result['args_list'][1] = expr
    return result


def zhurong_one(source):
    d = cp(source); b = base.builder(d, 300)
    skill = declare(d, 'ABILITY', SKILL, None)
    owner = declare(d, 'UNIT_ENTITY', OWNER)
    handle = declare(d, 'PROJECTILE_ENTITY', HANDLE)
    target = actor('UNIT_ENTITY', '目标单位')
    obtain = d['trigger_dict']['1959489540']
    obtain['action'][1:1] = [b.set(skill, base.ex(100014, 'CUR_ABILITY')),
                            b.set(owner, base.ex(100006, 'ABILITY_OWNER'))]
    cast = d['trigger_dict']['893440004']
    cast['action'] = substitute(cast['action'], [(base.ex(100014, 'CUR_ABILITY'), skill),
                                                (base.ex(100006, 'ABILITY_OWNER'), owner)])
    mover = base.one(cast['action'], 'CREATE_CHASING_MOVER', 893440004000009)
    create = base.one(cast['action'], 'SET_VARIABLE', 893440004000008)
    old_handle = cp(mover['args_list'][0])
    assert old_handle == create['args_list'][0]
    create['args_list'][0] = cp(handle)
    mover['args_list'][0] = cp(handle)
    current = base.ex(100077, 'GET_MOVER_OWNER_PROJECTILE')
    impact_target = get(100006, current, TARGET)
    impact_core = get(100076, current, CORE)
    current_core = base.ex(100076, 'GET_LAST_MODIFIER_INSTANCE', cp(owner), base.lit(134284036, 100046))
    old_hit = mover['args_list'][5]['args_list']
    delete = base.one(old_hit, 'PROJECTILE_DELETE')
    effects = substitute([n for n in old_hit if n is not delete], [(target, impact_target), (old_handle, current)])

    def bound(actions):
        allowed = base.kv(100001, current, PERMIT)
        had = base.kv(100001, current, HAD)
        set_allow = lambda: base.write(b, current, PERMIT, base.lit(True, 100001))
        yes_core = b.branch([b.cond('HAS_KV_ANY', current, base.lit(CORE, 100003))], [
            b.exists(impact_core, [b.branch([
                b.cmp(current_core, '==', impact_core, 'MODIFIER_COMPARE')], [set_allow()])])])
        decide = [base.write(b, current, PERMIT, base.lit(False, 100001)),
                  base.otherwise(b.branch([b.cmp(had, '==', base.lit(False, 100001), 'BOOL_COMPARE')],
                                          [set_allow()]), [yes_core]),
                  b.branch([b.cmp(allowed, '==', base.lit(True, 100001), 'BOOL_COMPARE'),
                            b.cmp(base.global_int('当前游戏进程阶段'), '==', base.lit(2)),
                            b.cmp(get(100002, current, WAVE), '==', base.global_int('当前进程所在波次编号'))], actions)]
        live = base.live(b, owner, [base.live(b, impact_target, decide, owner)])
        return b.exists(current, [b.exists(skill, [live])])

    # Damage may synchronously end the wave. Revalidate before adding a seed.
    seed = base.one(effects, 'IF_THEN_ELSE', 893440004000012)
    base.replace_action(effects, seed['element_id'], [bound([cp(seed)])])
    keys = [b.cond('HAS_KV_ANY', current, base.lit(k, 100003)) for k in (TARGET, WAVE, HAD)]
    mover['args_list'][5]['args_list'] = [b.exists(current, [b.branch(keys, [bound(effects)]), delete])]
    shot = [create, b.exists(handle, [
        b.node('SET_PROJECTILE_DURATION', cp(handle), base.lit(8.0, 100000)),
        base.write(b, handle, TARGET, target),
        base.write(b, handle, WAVE, base.global_int('当前进程所在波次编号')),
        base.write(b, handle, HAD, base.lit(False, 100001)),
        b.exists(current_core, [base.write(b, handle, CORE, current_core),
                                base.write(b, handle, HAD, base.lit(True, 100001))]), mover])]
    body = cast['action'][2]['args_list'][1]['args_list']
    i = next(i for i, n in enumerate(body) if n is create)
    assert body[i + 1] is mover
    body[i:i + 2] = shot
    valid_target = cast['action'][2]
    valid_target['args_list'][0]['args_list'] += [base.not_dead(b, target), b.cond('IS_ENEMY', target, owner)]
    cast['action'][2] = b.exists(target, [valid_target])
    head, rest = cast['action'][:1], cast['action'][1:]
    cast['action'] = [*head, b.exists(skill, [base.live(b, owner, [b.branch([
        b.cmp(base.global_int('当前游戏进程阶段'), '==', base.lit(2))], rest)])])]
    return d


def zhurong_three(source):
    d = cp(source); b = base.builder(d, 301)
    t = d['trigger_dict']['1959489540']
    timer = base.one(t['action'], 'RUN_LOOP_TIMER')
    ready = timer['args_list'][3]['args_list'][0]
    old_body = ready['args_list'][1]['args_list']
    disabled, pick, command_branch = old_body
    assert disabled.get('enable') is False and pick['action_type'] == 'PICK_UNIT_DO_ACTION'
    skill, owner = base.ex(100014, 'CUR_ABILITY'), base.ex(100006, 'ABILITY_OWNER')
    target = actor('UNIT_ENTITY', '目标单位')
    hate = declare(d, 'UNIT_ENTITY', 'R8_扇火仇恨目标')
    last = declare(d, 'INTEGER', LAST, -1)
    distance = base.ex(100000, 'GET_POINTS_DIS', base.ex(100004, 'UNIT_ENTITY_POINT', cp(owner)),
                       base.ex(100004, 'UNIT_ENTITY_POINT', cp(hate)))
    radius = base.ex(100000, 'GET_ABILITY_FLOAT_ATTR', cp(skill), base.lit('ability_cast_range', 100078))
    selected = base.ex(100006, 'FOR_EACH_SELECTED_UNIT')
    original_selection = pick['args_list'][1]['args_list'][0]['args_list'][1]['args_list']
    assert [n['action_type'] for n in original_selection] == ['SET_VARIABLE', 'BREAK_LOOP']
    pick['args_list'][1]['args_list'] = [base.live(b, selected, cp(original_selection), owner)]
    choose_hate = base.live(b, hate, [b.branch([b.cmp(distance, '<=', radius)], [b.set(target, hate)])], owner)
    no_target = b.cmp(target, '==', base.ex(100006, 'NONE_UNIT'), 'UNIT_COMPARE')
    def state(code, label, *values):
        return b.branch([b.cmp(last, '!=', base.lit(code))],
                        [note(b, label, *values), b.set(last, base.lit(code))])
    missing = state(0, '祝融3星/前置通过但范围内无合法目标', ('施法者', owner), ('施法范围', radius))
    chosen = state(1, '祝融3星/已选到合法目标', ('施法者', owner), ('目标', target))
    target_branch = base.live(b, target, [chosen, cp(command_branch)], owner)
    ready['args_list'][1]['args_list'] = [cp(disabled), b.set(target, base.ex(100006, 'NONE_UNIT')),
        b.set(hate, base.ex(100006, 'GET_UNIT_AI_BATTLE_TARGET_UNIT', cp(owner))), choose_hate,
        b.branch([no_target], [pick]), target_branch, b.branch([cp(no_target)], [missing])]
    helper = base.ex(100001, '97642c3d802a5935a73289745a266ac8', cp(owner))
    helper.update(call_rt_index=0, op_arg=[], op_arg_enable=[])
    ready['args_list'][2]['args_list'] = [state(2, '祝融3星/冷却或自动施法动作条件未满足',
        ('施法者', owner), ('冷却', base.ex(100000, 'ABILITY_CD_LEFT_TIME', cp(skill))),
        ('动作允许', helper), ('自动施法', base.kv(100001, owner, '自动施法')))]
    # Scope the old compound guard under ordered existence/life checks.
    timer['args_list'][3]['args_list'] = [b.exists(skill, [base.live(b, owner, [b.branch([
        b.cmp(base.global_int('当前游戏进程阶段'), '==', base.lit(2))], [ready])])])]
    t['action'].insert(1, b.set(last, base.lit(-1)))
    return d


def machao_five(source):
    d = cp(source); b = base.builder(d, 302)
    timer = base.one(d['trigger_dict']['1959489540']['action'], 'RUN_LOOP_TIMER')
    assert len(timer['args_list'][3]['args_list']) == 1
    ready = timer['args_list'][3]['args_list'][0]
    check = next(n for n in base.walk(ready) if n.get('element_id') == 1959489540974493)
    assert check['args_list'][0]['sub_type'] == 'GET_MOD_STACK'
    core = declare(d, 'MODIFIER_ENTITY', 'R8_马超五星彩冲势')
    lookup = cp(check['args_list'][0]['args_list'][0])
    check['args_list'][0]['args_list'][0] = cp(core)
    skill = base.ex(100014, 'CUR_ABILITY')
    owner = base.ex(100006, 'GET_ABILITY_OWNER', cp(skill))
    timer['args_list'][3]['args_list'] = [b.exists(skill, [base.live(b, owner, [b.branch([
        b.cmp(base.global_int('当前游戏进程阶段'), '==', base.lit(2))], [
            b.set(core, lookup), b.exists(core, [ready])])])])]
    return d


def build(root):
    return {FILES[0]: zhurong_one(base.trace.read(root / FILES[0])),
            FILES[1]: zhurong_three(base.trace.read(root / FILES[1])),
            FILES[2]: machao_five(base.trace.read(root / FILES[2]))}


def configure():
    base.WORK, base.FILES, base.build, base.PREFIX = WORK, FILES, build, PREFIX


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'refresh', 'publish', 'verify'])
    action = parser.parse_args().action
    configure()
    if action in ('prepare', 'refresh'):
        (base.prepare if action == 'prepare' else base.refresh)()
        if action == 'prepare':
            if LOG.is_file(): shutil.copy2(LOG, WORK / 'runtime-before.log')
            else: base.trace.save(WORK / 'runtime-log-state.json', {'source': str(LOG), 'available': False})
        base.trace.save(WORK / 'diagnostic-expressions.json', {
            p: [cp(n) for n in base.walk(base.trace.read(WORK / 'candidate' / p))
                if n.get('action_type') == 'PRINT_MESSAGE_ACTION_TO_DIALOG' and PREFIX in str(n)]
            for p in FILES})
    elif action == 'publish': base.publish()
    else:
        result = base.verify()
        assert all(t.get('valid') is True for p in FILES
                   for t in base.trace.read(ROOT / p)['trigger_dict'].values())
        result['all_triggers_valid'] = True
        base.trace.save(WORK / 'editor-verified.json', result)
        print(json.dumps(result))
