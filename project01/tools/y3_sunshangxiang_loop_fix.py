"""Repair Sun Shangxiang's approved idle-sword lifecycle and skill linkage."""
from copy import deepcopy as cp
import json
import y3_hero_repair_publish as pub
from y3_sunshangxiang_orbit_fix import Builder, ex, lit, ref, alive, global_int, walk, one

PHASE = 'ssx-loop-20261022'
CORE = 'modifier/134248740.json'
ACTIVE = '游剑修复_有效'
LIFE = '游剑修复_返回计时器'
TARGET = '目标单位'


class B(Builder):
    def var(self, kind, name, tid=None):
        name = '游剑修复_' + name
        data = self.doc if tid is None else self.doc['local_variable'][str(tid)]
        default = -1 if kind == 'NEW_TIMER' else False if kind == 'BOOLEAN' else 0
        assert name not in data['variable_length_dict'], name
        data['variable_dict'].setdefault(kind, {})[name] = default
        data['variable_length_dict'][name] = 0
        if tid is None:
            data['variable_group_info'].append({'__tuple__': True, 'items': [name, name]})
        else:
            v = self.doc['trigger_dict'][str(tid)]['var_data']
            v[0].setdefault(kind, {})[name] = default
            v[1][name] = 0
            v[2].append(name)
        types = {'NEW_TIMER': (100181, 'VARIABLE'), 'BOOLEAN': (100001, 'VARIABLE'),
                 'INTEGER': (100002, 6), 'UNIT_ENTITY': (100006, 11),
                 'MODIFIER_ENTITY': (100076, 11), 'PROJECTILE_ENTITY': (100077, 'VARIABLE'),
                 'UNIT_GROUP': (100026, 14)}
        t, s = types[kind]
        return ex(t, s, {'__tuple__': True, 'items': [kind, name, 'actor' if tid is None else 'local']})

    def kv(self, obj, key, value):
        return self.node('SET_ENTITY_KV', cp(obj), lit(key, 100003), cp(value))


def get(obj, key, kind='UNIT_ENTITY'):
    t, s = {'UNIT_ENTITY': (100006, 'GET_UNIT_ENTITY_KV'),
            'NEW_TIMER': (100181, 'GET_NEW_TIMER_KV')}[kind]
    return ex(t, s, cp(obj), lit(key, 100003))


def yes(b, value):
    return b.cmp(value, '==', lit(True, 100001), 'BOOL_COMPARE')


def if_else(b, checks, body, otherwise):
    n = b.branch(checks, body)
    n['args_list'][2]['args_list'] = otherwise
    return n


def active_walk(x):
    if isinstance(x, dict):
        if x.get('enable') is False:
            return
        yield x
        for v in x.values():
            yield from active_walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from active_walk(v)


def patch_core(original):
    d = cp(original)
    b = B(d)
    mod, owner = ex(100076, 'CUR_MODIFIER'), ex(100006, 'MODIFIER_OWNER')
    selected = ex(100077, 'FOR_EACH_SELECTED_PROJECTILE')
    group = ex(100203, 'GET_PROJECTILE_GROUP_KV', cp(mod), lit('游剑-组', 100003))
    source = next(n for n in walk(d) if n.get('element_id') == 1878966277000730)
    orbit_template = cp(source)
    chase_template = cp(next(n for n in walk(d) if n.get('element_id') == 1878966277000649))
    delete_template = cp(next(n for n in walk(d) if n.get('element_id') == 1485688834000495))
    create = cp(next(n for n in walk(d) if n.get('element_id') == 1485688834000621))
    created = cp(create['args_list'][0])
    active = b.var('BOOLEAN', '有效')
    poll = b.var('NEW_TIMER', '状态检查')
    cooldown = b.var('NEW_TIMER', '派剑间隔')

    def bound(body):
        lookup = ex(100076, 'GET_LAST_MODIFIER_INSTANCE', cp(owner), lit(134248740, 100046))
        return b.exists(mod, [b.branch([yes(b, active)], [b.exists(owner, [
            b.branch([b.cmp(lookup, '==', mod, 'MODIFIER_COMPARE')], body)])])])

    def each(body):
        return b.node('PICK_PROJECTILE_DO_ACTION', cp(group), ex(100022, 1, *body))

    def orbit(projectile, target):
        n = b.fresh(orbit_template)
        n['args_list'][0:2] = [cp(projectile), cp(target)]
        for arg in n['args_list']:
            if arg.get('arg_type') == 100022:
                arg['args_list'] = []
        return n

    def cancel(handle):
        return b.exists(handle, [b.node('DELETE_TIMER', cp(handle))])

    def cancel_life(projectile):
        return b.branch([b.cond('HAS_KV_ANY', projectile, lit(LIFE, 100003))],
                        [cancel(get(projectile, LIFE, 'NEW_TIMER'))])

    def return_sword(projectile):
        # Logical state commits before replacing the mover; old callbacks see idle.
        return [b.kv(projectile, TARGET, owner), cancel_life(projectile), orbit(projectile, owner)]

    def recount(tid):
        count = b.var('INTEGER', '待命数', tid)
        count_idle = each([b.exists(selected, [b.branch([
            b.cond('HAS_KV_ANY', selected, lit(TARGET, 100003))], [b.branch([
                b.cmp(get(selected, TARGET), '==', owner, 'UNIT_COMPARE')],
                [b.set(count, ex(100002, 'INT_PLUS_ONE', cp(count)))])])])])
        value = ex(100002, 'INT_PLUS_ONE', cp(count))
        update = b.branch([b.cmp(ex(100002, 'GET_MOD_STACK', cp(mod)), '!=', value)],
                          [b.node('SET_BUFF_STACK', cp(mod), value)])
        return [b.set(count, lit(0)), count_idle, update]

    gain = d['trigger_dict']['1485688834']
    registration = [a for a in gain['action'] if isinstance(a, int)]
    assert registration == [938414084, 1878966277]
    gain['action'] = [b.set(active, lit(True, 100001)),
        b.kv(mod, '游剑-组', ex(100203, 'CREATE_PROJECTILE_GOURP')),
        # Reset the existing six-star per-battle claim when a new loop is granted.
        b.kv(owner, 'P2_state_split_wave', lit(0))]
    for _ in range(3):
        gain['action'] += [b.fresh(create), b.exists(created, [
            b.kv(created, TARGET, owner),
            b.node('GROUP_ADD_PROJECTILE', cp(created), cp(group)), orbit(created, owner)])]
    gain['action'] += registration

    # Empty timer callbacks avoid carrying projectile iteration state asynchronously.
    life = get(selected, LIFE, 'NEW_TIMER')
    target = get(selected, TARGET)
    needs_return = b.var('BOOLEAN', '需要返回', '1485688834')
    expiry = if_else(b, [b.cond('TYPE_IS_EXIST', life)],
        [b.branch([b.cmp(ex(100000, 'GET_TIMER_REMAINING_TIME', cp(life)), '<=', lit(0.0, 100000))],
                  [b.set(needs_return, lit(True, 100001))])],
        [b.set(needs_return, lit(True, 100001))])
    expiry_key = if_else(b, [b.cond('HAS_KV_ANY', selected, lit(LIFE, 100003))],
                        [expiry], [b.set(needs_return, lit(True, 100001))])
    valid_target = if_else(b, [b.cond('TYPE_IS_EXIST', target)],
        [if_else(b, alive(b, target), [], [b.set(needs_return, lit(True, 100001))])],
        [b.set(needs_return, lit(True, 100001))])
    visit = b.exists(selected, [b.branch([b.cond('HAS_KV_ANY', selected, lit(TARGET, 100003))], [
        if_else(b, [b.cmp(target, '!=', owner, 'UNIT_COMPARE')], [
            b.set(needs_return, lit(False, 100001)), valid_target, expiry_key,
            b.branch([yes(b, needs_return)], return_sword(selected))], [cancel_life(selected)])])])
    battle = [b.cmp(global_int('当前游戏进程阶段'), '==', lit(2)), *alive(b, owner)]
    clear_all = each([b.exists(selected, [b.branch([
        b.cond('HAS_KV_ANY', selected, lit(TARGET, 100003))], [b.branch([
            b.cmp(get(selected, TARGET), '!=', owner, 'UNIT_COMPARE')], return_sword(selected))])])])
    poll_body = bound([if_else(b, battle,
        [each([visit]), *recount('1485688834')],
        [clear_all, b.branch([b.cmp(ex(100002, 'GET_MOD_STACK', cp(mod)), '!=', lit(1))],
                            [b.node('SET_BUFF_STACK', cp(mod), lit(1))])])])
    gain['action'].append(b.node('RUN_LOOP_TIMER', cp(poll), lit(0.1, 100000),
                                lit(False, 100001), ex(100022, 1, poll_body)))

    phase = d['trigger_dict']['938414084']
    phase['action'] = [bound([cancel(cooldown),
        each([b.exists(selected, return_sword(selected))]), *recount('938414084')])]

    hurt = d['trigger_dict']['1878966277']
    projectile = b.var('PROJECTILE_ENTITY', '派出的剑', '1878966277')
    victim = b.var('UNIT_ENTITY', '派剑目标', '1878966277')
    handle = b.var('NEW_TIMER', '返回句柄', '1878966277')
    allowed = b.var('BOOLEAN', '允许派剑', '1878966277')
    allowed_check = b.exists(cooldown, [b.branch([
        b.cmp(ex(100000, 'GET_TIMER_REMAINING_TIME', cp(cooldown)), '>', lit(0.0, 100000))],
        [b.set(allowed, lit(False, 100001))])])
    chase = b.fresh(chase_template)
    chase['args_list'][0:2] = [cp(projectile), cp(victim)]
    for arg in chase['args_list']:
        if arg.get('arg_type') == 100022:
            arg['args_list'] = []
    chase['args_list'][5]['args_list'] = [bound([b.exists(projectile, [b.exists(victim, [
        b.branch([*alive(b, victim), b.cmp(get(projectile, TARGET), '==', victim, 'UNIT_COMPARE')],
                 [orbit(projectile, victim)])])])])]
    send = cp(next(n for n in walk(original) if n.get('element_id') == 1878966277000823))
    dispatch = [b.set(projectile, selected), b.set(victim, ex(100006, 'DAMAGE_TARGET_UNIT')),
        cancel_life(projectile), b.kv(projectile, TARGET, victim),
        b.node('RUN_ONCE_TIMER', cp(handle), lit(6.0, 100000), ex(100022, 1)),
        b.kv(projectile, LIFE, handle), cancel(cooldown),
        b.node('RUN_ONCE_TIMER', cp(cooldown), lit(1.5, 100000), ex(100022, 1)),
        chase, *recount('1878966277'), send, b.node('BREAK_LOOP')]
    choose = b.exists(selected, [b.branch([
        b.cond('HAS_KV_ANY', selected, lit(TARGET, 100003))], [b.branch([
            b.cmp(get(selected, TARGET), '==', owner, 'UNIT_COMPARE')], dispatch)])])
    hurt['action'] = [bound([b.exists(ex(100006, 'DAMAGE_TARGET_UNIT'), [b.branch([
        *b.fresh(battle), *alive(b, ex(100006, 'DAMAGE_TARGET_UNIT')),
        b.cond('IS_ENEMY', ex(100006, 'DAMAGE_TARGET_UNIT'), owner)],
        [b.set(allowed, lit(True, 100001)), allowed_check,
         b.branch([yes(b, allowed)], [each([choose])])])])])]

    loss = d['trigger_dict']['594665475']
    unregister = [a for a in loss['action'] if a.get('action_type') == 'UNREG_TRIGGER']
    loss['action'] = [b.set(active, lit(False, 100001)), cancel(poll), cancel(cooldown),
        each([b.exists(selected, [cancel_life(selected),
                                  b.fresh(delete_template)])]), *unregister]
    return d


def patch_four(original):
    d = cp(original)
    b = B(d)
    tid = '1756393476'
    t = d['trigger_dict'][tid]
    add = cp(one(t['action'], 'ADD_MODIFIER'))
    skill, owner = ex(100014, 'CUR_ABILITY'), ex(100006, 'ABILITY_OWNER')
    event_unit = ex(100006, 'GET_CUS_EVENT_PARAM', lit('触发单位', 100240))
    target = ex(100006, 'GET_CUS_EVENT_PARAM', lit('目标单位', 100240))
    core = b.var('MODIFIER_ENTITY', '裂甲核心', tid)
    last_core = b.var('MODIFIER_ENTITY', '裂甲记录核心')
    claimed = b.var('UNIT_GROUP', '裂甲目标组')
    count = b.var('INTEGER', '裂甲剑数', tid)
    selected = ex(100077, 'FOR_EACH_SELECTED_PROJECTILE')
    count_sword = b.exists(selected, [b.branch([
        b.cond('HAS_KV_ANY', selected, lit(TARGET, 100003))], [b.branch([
            b.cmp(get(selected, TARGET), '==', target, 'UNIT_COMPARE')],
            [b.set(count, ex(100002, 'INT_PLUS_ONE', cp(count)))])])])
    group = ex(100203, 'GET_PROJECTILE_GROUP_KV', cp(core), lit('游剑-组', 100003))
    payload = [b.branch([b.cmp(last_core, '!=', core, 'MODIFIER_COMPARE')],
                       [b.set(last_core, core), b.set(claimed, ex(100026, 'NONE_UNIT_GROUP'))]),
        b.set(count, lit(0)), b.node('PICK_PROJECTILE_DO_ACTION', group, ex(100022, 1, count_sword)),
        b.branch([b.cmp(count, '>=', lit(2)),
                  b.cond('NOT', ex(100021, 1, b.cond('UNIT_IN_GROUP', target, claimed)))],
                 [b.node('GROUP_ADD_UNIT', cp(target), cp(claimed)), add])]
    t['condition'] = []
    t['action'] = [b.exists(skill, [b.exists(owner, [b.exists(event_unit, [b.exists(target, [
        b.branch([b.cmp(event_unit, '==', owner, 'UNIT_COMPARE'), *alive(b, owner), *alive(b, target),
                  b.cond('IS_ENEMY', target, owner),
                  b.cmp(global_int('当前游戏进程阶段'), '==', lit(2))], [
            b.set(core, ex(100076, 'GET_LAST_MODIFIER_INSTANCE', cp(owner), lit(134248740, 100046))),
            b.exists(core, [b.branch([b.cond('HAS_KV_ANY', core, lit('游剑-组', 100003))], payload)])])])])])])]
    return d


def patch_first(original):
    d = cp(original)
    b = B(d)
    gain = d['trigger_dict']['1959489540']
    timer = one(gain['action'], 'RUN_LOOP_TIMER')
    old = timer['args_list'][3]['args_list'][0]
    assert old['element_id'] == 1959489540974074
    checks = cp(old['args_list'][0]['args_list'])
    assert checks.pop(0)['condition_type'] == 'TYPE_IS_EXIST'
    actions = old['args_list'][1]['args_list']
    assign = cp(one(actions, 'SET_VARIABLE'))
    release = cp(one(actions, 'UNIT_RELEASE_COMMAND'))
    target = cp(assign['args_list'][0])
    target['arg_type'], target['sub_type'] = 100006, 11
    owner, skill = ex(100006, 'ABILITY_OWNER'), ex(100014, 'CUR_ABILITY')
    timer['args_list'][3]['args_list'] = [b.exists(skill, [b.exists(owner, [
        b.branch([*alive(b, owner), *checks], [assign, b.exists(target, [
            b.branch([*alive(b, target), b.cond('IS_ENEMY', target, owner)], [release])])])])])]
    return d


def guard_skill(original, oid):
    d = cp(original)
    b = B(d)
    owner, skill = ex(100006, 'ABILITY_OWNER'), ex(100014, 'CUR_ABILITY')
    # Keep dependency boundaries; append pseudo-death checks only where the unit
    # is already dereferenced by an existing native alive condition.
    for node in list(active_walk(d)):
        if node.get('arg_type') != 100021:
            continue
        checks = node['args_list']
        for c in list(checks):
            if c.get('condition_type') == 'IS_UNIT_ALIVE':
                value = c['args_list'][0]
                tag = ex(100001, 'UNIT_HAS_TAG', cp(value), lit('已死亡', 100003))
                if not any(n.get('condition_type') == 'BOOL_NOT' and n.get('args_list') == [tag] for n in checks):
                    checks.append(b.cond('BOOL_NOT', tag))
    if oid in (134219344, 134276381):
        cast_key = '893440004' if oid == 134219344 else '1756393476'
        t = d['trigger_dict'][cast_key]
        name = 'P2_state_cast_core' if oid == 134219344 else 'P2_state_split_core'
        saved_core = cp(next(n for n in active_walk(t)
                             if n.get('arg_type') == 100076 and name in json.dumps(n)))
        lookup = ex(100076, 'GET_LAST_MODIFIER_INSTANCE', cp(owner), lit(134248740, 100046))
        for timer in list(active_walk(t)):
            if timer.get('action_type') == 'RUN_ONCE_TIMER_NO_SAVE':
                old = timer['args_list'][1]['args_list']
                timer['args_list'][1]['args_list'] = [b.exists(saved_core, [b.exists(owner, [
                    b.branch([b.cmp(lookup, '==', saved_core, 'MODIFIER_COMPARE')], old)])])]
        t['action'] = [b.exists(skill, [b.exists(owner, [b.branch([
            *alive(b, owner), b.cmp(global_int('当前游戏进程阶段'), '==', lit(2))], t['action'])])])]
    if oid in (134219344, 134276381):
        for n in list(active_walk(d)):
            if n.get('action_type') == 'PICK_PROJECTILE_DO_ACTION':
                actions = n['args_list'][1]['args_list']
                n['args_list'][1]['args_list'] = [b.exists(ex(100077, 'FOR_EACH_SELECTED_PROJECTILE'), actions)]
    if oid == 134219344:
        timer = one(list(n for n in active_walk(d['trigger_dict']['1959489540'])
                         if n.get('action_type') == 'RUN_LOOP_TIMER'), 'RUN_LOOP_TIMER')
        body = timer['args_list'][3]['args_list']
        timer['args_list'][3]['args_list'] = [b.exists(skill, [b.exists(owner, [
            b.branch(alive(b, owner), body)])])]
        # Obtain the native cast-core operand before traversing the effect payload.
        cast_core = next(n for n in active_walk(d['trigger_dict']['893440004'])
                         if n.get('arg_type') == 100076 and 'P2_state_cast_core' in json.dumps(n))
        # The effect list itself doesn't otherwise reference the core.
        def attach(x):
            if isinstance(x, list):
                state = [a for a in x if isinstance(a, dict) and a.get('action_type') == 'SET_ENTITY_KV'
                         and a['args_list'][1] == lit(TARGET, 100003)]
                if len(state) == 3:
                    commits = []
                    for a in state:
                        sword = a['args_list'][0]
                        life = get(sword, LIFE, 'NEW_TIMER')
                        commits += [b.branch([b.cond('HAS_KV_ANY', sword, lit(LIFE, 100003))],
                                             [b.exists(life, [b.node('DELETE_TIMER', cp(life))])]), a]
                    commits.append(b.exists(cast_core, [b.node('SET_BUFF_STACK', cp(cast_core), lit(4))]))
                    x[:] = commits + [a for a in x if all(a is not s for s in state)]
                    return 1
                return sum(attach(a) for a in x)
            if isinstance(x, dict) and x.get('enable') is not False:
                return sum(attach(v) for v in list(x.values()))
            return 0
        assert attach(d['trigger_dict']['893440004']['action']) == 1
        for mover in active_walk(d['trigger_dict']['893440004']):
            if mover.get('action_type') == 'CREATE_ROUND_MOVER':
                for arg in mover['args_list']:
                    if arg.get('arg_type') == 100022:
                        assert all(n.get('action_type') == 'PRINT_MESSAGE_ACTION_TO_DIALOG'
                                   for n in arg['args_list'])
                        arg['args_list'] = []
    return d


def stage():
    work = pub.WORK / PHASE
    assert not work.exists(), 'Never overwrite backup'
    baseline = {p.relative_to(pub.MAP).as_posix(): pub.sha(p.read_bytes()) for p in pub.map_files()}
    patches = {CORE: patch_core}
    patches['ability/134219500.json'] = patch_first
    patches['ability/134219157.json'] = patch_four
    for oid in (134222169, 134219344, 134276381):
        patches[f'ability/{oid}.json'] = lambda d, oid=oid: guard_skill(d, oid)
    entries = []
    for rel, patcher in patches.items():
        raw = (pub.MAP / rel).read_bytes()
        before = json.loads(raw)
        after = patcher(before)
        pub.write_generated(work / 'original' / rel, raw)
        encoded = pub.encode(after)
        pub.write_generated(work / 'staged' / rel, encoded)
        entries.append(dict(path=rel, before=pub.sha(raw), after=pub.sha(encoded), pointers=pub.compare(before, after)))
    pub.write_generated(work / 'manifest.json', pub.encode(dict(map=str(pub.MAP), phase=PHASE,
        entries=entries, notes=[], protected={f: h for f, h in baseline.items() if f not in patches})))
    print(json.dumps({'phase': PHASE, 'files': len(entries)}))


if __name__ == '__main__':
    stage()
