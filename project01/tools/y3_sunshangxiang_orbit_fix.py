"""Narrow, hash-staged fix for Jian Ying Hui Huan's projectile lifecycle."""
from copy import deepcopy as clone
import json
from pathlib import Path

FILE = 'ability/134222169.json'
CORE = 134248740
GAIN, CAST = '1959489540', '893440004'
PREFIX = 'SSX回环修复_'
WAVE = '当前进程所在波次编号'
PHASE = '当前游戏进程阶段'


def ex(t, s, *a):
    return dict(arg_type=t, sub_type=s, args_list=list(a))


def lit(v, t=100002):
    return ex(t, 1, v)


def walk(v):
    if isinstance(v, dict):
        yield v
        for a in v.values():
            yield from walk(a)
    elif isinstance(v, list):
        for a in v:
            yield from walk(a)


def one(v, kind):
    found = [n for n in walk(v) if n.get('action_type') == kind and n.get('enable') is not False]
    assert len(found) == 1, (kind, len(found))
    return found[0]


def ref(kind, name, scope='local', lhs=False):
    t, s = {'UNIT_ENTITY': (100006, 11), 'MODIFIER_ENTITY': (100076, 11),
            'ABILITY': (100014, 2), 'INTEGER': (100002, 6), 'POINT': (100004, 19)}[kind]
    return ex(100030 if lhs else t, 1 if lhs else s,
              {'__tuple__': True, 'items': [kind, name, scope]})


class Builder:
    def __init__(self, doc):
        self.doc = doc
        self.index = max(n.get('element_id', 0) for n in walk(doc))

    def node(self, kind, *a, cond=False):
        self.index += 1
        n = dict(element_id=self.index, enable=True, args_list=list(a))
        n['condition_type' if cond else 'action_type'] = kind
        if not cond:
            n['bp'] = False
        return n

    def fresh(self, value):
        value = clone(value)
        for n in walk(value):
            if 'element_id' in n:
                self.index += 1
                n['element_id'] = self.index
        return value

    def var(self, tid, kind, suffix):
        name = PREFIX + suffix
        data = self.doc['local_variable'][tid]
        assert name not in data['variable_length_dict']
        default = {'__tuple__': True, 'items': [0, 0, 0]} if kind == 'POINT' else (None if kind == 'ABILITY' else 0)
        data['variable_dict'].setdefault(kind, {})[name] = default
        data['variable_length_dict'][name] = 0
        v = self.doc['trigger_dict'][tid]['var_data']
        v[0].setdefault(kind, {})[name] = default
        v[1][name] = 0
        v[2].append(name)
        return ref(kind, name)

    def set(self, value, rhs):
        lhs = ex(100030, 1, clone(value['args_list'][0]))
        return self.node('SET_VARIABLE', lhs, clone(rhs))

    def cond(self, name, *a):
        return self.node(name, *map(clone, a), cond=True)

    def cmp(self, a, op, b, kind='FLOAT_COMPARE'):
        return self.cond(kind, a, lit(op, 100015 if kind == 'FLOAT_COMPARE' else 100035), b)

    def branch(self, checks, body):
        n = self.node('IF_THEN_ELSE', ex(100021, 1, *checks), ex(100022, 1, *body), ex(100022, 1))
        n['fake_op'] = []
        return n

    def exists(self, value, body):
        return self.branch([self.cond('TYPE_IS_EXIST', value)], body)


def alive(b, value):
    return [b.cond('IS_UNIT_ALIVE', value),
            b.cond('BOOL_NOT', ex(100001, 'UNIT_HAS_TAG', clone(value), lit('已死亡', 100003)))]


def global_int(name):
    return ex(100002, 6, {'__tuple__': True, 'items': ['INTEGER', name]})


def patch(original):
    doc = clone(original)
    b = Builder(doc)
    gain, cast = (doc['trigger_dict'][key] for key in (GAIN, CAST))
    timer = one(gain['action'], 'RUN_LOOP_TIMER')
    auto = timer['args_list'][3]['args_list']
    assert len(auto) == 1 and auto[0]['action_type'] == 'IF_THEN_ELSE'
    old_auto = auto[0]
    auto_scan = one(old_auto, 'PICK_PROJECTILE_DO_ACTION')
    assert auto_scan['element_id'] == 1959489540974534
    release = one(old_auto, 'UNIT_RELEASE_COMMAND')
    current = ex(100014, 'CUR_ABILITY')
    owner = ex(100006, 'GET_ABILITY_OWNER', clone(current))
    selected = ex(100077, 'FOR_EACH_SELECTED_PROJECTILE')
    actor_target = ref('UNIT_ENTITY', '目标单位', 'actor')

    def core_body(tid, source, body):
        core = b.var(tid, 'MODIFIER_ENTITY', '核心')
        lookup = ex(100076, 'GET_LAST_MODIFIER_INSTANCE', clone(source), lit(CORE, 100046))
        body = body(core)
        available = b.exists(core, [b.branch([
            b.cond('HAS_KV_ANY', core, lit('游剑-组', 100003))], body)])
        return [b.set(core, lookup), available]

    def visit(tid, source, hit):
        target = b.var(tid, 'UNIT_ENTITY', '遍历目标')
        get_target = ex(100006, 'GET_UNIT_ENTITY_KV', clone(selected), lit('目标单位', 100003))
        legal = b.exists(target, [b.branch([*alive(b, target),
            b.cond('IS_ENEMY', target, source), b.cmp(target, '!=', source, 'UNIT_COMPARE')], hit(target))])
        return b.exists(selected, [b.branch([
            b.cond('HAS_KV_ANY', selected, lit('目标单位', 100003))], [b.set(target, get_target), legal])])

    def iterate(core, body):
        group = ex(100203, 'GET_PROJECTILE_GROUP_KV', clone(core), lit('游剑-组', 100003))
        # PROJECTILE_GROUP is not an allowed TYPE_IS_EXIST operand. The live
        # owning core initializes this key synchronously before use.
        return b.node('PICK_PROJECTILE_DO_ACTION', group, ex(100022, 1, body))

    def scan_auto(core):
        body = visit(GAIN, owner, lambda target: [b.set(actor_target, target), b.node('BREAK_LOOP')])
        chosen = b.exists(actor_target, [b.branch([*alive(b, actor_target),
            b.cond('IS_ENEMY', actor_target, owner)], [release])])
        return [iterate(core, body), chosen]

    checks = clone(old_auto['args_list'][0]['args_list'])
    assert checks[0]['condition_type'] == 'TYPE_IS_EXIST'
    checks = checks[1:]
    safe_auto = b.exists(current, [b.exists(owner, [
        b.set(actor_target, ex(100006, 'NONE_UNIT')),
        b.branch([*alive(b, owner), *checks], core_body(GAIN, owner, scan_auto))])])
    timer['args_list'][3]['args_list'] = [safe_auto]

    old_cast = cast['action']
    assert len(old_cast) == 4
    manual, final_damage, animation, old_scan = old_cast
    assert old_scan['action_type'] == 'PICK_PROJECTILE_DO_ACTION'
    old_delay = one(old_scan, 'RUN_ONCE_TIMER_NO_SAVE')
    old_sfx, old_damage = one(old_delay, 'CREATE_SFX_ON_POINT_NEW'), one(old_delay, 'APPLY_DAMAGE')
    source = b.var(CAST, 'UNIT_ENTITY', '施法者')
    skill = b.var(CAST, 'ABILITY', '技能')
    wave = b.var(CAST, 'INTEGER', '波次')
    live_core = b.var(CAST, 'MODIFIER_ENTITY', '回调当前核心')
    count = b.var(CAST, 'INTEGER', '有效游剑数')
    targets = [b.var(CAST, 'UNIT_ENTITY', '目标' + str(k)) for k in (1, 2, 3)]
    points = [b.var(CAST, 'POINT', '位置' + str(k)) for k in (1, 2, 3)]

    def cast_effect(core):
        initialize = [b.set(count, lit(0)), *[b.set(t, ex(100006, 'NONE_UNIT')) for t in targets]]
        def capture(target):
            body = [b.set(count, ex(100002, 'INT_PLUS_ONE', clone(count)))]
            for k, (slot, point) in enumerate(zip(targets, points), 1):
                body.append(b.branch([b.cmp(count, '==', lit(k))], [b.set(slot, target),
                    b.set(point, ex(100004, 'PROJECTILE_ENTITY_POINT', clone(selected)))]))
            return [b.branch([b.cmp(count, '<', lit(3))], body)]
        result = [*initialize, iterate(core, visit(CAST, source, capture))]
        for target, point in zip(targets, points):
            damage, sfx, delay = b.fresh(old_damage), b.fresh(old_sfx), b.fresh(old_delay)
            damage['args_list'][0:3] = [clone(source), clone(skill), clone(target)]
            sfx['args_list'][1] = clone(point)
            lookup = ex(100076, 'GET_LAST_MODIFIER_INSTANCE', clone(source), lit(CORE, 100046))
            apply = b.exists(live_core, [b.branch([
                b.cmp(live_core, '==', core, 'MODIFIER_COMPARE')], [sfx, damage])])
            active = b.branch([*alive(b, source), *alive(b, target), b.cond('IS_ENEMY', target, source),
                b.cmp(global_int(PHASE), '==', lit(2)), b.cmp(global_int(WAVE), '==', wave)],
                [b.exists(core, [b.set(live_core, lookup), apply])])
            callback = b.exists(skill, [b.exists(source, [b.exists(target, [b.exists(point, [active])])])])
            delay['args_list'][1]['args_list'] = [callback]
            result.append(b.exists(target, [delay]))
        return [b.set(wave, global_int(WAVE)), final_damage, animation, *result]

    payload = core_body(CAST, source, cast_effect)
    cast['action'] = [b.set(skill, current), b.exists(skill, [b.set(source, owner),
        b.exists(source, [b.branch([*alive(b, source), b.cmp(global_int(PHASE), '==', lit(2))],
                                 [manual, *payload])])])]
    return doc


def build(root: Path):
    core = json.loads((root / f'modifier/{CORE}.json').read_text('utf8'))
    generators = [n for n in walk(core['trigger_dict']['1485688834']['action'])
                  if n.get('action_type') == 'RUN_COUNT_TIMER']
    assert len(generators) == 1 and generators[0]['args_list'][2] == lit(3), 'Sword count changed'
    assert any(n.get('args_list') == [ex(100076, 'CUR_MODIFIER'), lit('游剑-组', 100003),
                                     ex(100203, 'CREATE_PROJECTILE_GOURP')]
               for n in walk(core) if n.get('action_type') == 'SET_ENTITY_KV')
    doc = json.loads((root / FILE).read_text('utf8'))
    return {FILE: patch(doc)}, [dict(status='candidate', object=134222169,
        effect='Ordered owner/core/KV/projectile/target gates; clear stale auto target; '
               'three independent target/point snapshots, no delayed projectile-context reads; '
               'wave/core identity and living source/target gates at delayed damage',
        validation='offline candidate; editor and battle verification required')]
