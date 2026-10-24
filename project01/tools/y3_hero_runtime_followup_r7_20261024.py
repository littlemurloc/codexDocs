"""Scoped passive-projectile repair, staged against a complete saved-map backup."""
from copy import deepcopy as cp
import argparse
import json
import shutil
from pathlib import Path

import y3_hero_runtime_followup_20261024 as base

ROOT = base.ROOT
WORK = base.WORK.parent / 'hero-followup-20261024-r7'
FILES = ['ability/134284011.json', 'ability/134284021.json']
PREFIX = '[技能排查/20261024-r7] '
LOG = 'D:/Program Files/y3/games/2.0/game/LocalData/trigger_log/map3/Log/littlemurloc_2026_10_24_12_34_50.log'
TARGET, CORE, WAVE = ('R7_弹道目标', 'R7_来源循环', 'R7_发射波次')
SKILL, OWNER, HANDLE = ('R7_被动技能', 'R7_被动拥有者', 'R7_创建弹道')


def actor(kind, name):
    if kind == 'PROJECTILE_ENTITY':
        return base.ex(100077, 'VARIABLE', {'__tuple__': True, 'items': [kind, name, 'actor']})
    return base.var(kind, name, 'actor')


def declare(doc, kind, name, default=0):
    assert name not in doc['variable_length_dict']
    doc['variable_dict'].setdefault(kind, {})[name] = default
    doc['variable_length_dict'][name] = 0
    doc['variable_group_info'].append({'__tuple__': True, 'items': [name, name]})
    return actor(kind, name)


def get(kind, entity, key):
    names = {100006: 'GET_UNIT_ENTITY_KV', 100076: 'GET_MODIFIER_ENTITY_KV',
             100002: 'GET_INTEGER_KV'}
    return base.ex(kind, names[kind], cp(entity), base.lit(key, 100003))


def substitute(value, pairs):
    for old, new in pairs:
        if value == old:
            return cp(new)
    if isinstance(value, dict):
        return {k: substitute(v, pairs) for k, v in value.items()}
    if isinstance(value, list):
        return [substitute(v, pairs) for v in value]
    return cp(value)


def patch(source, oid, timeout=8.0):
    d = cp(source)
    b = base.builder(d, 200 + (oid == 134284021))
    core_id = 134230485 if oid == 134284011 else 134218215
    skill = declare(d, 'ABILITY', SKILL, None)
    owner = declare(d, 'UNIT_ENTITY', OWNER)
    handle = declare(d, 'PROJECTILE_ENTITY', HANDLE)
    target = actor('UNIT_ENTITY', '目标单位')
    current = base.ex(100077, 'GET_MOVER_OWNER_PROJECTILE')
    impact_target = get(100006, current, TARGET)
    impact_core = get(100076, current, CORE)
    shooter = base.ex(100006, 'PROJECTILE_OWNER', cp(current))
    core = base.ex(100076, 'GET_LAST_MODIFIER_INSTANCE', cp(owner), base.lit(core_id, 100046))
    obtain = d['trigger_dict']['1959489540']
    obtain['action'] = substitute(obtain['action'], [
        (base.ex(100014, 'CUR_ABILITY'), skill),
        (base.ex(100006, 'ABILITY_OWNER'), owner)])
    timer = base.one(obtain['action'], 'RUN_LOOP_TIMER')
    payload = timer['args_list'][3]['args_list']

    # Native alive checks do not cover absent objects or this project's fake death.
    def guard_alive(value):
        if isinstance(value, list):
            for i in range(len(value)):
                node = value[i]
                guard_alive(node)
                if isinstance(node, dict) and node.get('action_type') == 'IF_THEN_ELSE':
                    checks = node['args_list'][0]['args_list']
                    units = [c['args_list'][0] for c in checks
                             if c.get('condition_type') == 'IS_UNIT_ALIVE' and c.get('enable') is not False]
                    for unit in reversed(units):
                        checks.append(base.not_dead(b, unit))
                        node = b.exists(unit, [node])
                    value[i] = node
        elif isinstance(value, dict):
            for child in value.values():
                guard_alive(child)

    guard_alive(payload)
    pairs = []
    for node in list(base.walk(payload)):
        if node.get('action_type') == 'CREATE_CHASING_MOVER':
            pairs.append(node)
    assert len(pairs) == 2, 'Review any changed user projectile topology'
    original_creates = [n for n in base.walk(payload) if n.get('action_type') == 'SET_VARIABLE'
                        and n['args_list'][1].get('sub_type') == 'CREATE_PROJECTILE_NEW']
    assert len(original_creates) == len(pairs)

    for mover, create in zip(pairs, original_creates):
        assert mover['args_list'][0] == create['args_list'][0]
        shot_source = cp(create['args_list'][1]['args_list'][2])
        old_handle = cp(mover['args_list'][0])
        create['args_list'][0] = cp(handle)
        creation = create['args_list'][1]
        assert creation['op_arg'][0]['sub_type'] == 'GET_ABILITY_RELEASE_DIRECTION'
        assert creation['op_arg_enable'][:2] == [True, True]
        creation['op_arg_enable'][0] = False
        mover['args_list'][0] = cp(handle)
        mover['args_list'][1] = cp(target)
        hit = mover['args_list'][5]['args_list']
        delete = base.one(hit, 'PROJECTILE_DELETE')
        assert delete['args_list'] == [current]
        assert all(not a['args_list'] for a in mover['args_list'][6:11])
        effects = substitute([n for n in hit if n is not delete], [(target, impact_target),
                                                                      (old_handle, current)])
        legal = [b.cmp(base.global_int('当前游戏进程阶段'), '==', base.lit(2)),
                 b.cmp(get(100002, current, WAVE), '==', base.global_int('当前进程所在波次编号')),
                 b.cmp(core, '==', impact_core, 'MODIFIER_COMPARE'),
                 b.cond('IS_UNIT_ALIVE', owner), base.not_dead(b, owner),
                 b.cond('IS_UNIT_ALIVE', shooter), base.not_dead(b, shooter),
                 b.cond('IS_UNIT_ALIVE', impact_target), base.not_dead(b, impact_target),
                 b.cond('IS_ENEMY', impact_target, owner)]
        # Keep cleanup outside effect guards: an expired target must not leak a missile.
        qualified = b.branch(legal, effects)
        for entity in [impact_core, impact_target, shooter, owner, skill]:
            qualified = b.exists(entity, [qualified])
        keys = [b.cond('HAS_KV_ANY', current, base.lit(k, 100003)) for k in (TARGET, CORE, WAVE)]
        mover['args_list'][5]['args_list'] = [b.exists(current, [b.branch(keys, [qualified]), delete])]
        # Explicit native timeout also cleans a projectile that never reaches its target.
        shot = [create, b.exists(handle, [
            b.node('SET_PROJECTILE_DURATION', cp(handle), base.lit(timeout, 100000)),
            base.write(b, handle, TARGET, target), base.write(b, handle, CORE, core),
            base.write(b, handle, WAVE, base.global_int('当前进程所在波次编号')), mover])]
        shooting_checks = [b.cond('IS_UNIT_ALIVE', owner), base.not_dead(b, owner),
                           b.cond('IS_UNIT_ALIVE', shot_source), base.not_dead(b, shot_source),
                           b.cond('IS_UNIT_ALIVE', target), base.not_dead(b, target),
                           b.cond('IS_ENEMY', target, owner),
                           b.cmp(base.global_int('当前游戏进程阶段'), '==', base.lit(2))]
        shot = b.branch(shooting_checks, shot)
        for entity in [core, target, shot_source, owner, skill]:
            shot = b.exists(entity, [shot])

        def replace_sequence(value):
            if isinstance(value, list):
                if create in value:
                    i = next(i for i, n in enumerate(value) if n is create)
                    assert value[i + 1] is mover
                    value[i:i + 2] = [shot]
                    return True
                return any(replace_sequence(v) for v in value)
            if isinstance(value, dict):
                return any(replace_sequence(v) for v in value.values())
            return False

        assert replace_sequence(payload)

    phase = b.cmp(base.global_int('当前游戏进程阶段'), '==', base.lit(2))
    # Handang's existing interval clock must keep advancing during preparation.
    if oid == 134284011:
        assert len(payload) == 2
        body = [payload[0], b.branch([phase], payload[1:])]
    else:
        body = [b.branch([phase], payload)]
    timer['args_list'][3]['args_list'] = [b.exists(skill, [base.live(b, owner, body)])]
    obtain['action'][1:1] = [b.set(skill, base.ex(100014, 'CUR_ABILITY')),
                            b.set(owner, base.ex(100006, 'ABILITY_OWNER'))]
    return d


def build(root):
    result = {}
    for p in FILES:
        source = base.trace.read(root / p)
        classes = {n['args_list'][0]['args_list'][0] for n in base.walk(source)
                   if n.get('sub_type') == 'CREATE_PROJECTILE_NEW'}
        assert len(classes) == 1
        resource = base.trace.read(root / 'editor_table/projectileall' / f'{classes.pop()}.json')
        timeout = min(float(resource['max_duration']), 8.0)
        assert timeout > 0
        result[p] = patch(source, int(p.split('/')[1][:-5]), timeout)
    return result


def configure():
    base.WORK, base.FILES, base.build, base.PREFIX = WORK, FILES, build, PREFIX


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'refresh', 'publish', 'verify'])
    action = parser.parse_args().action
    configure()
    if action == 'prepare':
        base.prepare()
        if Path(LOG).is_file():
            shutil.copy2(LOG, WORK / 'runtime-before.log')
        else:
            base.trace.save(WORK / 'runtime-log-state.json', {
                'source': LOG, 'available': False,
                'note': 'Previously reviewed native runtime log is no longer present after client closure.'})
    elif action == 'publish':
        base.publish()
    elif action == 'refresh':
        base.refresh()
    else:
        result = base.verify()
        for p in FILES:
            assert all(t.get('valid') is True for t in base.trace.read(ROOT / p)['trigger_dict'].values())
        result['all_triggers_valid'] = True
        base.trace.save(WORK / 'editor-verified.json', result)
        print(json.dumps(result))
