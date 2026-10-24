"""Add or remove literal Y3 skill diagnostics by an exact, portable registry.

prepare-add/prepare-remove only stage changes. publish requires the editor to
be closed or an explicitly coordinated reload. Never restore entire old ECA
files to remove logs: preserve current gameplay edits and remove registered
literal print nodes only.
"""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil

from y3_native_skill_log_probe import PREFIX, instrument, read, save, sha, walk

PROJECT = Path(__file__).resolve().parents[1]
REGISTRY = PROJECT / 'tools/data/y3-skill-trace-registry.json'
LEGACY = PROJECT / 'tmp/native-skill-log-20261023/manifest.json'
SLOTS = [(1, '技能1'), (2, '技能5'), (3, '技能2'),
         (4, '技能6'), (5, '技能3'), (6, '技能7')]


def files(root):
    for directory, folders, names in os.walk(root):
        folders[:] = sorted(f for f in folders if f != '.git')
        for name in sorted(names):
            yield Path(directory) / name


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                    separators=(',', ':')).encode()).hexdigest()


def log_node(element_id, message):
    return {'action_type': 'PRINT_MESSAGE_ACTION_TO_DIALOG',
            'args_list': [{'arg_type': 100175, 'sub_type': 1, 'args_list': [3]},
                          {'arg_type': 100003, 'sub_type': 1, 'args_list': [message]}],
            'bp': False, 'element_id': element_id, 'enable': True}


def checked_nodes(document, records):
    expected = {entry['element_id']: entry for entry in records}
    assert len(expected) == len(records), 'Duplicate IDs in registry'
    matches = {key: [] for key in expected}
    for node in walk(document):
        key = node.get('element_id')
        if key not in expected:
            continue
        reference = log_node(key, expected[key]['message'])
        assert node.get('action_type') == reference['action_type'], f'Log ID reused: {key}'
        assert node.get('args_list') == reference['args_list'], f'Log changed; review required: {key}'
        matches[key].append(node)
    for key, nodes in matches.items():
        assert len(nodes) == 1, f'Expected one log node, got {len(nodes)}: {key}'
    return set(expected)


def remove_registered(document, records):
    ids = checked_nodes(document, records)
    removed = []

    def clean(value):
        if isinstance(value, list):
            result = []
            for child in value:
                if isinstance(child, dict) and child.get('element_id') in ids:
                    removed.append(child['element_id'])
                else:
                    result.append(clean(child))
            return result
        if isinstance(value, dict):
            return {key: clean(child) for key, child in value.items()}
        return value
    result = clean(document)
    assert set(removed) == ids and len(removed) == len(ids)
    return result


def discover(root):
    data = read(root / 'tables/单位技能配置表.json')['table_data']['data']
    columns = {name: i for i, name in enumerate(data[0]) if name}
    loops = read(root / 'tables/技能特有循环机制表.json')['table_data']['data']
    loop_columns = {name: i for i, name in enumerate(loops[0]) if name}
    records = {}
    heroes = []
    for row in data[2:]:
        values = [row[columns[name]] for _, name in SLOTS]
        if not any(isinstance(v, int) and v not in (0, 134255698) for v in values):
            continue
        hero = row[columns['单位名称']]
        assert hero and hero not in heroes
        assert all(isinstance(v, int) and v not in (0, 134255698) for v in values), hero
        heroes.append(hero)
        for (star, _), resource in zip(SLOTS, values):
            relative = f'ability/{resource}.json'
            assert relative not in records, 'Shared hero skill requires manual review: ' + relative
            records[relative] = {'hero': hero, 'resource_id': resource,
                                 'role': f'{star}星' + ('主动' if star % 2 else '被动')}
        # Select by actual skill associations, never by table row position.
        matched = [loop for loop in loops[2:] if any(
            loop[loop_columns[f'关联技能{i}']] in values for i in (1, 2, 3))]
        assert len(matched) == 1, f'Expected one core loop for {hero}, got {len(matched)}'
        resource = matched[0][loop_columns['能力循环机制BUFF']]
        relative = f'modifier/{resource}.json'
        assert relative not in records, 'Shared core requires manual review: ' + relative
        records[relative] = {'hero': hero, 'resource_id': resource, 'role': '核心循环'}
    gaps = []
    for relative in list(records):
        if (root / relative).is_file():
            continue
        metadata = records.pop(relative)
        assert relative.startswith('ability/'), 'Missing core ECA: ' + relative
        object_file = root / 'editor_table/abilityall' / Path(relative).name
        assert object_file.is_file(), 'Missing skill object: ' + relative
        gaps.append({'path': relative, **metadata,
                     'reason': 'No independent skill ECA; no trigger invented for logging.'})
    return records, heroes, gaps


def load_registry(root, specs):
    if REGISTRY.exists():
        registry = read(REGISTRY)
        assert registry['schema'] == 1 and registry['prefix'] == PREFIX
        return registry
    assert LEGACY.is_file(), 'Initial three-hero manifest is required for adoption'
    legacy = read(LEGACY)
    entries = {}
    for entry in legacy['entries']:
        relative = entry['path']
        assert relative in specs, 'Existing diagnostic outside current roster'
        checked_nodes(read(root / relative), entry['logs'])
        entries[relative] = {**specs[relative], 'logs': entry['logs'], 'batch': 'native-three-20261023'}
    return {'schema': 1, 'prefix': PREFIX, 'map_identity': 'ProjectMonster02/map3',
            'entries': entries, 'note': 'Keep this registry for exact node-only removal; no full-file rollback.'}


def prepare(root, work, operation):
    assert not work.exists(), 'Never overwrite a previous stage or recovery backup'
    assert root.is_dir() and root.name == 'map3'
    assert work.resolve().is_relative_to((PROJECT / 'tmp').resolve())
    specs, heroes, gaps = discover(root)
    registry_before = sha(REGISTRY) if REGISTRY.exists() else None
    registry = load_registry(root, specs)
    registry['coverage_gaps'] = gaps
    assert set(registry['entries']) <= set(specs), 'Roster changed; review registry first'
    for relative, entry in registry['entries'].items():
        assert all(entry[key] == specs[relative][key] for key in ('hero', 'role', 'resource_id'))
        checked_nodes(read(root / relative), entry['logs'])
    work.mkdir(parents=True)
    backup = work / 'map3-before'
    shutil.copytree(root, backup, ignore=shutil.ignore_patterns('.git'))
    shutil.copy2(root.parents[1] / 'header.project', work / 'header.project.before')
    baseline = {p.relative_to(backup).as_posix(): sha(p) for p in files(backup)}
    save(work / 'registry-before.json', registry)
    occupied = set()
    for path in files(backup):
        if path.suffix not in ('.json', '.txt'):
            continue
        try:
            occupied.update(n['element_id'] for n in walk(read(path)) if 'element_id' in n)
        except (ValueError, UnicodeError):
            continue
    def sequence():
        current = 209996500100000
        while True:
            current += 1
            if current not in occupied:
                occupied.add(current)
                yield current
    ids = sequence()
    changes = []
    for relative, metadata in specs.items():
        source = read(backup / relative)
        if operation == 'add':
            if relative in registry['entries']:
                continue
            assert not any(PREFIX in str(n['args_list']) for n in walk(source)
                           if n.get('action_type') == 'PRINT_MESSAGE_ACTION_TO_DIALOG'), \
                'Unregistered existing diagnostics: ' + relative
            label = metadata['hero'] + '/' + metadata['role'] + '#' + str(metadata['resource_id'])
            candidate, logs = instrument(source, label, ids)
            assert logs, 'No diagnostic nodes generated: ' + relative
            assert remove_registered(candidate, logs) == source
            registry['entries'][relative] = {**metadata, 'logs': logs, 'batch': work.name}
        else:
            if relative not in registry['entries']:
                continue
            logs = registry['entries'][relative]['logs']
            candidate = remove_registered(source, logs)
            del registry['entries'][relative]
        path = work / 'candidate' / relative
        save(path, candidate)
        changes.append({'path': relative, 'before': baseline[relative], 'after': sha(path),
                        'logs': logs, 'gameplay_before': digest(remove_registered(source, logs)
                            if operation == 'remove' else source)})
    manifest = {'schema': 1, 'operation': operation, 'map': str(root),
                'created': datetime.now().isoformat(), 'heroes': heroes, 'coverage_gaps': gaps,
                'baseline': baseline, 'entries': changes,
                'registry_before_sha': registry_before,
                'scope': 'Six skills plus configured core per hero. No shared functions or auxiliary status Buffs.'}
    save(work / 'registry-after.json', registry)
    manifest['registry_after_sha'] = sha(work / 'registry-after.json')
    save(work / 'manifest.json', manifest)
    print(json.dumps({'phase': 'prepared', 'operation': operation, 'heroes': len(heroes),
                      'files_changed': len(changes), 'new_or_removed_log_nodes': sum(len(e['logs']) for e in changes),
                      'registry_files_after': len(registry['entries']), 'coverage_gaps': gaps,
                      'work': str(work)}, ensure_ascii=False))


def verify(work, exact=False):
    manifest = read(work / 'manifest.json')
    root = Path(manifest['map'])
    for entry in manifest['entries']:
        current = read(root / entry['path'])
        if manifest['operation'] == 'add':
            current = remove_registered(current, entry['logs'])
        assert digest(current) == entry['gameplay_before'], 'Gameplay changed: ' + entry['path']
        if exact:
            assert sha(root / entry['path']) == entry['after']
    registry = read(work / 'registry-after.json')
    for relative, entry in registry['entries'].items():
        checked_nodes(read(root / relative), entry['logs'])
    assert REGISTRY.is_file() and sha(REGISTRY) == manifest['registry_after_sha']
    return {'operation': manifest['operation'], 'files_changed': len(manifest['entries']),
            'hero_count': len(manifest['heroes']), 'registered_eca_files': len(registry['entries']),
            'registered_log_nodes': sum(len(e['logs']) for e in registry['entries'].values()),
            'coverage_gaps': registry.get('coverage_gaps', []),
            'only_log_changes_verified': True}


def publish(work):
    manifest = read(work / 'manifest.json')
    root = Path(manifest['map'])
    assert not (work / 'published.json').exists(), 'Already published'
    assert (sha(REGISTRY) if REGISTRY.exists() else None) == manifest['registry_before_sha']
    assert sha(work / 'registry-after.json') == manifest['registry_after_sha']
    assert set(manifest['baseline']) == {p.relative_to(root).as_posix() for p in files(root)}
    for relative, expected in manifest['baseline'].items():
        assert sha(root / relative) == expected, 'Map changed since staging: ' + relative
    for entry in manifest['entries']:
        assert sha(work / 'candidate' / entry['path']) == entry['after']
    for entry in manifest['entries']:
        shutil.copy2(work / 'candidate' / entry['path'], root / entry['path'])
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(work / 'registry-after.json', REGISTRY)
    receipt = verify(work, exact=True)
    changed = {e['path'] for e in manifest['entries']}
    for relative, expected in manifest['baseline'].items():
        if relative not in changed:
            assert sha(root / relative) == expected, 'Unrelated file changed: ' + relative
    receipt['published'] = datetime.now().isoformat()
    save(work / 'published.json', receipt)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare-add', 'prepare-remove', 'publish', 'verify'])
    parser.add_argument('--map', type=Path)
    parser.add_argument('--work', type=Path, required=True)
    options = parser.parse_args()
    if options.action.startswith('prepare-'):
        assert options.map is not None, '--map is required when preparing'
        prepare(options.map.resolve(), options.work.resolve(), options.action.removeprefix('prepare-'))
    elif options.action == 'publish':
        publish(options.work.resolve())
    else:
        result = verify(options.work.resolve())
        save(options.work / 'verified.json', result)
        print(json.dumps(result, ensure_ascii=False))
