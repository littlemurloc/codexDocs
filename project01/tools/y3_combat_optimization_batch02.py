"""Maintain exact registered skill-trace enable flags and counter helpers.

The trace switch is an offline maintenance setting: no extra in-game branches.
Initial counter deployment retired after delivery; only new trace-only batches
may be staged/published. Frozen counter examples remain regression inputs.
"""
from __future__ import annotations
import argparse
import copy
import csv
import json
import os
import re
from pathlib import Path
import subprocess
import zipfile
import y3_damage_context_optimization as base
import y3_skill_trace_manager as trace_manager

MAP = base.MAP
PROJECT = Path(__file__).resolve().parents[1]
WORK = PROJECT / 'tmp/combat-performance-20261030/batch02'
REGISTRY = PROJECT / 'tools/data/y3-skill-trace-registry.json'
MODE = PROJECT / 'tools/data/y3-skill-trace-mode.json'
COUNTER = 'global_trigger/function/new/条件判断/判断兵种是否产生克制关系.json'
NAMES = ('本次输出单位类型', '本次承受单位类型')
IDS = (2099947101000001, 2099947101000002, 2099947101000003)
load, encode, sha, walk, at = base.load, base.encode, base.sha, base.walk, base.at


def type_ref(name):
    return base.expr(100116, 2, {'__tuple__': True, 'items': ['UNIT_NAME', name, 'local']})


def patch_counter(original):
    doc = copy.deepcopy(original)
    assert doc['func_id'] == '568f4bfd9c5c11f1a9c94123bbd68bd9'
    assert not set(NAMES) & set(doc['var_data'][1]), 'Counter already patched'
    edits, initializers = [], {}
    for path, node in list(walk(doc['action'], active=True)):
        if node.get('sub_type') != 'GET_UNIT_KEY_OF_UNIT':
            continue
        owner = node['args_list'][0]['args_list'][0]['items'][1]
        assert owner in ('输出单位', '承受单位')
        name = NAMES[0 if owner == '输出单位' else 1]
        initializers[name] = copy.deepcopy(node)
        edits.append(dict(path=list(path), original=copy.deepcopy(node)))
        node.clear()
        node.update(type_ref(name))
    assert len(edits) == 20
    assignments = []
    for index, name in enumerate(NAMES):
        doc['var_data'][0].setdefault('UNIT_NAME', {})[name] = 0
        doc['var_data'][1][name] = 0
        doc['var_data'][2].append(name)
        assignments.append(dict(action_type='SET_VARIABLE', element_id=IDS[index],
                                bp=False, enable=True,
                                args_list=[base.expr(100030, 1, *type_ref(name)['args_list']), initializers[name]]))
    doc['action'].insert(0, dict(action_type='STORAGE_BOX', element_id=IDS[2], bp=False, enable=True,
        args_list=[base.expr(100021, 1), base.expr(100022, 1, *assignments), base.expr(100022, 1),
                   base.expr(100003, 1, '本次克制判断：双方类型各取一次，原五条克制关系保持')]))
    assert undo_counter(doc, edits) == original
    return doc, edits


def undo_counter(candidate, edits):
    doc = copy.deepcopy(candidate)
    assert doc['action'].pop(0)['element_id'] == IDS[2]
    for row in edits:
        node = at(doc['action'], row['path'])
        node.clear()
        node.update(copy.deepcopy(row['original']))
    del doc['var_data'][0]['UNIT_NAME']
    for name in NAMES:
        del doc['var_data'][1][name]
        doc['var_data'][2].remove(name)
    return doc


def toggle_logs(original, records, enabled):
    doc = copy.deepcopy(original)
    by_id = {}
    for _, node in walk(doc):
        by_id.setdefault(node.get('element_id'), []).append(node)
    changes = []
    for row in records:
        matches = by_id.get(row['element_id'], [])
        assert len(matches) == 1, 'Registered log missing or duplicated'
        node = matches[0]
        assert node.get('action_type') == 'PRINT_MESSAGE_ACTION_TO_DIALOG'
        assert node['args_list'] == [base.expr(100175, 1, 3), base.expr(100003, 1, row['message'])]
        assert row['message'].startswith('[技能追踪/简版v1] ')
        assert isinstance(node.get('enable'), bool)
        changes.append(dict(element_id=row['element_id'], before=node['enable']))
        node['enable'] = enabled
    return doc, changes


def undo_logs(candidate, changes):
    doc = copy.deepcopy(candidate)
    flags = {row['element_id']: row['before'] for row in changes}
    for _, node in walk(doc):
        if node.get('element_id') in flags:
            node['enable'] = flags[node['element_id']]
    return doc


def stage(enabled, trace_only=True):
    assert trace_only, 'Initial counter deployment retired; use trace-only maintenance'
    assert not WORK.exists(), 'Do not overwrite a previous batch; review its manifest'
    registry = load(REGISTRY)
    legacy = trace_manager.legacy_records()
    assert registry['map_identity'] == 'ProjectMonster02/map3'
    entries = []
    for rel in dict.fromkeys(list(registry['entries']) + list(legacy)):
        raw = (MAP / rel).read_bytes()
        original = json.loads(raw)
        candidate, edits = (toggle_logs(original, registry['entries'][rel]['logs'], enabled)
                            if rel in registry['entries'] else (copy.deepcopy(original), []))
        if rel in legacy:
            candidate, extra = trace_manager.toggle_legacy_registered(candidate, legacy[rel]['logs'], enabled)
            edits.extend(extra)
        assert undo_logs(candidate, edits) == original
        detail = dict(kind='trace', changes=edits)
        payload = encode(candidate)
        for folder, data in [('before', raw), ('staged', payload)]:
            dest = WORK / folder / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        entries.append(dict(path=rel, before=sha(raw), after=sha(payload), **detail))
    manifest = dict(map=str(MAP), entries=entries, trace_enabled=enabled,
                    registry_sha256=sha(REGISTRY.read_bytes()),
                    mode_before=sha(MODE.read_bytes()) if MODE.exists() else None,
                    protected_step01_sha256=sha((MAP / base.REL).read_bytes()))
    if legacy:
        manifest['legacy_registry_sha256'] = sha(trace_manager.LEGACY_REGISTRY.read_bytes())
    (WORK / 'manifest.json').write_bytes(encode(manifest))
    print('Staged', len(entries), 'resources; registered trace nodes:',
          sum(len(e.get('changes', [])) for e in entries))


def verify_trace_only():
    """Verify future offline toggles without rerunning or reverting gameplay builders."""
    manifest = check(live=True)
    assert manifest['entries'] and all(row['kind'] == 'trace' for row in manifest['entries'])
    registry = load(REGISTRY)
    legacy = trace_manager.legacy_records() if 'legacy_registry_sha256' in manifest else {}
    for row in manifest['entries']:
        doc = load(WORK / 'staged' / row['path'])
        checked = doc
        if row['path'] in registry['entries']:
            checked, _ = toggle_logs(checked, registry['entries'][row['path']]['logs'], manifest['trace_enabled'])
        if row['path'] in legacy:
            checked, _ = trace_manager.toggle_legacy_registered(checked, legacy[row['path']]['logs'], manifest['trace_enabled'])
        assert checked == doc
    paths = ['tools/y3_combat_optimization_batch02.py', 'tools/y3_skill_trace_manager.py']
    (WORK / 'tests.json').write_bytes(encode(dict(passed=True,
        verification_kind='exact registered print flags; literal and audited legacy dynamic arguments; gameplay unchanged',
        resources_checked=len(manifest['entries']),
        manifest_sha256=sha((WORK / 'manifest.json').read_bytes()),
        tool_hashes={p:sha((PROJECT / p).read_bytes()) for p in paths})))
    print('Verified exact trace-only flags; gameplay expressions unchanged.')


def check(live=False):
    manifest = load(WORK / 'manifest.json')
    assert manifest['map'] == str(MAP)
    assert sha(REGISTRY.read_bytes()) == manifest['registry_sha256']
    if 'legacy_registry_sha256' in manifest:
        assert sha(trace_manager.LEGACY_REGISTRY.read_bytes()) == manifest['legacy_registry_sha256']
    for row in manifest['entries']:
        old = (WORK / 'before' / row['path']).read_bytes()
        new = (WORK / 'staged' / row['path']).read_bytes()
        assert sha(old) == row['before'] and sha(new) == row['after']
        restore = undo_counter(json.loads(new), row['edits']) if row['kind'] == 'counter' else undo_logs(json.loads(new), row['changes'])
        assert restore == json.loads(old), 'Out-of-scope changes: ' + row['path']
        if live:
            assert sha((MAP / row['path']).read_bytes()) == row['before'], 'Live resource changed: ' + row['path']
    if live:
        assert sha((MAP / base.REL).read_bytes()) == manifest['protected_step01_sha256']
        assert (sha(MODE.read_bytes()) if MODE.exists() else None) == manifest['mode_before']
    return manifest


def publish(confirmed):
    assert confirmed, 'Save and normally close Y3 and its client first'
    assert not (WORK / 'published.json').exists()
    tasks = subprocess.run(['tasklist', '/fo', 'csv', '/nh'], capture_output=True, text=True, check=True).stdout
    assert 'game_x64h.exe' not in {r[0].lower() for r in csv.reader(tasks.splitlines()) if r}
    manifest = check(live=True)
    tests = load(WORK / 'tests.json')
    assert tests['passed'] and tests['manifest_sha256'] == sha((WORK / 'manifest.json').read_bytes())
    assert all(sha((PROJECT / path).read_bytes()) == digest for path, digest in tests['tool_hashes'].items())
    archive = WORK / 'map3-before-batch02.zip'
    baseline = {}
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_STORED, allowZip64=True) as z:
        for path in sorted(MAP.rglob('*')):
            if path.is_file() and '.git' not in path.parts:
                rel = path.relative_to(MAP).as_posix();raw = path.read_bytes()
                baseline[rel] = sha(raw);z.writestr(rel, raw)
    header = MAP.parents[1] / 'header.project';header_raw = header.read_bytes()
    (WORK / 'header.project.before-batch02').write_bytes(header_raw)
    assert all(sha((MAP / p).read_bytes()) == digest for p, digest in baseline.items())
    check(live=True)
    done = []
    mode_before = MODE.read_bytes() if MODE.exists() else None
    def atomic(path, raw):
        assert path.resolve().is_relative_to(MAP.resolve()) or path == MODE
        pending = path.with_name(path.name + '.combat-pending')
        assert not pending.exists()
        try:
            pending.write_bytes(raw);os.replace(pending, path)
        finally:
            if pending.exists():pending.unlink()
    try:
        for row in manifest['entries']:
            path = MAP / row['path']
            assert sha(path.read_bytes()) == row['before']
            atomic(path, (WORK / 'staged' / row['path']).read_bytes());done.append(row)
        changed = {row['path'] for row in done}
        assert all(sha((MAP / row['path']).read_bytes()) == row['after'] for row in done)
        assert all(sha((MAP / p).read_bytes()) == digest for p, digest in baseline.items() if p not in changed)
        assert header.read_bytes() == header_raw
        atomic(MODE, encode(dict(schema=1, enabled=manifest['trace_enabled'],
            scope='Exact nodes in skill trace registry and, when included, legacy diagnostics registry; offline switch',
            batch='combat-performance-20261030/batch02')))
    except BaseException:
        for row in reversed(done):atomic(MAP / row['path'], (WORK / 'before' / row['path']).read_bytes())
        if mode_before is not None:atomic(MODE, mode_before)
        elif MODE.exists():MODE.unlink()
        raise
    (WORK / 'published.json').write_bytes(encode(dict(files=len(done), trace_enabled=manifest['trace_enabled'],
        unchanged_files=len(baseline)-len(done), editor_verified=False, runtime_verified=False,
        performance_verified=False, backup=str(archive))))
    print('Published', len(done), 'map resources; native loading and performance checks pending.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['stage-trace', 'verify-trace', 'check', 'publish'])
    parser.add_argument('--batch-name', default='trace-maintenance', help='New workspace folder for future trace-only toggles')
    parser.add_argument('--trace', choices=['off', 'on'], default='off')
    parser.add_argument('--confirmed-normal-close', action='store_true')
    args = parser.parse_args()
    assert re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', args.batch_name)
    WORK = WORK.parent / args.batch_name
    if args.action == 'stage-trace':stage(args.trace == 'on', trace_only=True)
    elif args.action == 'verify-trace':verify_trace_only()
    elif args.action == 'check':check(live=True);print('Candidate and live baseline match.')
    else:publish(args.confirmed_normal_close)
