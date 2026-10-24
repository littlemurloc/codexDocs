"""Scoped Tai Shi Ci auto-cast repair; no design or shared-function changes."""
from copy import deepcopy as clone
import json
import y3_hero_repair_publish as pub
from y3_sunshangxiang_orbit_fix import Builder, ex, lit, ref, one, walk, alive, global_int

PHASE = 'taishi-autocast-20261022'
IDS = (134259517, 134273833, 134275696)
TEAM = '869622f5961411f1933a3fb31c846afd'
STATE = '97642c3d802a5935a73289745a266ac8'


def declare_buff(doc, tid):
    name = '太史慈施法检查_战书'
    data = doc['local_variable'][tid]
    assert name not in data['variable_length_dict']
    data['variable_dict'].setdefault('MODIFIER_ENTITY', {})[name] = 0
    data['variable_length_dict'][name] = 0
    v = doc['trigger_dict'][tid]['var_data']
    v[0].setdefault('MODIFIER_ENTITY', {})[name] = 0
    v[1][name] = 0
    v[2].append(name)
    return ref('MODIFIER_ENTITY', name)


def patch(original, oid):
    doc = clone(original)
    b = Builder(doc)
    tid = '1959489540'
    gain = doc['trigger_dict'][tid]
    timer = one(gain['action'], 'RUN_LOOP_TIMER')
    current, owner = ex(100014, 'CUR_ABILITY'), ex(100006, 'ABILITY_OWNER')
    selected = ex(100006, 'FOR_EACH_SELECTED_UNIT')
    target = ref('UNIT_ENTITY', '目标单位', 'actor')
    old_body = timer['args_list'][3]['args_list']
    release = clone(one(old_body, 'UNIT_RELEASE_COMMAND'))
    # Keep the original native target-unit option, not a location-only command.
    assert release['args_list'][1]['op_arg_enable'] == [False, False, True, False, False]
    assert release['args_list'][1]['op_arg'][2] == target
    scan = clone(one(old_body, 'PICK_UNIT_DO_ACTION'))
    if oid == IDS[0]:
        # Preserve the original target preference and scan radius.
        visit = scan['args_list'][1]['args_list']
        scan['args_list'][1]['args_list'] = [b.exists(selected, [b.branch([
            *alive(b, selected), b.cond('IS_ENEMY', selected, owner)], visit)])]
        effect = [scan, b.exists(target, [b.branch([
            *alive(b, target), b.cond('IS_ENEMY', target, owner)], [release])])]
    else:
        search = doc['trigger_dict']['82759685']
        assert [n['action_type'] for n in search['action']] == ['CLEAR_GROUP', 'SET_VARIABLE']
        assign = clone(search['action'][1])
        assert assign['args_list'][1]['sub_type'] == TEAM
        # The returned team is borrowed. Neither the phase callback nor this
        # periodic scan may mutate it. Refresh also handles mid-wave acquisition.
        search['action'] = [search['action'][1]]
        old_checks = scan['args_list'][1]['args_list'][0]['args_list'][0]['args_list']
        assert [c['condition_type'] for c in old_checks[:2]] == ['UNIT_HAS_MODIFIER', 'UNIT_COMPARE']
        letter = declare_buff(doc, tid)
        lookup = ex(100076, 'GET_LAST_MODIFIER_INSTANCE', clone(selected), lit(134274015, 100046))
        source_check = b.cmp(ex(100006, 'GET_BUFF_SOURCE', clone(letter)), '==', owner, 'UNIT_COMPARE')
        checks = [source_check]
        if oid == IDS[2]:
            assert len(old_checks) == 3
            checks.append(clone(old_checks[2]))  # Preserve the existing <=50% gate.
        else:
            assert len(old_checks) == 2
        payload = [b.set(target, selected), release, b.node('BREAK_LOOP')]
        qualified = b.exists(letter, [b.branch(checks, payload)])
        valid_target = b.exists(selected, [b.branch([
            *alive(b, selected), b.cond('IS_ENEMY', selected, owner)],
            [b.set(letter, lookup), qualified])])
        scan['args_list'][1]['args_list'] = [valid_target]
        effect = [assign, scan]
    checks = [*alive(b, owner),
        b.cmp(ex(100000, 'ABILITY_CD_LEFT_TIME', clone(current)), '==', lit(0.0, 100000)),
        b.cmp(global_int('当前游戏进程阶段'), '==', lit(2)),
        b.cmp(ex(100001, 'GET_BOOLEAN_KV', clone(owner), lit('自动施法', 100003)),
              '==', lit(True, 100001), 'BOOL_COMPARE'),
        b.cmp(dict(arg_type=100001, sub_type=STATE, args_list=[clone(owner)],
                   call_rt_index=0, op_arg=[], op_arg_enable=[]),
              '==', lit(True, 100001), 'BOOL_COMPARE')]
    timer['args_list'][3]['args_list'] = [b.exists(current, [b.exists(owner, [
        b.branch(checks, [b.set(target, ex(100006, 'NONE_UNIT')), *effect])])])]
    return doc


def stage():
    work = pub.WORK / PHASE
    assert not work.exists(), 'Never overwrite baseline'
    baseline = {p.relative_to(pub.MAP).as_posix(): pub.sha(p.read_bytes()) for p in pub.map_files()}
    entries = []
    for oid in IDS:
        rel = f'ability/{oid}.json'
        raw = (pub.MAP / rel).read_bytes()
        source = json.loads(raw)
        result = patch(source, oid)
        pub.write_generated(work / 'original' / rel, raw)
        encoded = pub.encode(result)
        pub.write_generated(work / 'staged' / rel, encoded)
        entries.append(dict(path=rel, before=pub.sha(raw), after=pub.sha(encoded),
                            pointers=pub.compare(source, result)))
    pub.write_generated(work / 'manifest.json', pub.encode(dict(
        map=str(pub.MAP), phase=PHASE, entries=entries, notes=[],
        protected={f: h for f, h in baseline.items() if f not in {e['path'] for e in entries}})))
    print(json.dumps({'phase': PHASE, 'files': len(entries), 'protected': len(baseline)-len(entries)}))


if __name__ == '__main__':
    stage()
