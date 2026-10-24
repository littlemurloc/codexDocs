"""Scoped loop UI lifecycle repair; stage only, publish with the receipt tool."""
import copy
import json
from pathlib import Path
import y3_hero_repair_publish as pub
import y3_hero_repair_editor_audit as audit

PHASE = 'loop-reinit-20261022'
FUNCTION = 'global_trigger/function/new/功能执行/根据拥有技能赋予能力循环机制.json'
MACH = 'modifier/134265433.json'


def ex(kind, sub, *args):
    return dict(arg_type=kind, sub_type=sub, args_list=list(args))


def walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)


def build(doc):
    d = copy.deepcopy(doc)
    assert d['func_id'] == '249a7f506a0511f1acc343869eb6b152'
    cleanup, rebuild = d['action']
    assert cleanup['element_id'] == 1935909566000174
    assert rebuild['action_type'] == 'ITER_ABILITY_DO'
    old = cleanup['args_list'][1]['args_list']
    assert [a['action_type'] for a in old] == [
        'REMOVE_BUFF_INS', 'TRAVERSE_TABLE_NEW', 'CLEAR_TABLE',
        'SET_UI_COMP_TEXT', 'SET_UI_COMP_VISIBLE']
    unit = copy.deepcopy(rebuild['args_list'][0])
    next_id = max(n.get('element_id', 0) for n in walk(d))

    def node(key, name, *args):
        nonlocal next_id
        next_id += 1
        n = {key: name, 'args_list': list(args), 'element_id': next_id, 'enable': True}
        if key == 'action_type':
            n['bp'] = False
        return n

    def exists(obj):
        return node('condition_type', 'TYPE_IS_EXIST', copy.deepcopy(obj))

    def has(key):
        return node('condition_type', 'HAS_KV_ANY', copy.deepcopy(unit), ex(100003, 1, key))

    def branch(conditions, actions):
        return node('action_type', 'IF_THEN_ELSE', ex(100021, 1, *conditions),
                    ex(100022, 1, *actions), ex(100022, 1))

    # UI ownership survives the logical-death window, independently of the Buff.
    ui_clear = branch([has('能量格数据表')], old[1:3])
    panel_clear = branch([has('循环机制面板')], old[3:5])
    remove = branch([has('能力循环机制')], [branch([exists(old[0]['args_list'][0])], [old[0]])])
    matched = [n for n in walk(rebuild) if n.get('element_id') == 1935909566000308]
    assert len(matched) == 1
    body = matched[0]['args_list'][1]['args_list']
    assert [a['element_id'] for a in body] == [1935909566000302, 1935909566000303,
        1935909566000324, 1935909566000305, 1935909566000306, 1935909566000307]
    buff = copy.deepcopy(body[0]['args_list'][0])
    # No name/maximum/UI reads if ADD_MODIFIER failed. Still stop after a match.
    matched[0]['args_list'][1]['args_list'] = [body[0], branch([exists(buff)], body[1:-1]), body[-1]]
    alive = copy.deepcopy(cleanup['args_list'][0]['args_list'][1])
    not_dead = copy.deepcopy(cleanup['args_list'][0]['args_list'][2])
    assert alive['condition_type'] == 'IS_UNIT_ALIVE'
    assert not_dead['condition_type'] == 'BOOL_NOT'
    assert '已死亡' in json.dumps(not_dead, ensure_ascii=False)
    # Engine life is supplemental; the project's pseudo-death tag is mandatory.
    d['action'] = [branch([exists(unit)], [ui_clear, panel_clear, remove,
                                          branch([not_dead, alive], [rebuild])])]
    d['func_comment'] = (d.get('func_comment', '') +
        '\n2026-10-22：先独立清理旧能量格与面板，再按实例有效性移除旧循环；'
        '仅未处于项目伪死亡且引擎存活的单位重建。新 Buff 无效时不读层数或名称。')
    return d


def allowed_diffs(expected, actual):
    return [(p, repr(a)[:80], repr(b)[:80]) for p, a, b in audit.differences(expected, actual)
            if not ((p.endswith('/fake_op') and (a is audit.MISSING or a == []) and b == [2])
                    or (p.endswith('/local_var') and a is audit.MISSING
                        and b == {'__tuple__': True, 'items': [{}, {}]}))]


def stage():
    work = pub.WORK / PHASE
    assert not work.exists(), 'Never replace an existing backup'
    ab = pub.WORK / 'ab-20261022'
    live_mach = json.loads((pub.MAP / MACH).read_text('utf8'))
    expected_ab = json.loads((ab / 'mach' / MACH).read_text('utf8'))
    assert not allowed_diffs(expected_ab, live_mach), 'Ma Chao was edited since A/B; stop'
    current = json.loads((pub.MAP / FUNCTION).read_text('utf8'))
    patched = build(current)
    restored = json.loads((ab / 'baseline' / MACH).read_text('utf8'))
    baseline = {p.relative_to(pub.MAP).as_posix(): pub.sha(p.read_bytes()) for p in pub.map_files()}
    entries = []
    for rel, doc in [(FUNCTION, patched), (MACH, restored)]:
        raw = (pub.MAP / rel).read_bytes()
        pub.write_generated(work / 'original' / rel, raw)
        encoded = pub.encode(doc)
        pub.write_generated(work / 'staged' / rel, encoded)
        entries.append(dict(path=rel, before=pub.sha(raw), after=pub.sha(encoded),
                            pointers=pub.compare(json.loads(raw), doc)))
    manifest = dict(map=str(pub.MAP), phase=PHASE, entries=entries, notes=[],
                    protected={f: h for f, h in baseline.items() if f not in [FUNCTION, MACH]})
    pub.write_generated(work / 'manifest.json', pub.encode(manifest))
    print(json.dumps({'phase': PHASE, 'files': len(entries), 'protected': len(manifest['protected'])}))


if __name__ == '__main__':
    stage()
