"""Post-editor correction: cast-only target getters cannot run in Buff events."""
import copy
import json
from pathlib import Path

CORE = 'modifier/134277456.json'
ACTIVES = (134259517, 134273833, 134275696)
PRIMARY = 'P2太史慈主动主目标'
READY = 'P2太史慈主目标已记录'


def ex(t, s, *args):
    return dict(arg_type=t, sub_type=s, args_list=list(args))


def walk(v):
    if isinstance(v, dict):
        yield v
        for x in v.values():
            yield from walk(x)
    elif isinstance(v, list):
        for x in v:
            yield from walk(x)


def nodes(doc):
    index = max(n.get('element_id', 0) for n in walk(doc))
    def make(kind, *args, condition=False):
        nonlocal index
        index += 1
        n = dict(element_id=index, enable=True, args_list=list(args))
        n['condition_type' if condition else 'action_type'] = kind
        if not condition:
            n['bp'] = False
        return n
    return make


def branch(make, checks, yes):
    n = make('IF_THEN_ELSE', ex(100021, 1, *checks), ex(100022, 1, *yes), ex(100022, 1))
    n['fake_op'] = []
    return n


def patch_active(original):
    doc = copy.deepcopy(original)
    make = nodes(doc)
    cast = doc['trigger_dict']['893440004']
    assert any(e['event_type'] == 'ABILITY_SP_END' for e in cast['event'])
    first = cast['action'][0]
    assert first['element_id'] == 893440004974041
    assert any(n.get('sub_type') == 'GET_ABILITY_TARGET_UNIT_FROM_EVENT' for n in walk(first))
    assert not any(n.get('args_list') == [PRIMARY] for n in walk(doc))
    ability = ex(100014, 'CUR_ABILITY')
    target = ex(100006, 11, {'__tuple__': True, 'items': ['UNIT_ENTITY', '目标单位', 'actor']})
    clear = make('SET_ENTITY_KV', ability, ex(100003, 1, READY), ex(100001, 1, False))
    store = [make('SET_ENTITY_KV', ability, ex(100003, 1, PRIMARY), target),
             make('SET_ENTITY_KV', ability, ex(100003, 1, READY), ex(100001, 1, True))]
    capture = branch(make, [make('TYPE_IS_EXIST', target, condition=True)], store)
    cast['action'][0:1] = [clear, first, capture]
    return doc


def patch_core(original):
    doc = copy.deepcopy(original)
    make = nodes(doc)
    hurt = doc['trigger_dict']['1418035204']
    ability = ex(100014, 'DAMAGE_ABILITY')
    replacements = 0
    for n in walk(hurt['action']):
        if n.get('sub_type') == 'TARGET_UNIT_IN_ABILITY':
            assert n['args_list'] == [ability]
            n.clear()
            n.update(ex(100006, 'GET_UNIT_ENTITY_KV', ability, ex(100003, 1, PRIMARY)))
            replacements += 1
    assert replacements == 2, replacements
    known = [make('HAS_KV_ANY', ability, ex(100003, 1, PRIMARY), condition=True),
             make('HAS_KV_ANY', ability, ex(100003, 1, READY), condition=True)]
    ready = make('BOOL_COMPARE', ex(100001, 'GET_BOOLEAN_KV', ability, ex(100003, 1, READY)),
                 ex(100035, 1, '=='), ex(100001, 1, True), condition=True)
    hurt['action'] = [branch(make, known, [branch(make, [ready], hurt['action'])])]
    # Revalidate after removing the cast-context expression, not merely flipping flags.
    hurt['valid'] = True
    doc['trigger_dict']['1485688834']['valid'] = True
    return doc


def build(root: Path):
    payload = {CORE: patch_core(json.loads((root / CORE).read_text('utf8')))}
    for aid in ACTIVES:
        path = f'ability/{aid}.json'
        payload[path] = patch_active(json.loads((root / path).read_text('utf8')))
    return payload, [dict(status='candidate', issue='28-editor-context',
                         files=list(payload), validation='requires delayed editor save/readback',
                         effect='Three actives record primary after manual-target override; '
                                'Buff damage event reads guarded KV, not cast runtime context')]
