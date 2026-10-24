"""Stage, hash-check and publish reviewed hero repairs in separate phases."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import zipfile

MAP = Path('D:/littl/testTempFile/ProjectMonster02/maps/map3')
WORK = Path(__file__).resolve().parents[1] / 'tmp/hero-repair-20261020'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(document):
    return (json.dumps(document, ensure_ascii=False, indent=4) + '\n').encode('utf8')


def write_generated(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def compare(before, after, pointer=''):
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict) and before.keys() == after.keys():
        return [x for key in before for x in compare(before[key], after[key], pointer + '/' + key)]
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [x for i, (a, b) in enumerate(zip(before, after))
                for x in compare(a, b, pointer + '/' + str(i))]
    return [pointer]


MISSING = object()


def merge_three_way(base, current, incoming, pointer=''):
    """Combine disjoint worker edits; reject ambiguous structure changes."""
    if incoming == base:
        return current
    if current == base or current == incoming:
        return incoming
    if all(isinstance(value, dict) for value in (base, current, incoming)):
        result = {}
        for key in dict.fromkeys([*base, *current, *incoming]):
            value = merge_three_way(base.get(key, MISSING), current.get(key, MISSING),
                                    incoming.get(key, MISSING), pointer + '/' + str(key))
            if value is not MISSING:
                result[key] = value
        return result
    if all(isinstance(value, list) for value in (base, current, incoming)) and len(base) == len(current) == len(incoming):
        return [merge_three_way(a, b, c, pointer + '/' + str(i))
                for i, (a, b, c) in enumerate(zip(base, current, incoming))]
    raise ValueError('Conflicting worker edits require review: ' + pointer)


def publication_blockers(notes, modules):
    """Unfinished atomic repairs must never disappear from a batch receipt."""
    blocked = []
    for note in notes:
        status = str(note.get('status', note.get('code', '')))
        dependencies = note.get('required_modules', [])
        if (note.get('publishable') is False or note.get('candidate_omitted')
                or note.get('severity') in ('blocker', 'error')
                or status in ('review_required', 'id_conflict_or_audit_error')
                or status.startswith('pending') or note.get('pending_review')
                or any(name not in modules for name in dependencies)):
            blocked.append(note)
    return blocked


def map_files():
    for dirname in ('ability', 'modifier', 'projectile', 'editor_table', 'editor/folderinfo',
                    'global_trigger', 'tables'):
        for current, dirs, files in os.walk(MAP / dirname):
            dirs[:] = [d for d in dirs if d != '.git']
            for name in files:
                if name.endswith(('.json', '.txt')):
                    yield Path(current) / name
    for name in ('attr.json', 'zhlanguage.json', 'tidindexinfo.json'):
        yield MAP / name


def stage(phase, modules):
    work = WORK / phase
    if (work / 'manifest.json').exists():
        raise ValueError('Candidate already exists; use a new phase label to preserve its baseline')
    baseline = {p.relative_to(MAP).as_posix(): sha(p.read_bytes()) for p in map_files()}
    payload, details = {}, []
    for module_name in modules:
        module = importlib.import_module(module_name)
        generated, notes = module.build(MAP)
        blockers = publication_blockers(notes, modules)
        if blockers:
            raise ValueError('Module contains publication blockers: ' + json.dumps(blockers, ensure_ascii=False))
        for relative, document in generated.items():
            if relative in payload:
                source = MAP / relative
                base = json.loads(source.read_text('utf8')) if source.exists() else None
                payload[relative] = merge_three_way(base, payload[relative], document, relative)
            else:
                payload[relative] = document
        details.extend(notes)
    if phase.startswith('p1'):
        module = importlib.import_module('y3_hero_repair_p1_shared')
        generated, notes = module.build(MAP, payload)
        payload.update(generated)
        details.extend(notes)
    elif phase.startswith('p2'):
        if 'y3_hero_repair_p2_lifecycle' in modules and 'ability/134262911.json' in payload:
            lifecycle = importlib.import_module('y3_hero_repair_p2_lifecycle')
            for oid in lifecycle.ACTIVES:
                relative = f'ability/{oid}.json'
                original = payload.get(relative)
                payload[relative] = lifecycle.patch_xiahou_active(
                    original if original is not None else json.loads((MAP / relative).read_text('utf8')), oid)
        module = importlib.import_module('y3_hero_repair_p2_shared')
        generated, notes = module.build(MAP, payload)
        payload.update(generated)
        details.extend(notes)
        descriptions = importlib.import_module('y3_hero_repair_p2_descriptions')
        generated, notes = descriptions.build(MAP, payload)
        payload.update(generated)
        details.extend(notes)
    blockers = publication_blockers(details, modules)
    if blockers:
        raise ValueError('Batch contains unfinished repairs: ' + json.dumps(blockers, ensure_ascii=False))
    entries = []
    for relative, fixed in sorted(payload.items()):
        target = (MAP / relative).resolve()
        assert MAP.resolve() in target.parents
        original = target.read_bytes() if target.exists() else None
        assert (sha(original) if original is not None else None) == baseline.get(relative), 'Map drifted while building: ' + relative
        old = json.loads(original) if original is not None else None
        pointers = compare(old, fixed)
        if not pointers:
            continue
        raw = encode(fixed)
        if original is not None:
            write_generated(work / 'original' / relative, original)
        write_generated(work / 'staged' / relative, raw)
        entries.append(dict(path=relative, before=sha(original) if original is not None else None,
                            after=sha(raw), pointers=pointers))
    manifest = dict(map=str(MAP), phase=phase, entries=entries, notes=details,
                    protected={k: v for k, v in baseline.items() if k not in {e['path'] for e in entries}})
    write_generated(work / 'manifest.json', encode(manifest))
    with zipfile.ZipFile(work / 'rollback.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for entry in entries:
            if entry['before'] is not None:
                archive.write(work / 'original' / entry['path'], entry['path'])
    print(json.dumps(dict(phase=phase, files=len(entries), notes=details), ensure_ascii=False, indent=2))


def publish(phase, apply=False):
    work = WORK / phase
    assert not (work / 'WITHDRAWN.json').exists(), 'Withdrawn candidate must not be republished: ' + phase
    manifest = json.loads((work / 'manifest.json').read_text('utf8'))
    assert Path(manifest['map']).resolve() == MAP.resolve()
    for entry in manifest['entries']:
        target = (MAP / entry['path']).resolve()
        assert MAP.resolve() in target.parents
        if entry['before'] is None:
            assert not target.exists(), 'New object already exists: ' + entry['path']
        else:
            assert sha(target.read_bytes()) == entry['before'], 'Live edit: ' + entry['path']
        raw = (work / 'staged' / entry['path']).read_bytes()
        assert sha(raw) == entry['after']
        json.loads(raw)
    for relative, digest in manifest['protected'].items():
        assert sha((MAP / relative).read_bytes()) == digest, 'Unrelated map edit: ' + relative
    if apply:
        for entry in manifest['entries']:
            target = MAP / entry['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + '.codex-pending')
            assert not temporary.exists()
            raw = (work / 'staged' / entry['path']).read_bytes()
            try:
                temporary.write_bytes(raw)
                os.replace(temporary, target)
            finally:
                if temporary.exists():
                    temporary.unlink()
            assert sha(target.read_bytes()) == entry['after']
    print(json.dumps(dict(phase=phase, mode='applied' if apply else 'preflight',
                          files=len(manifest['entries']), protected=len(manifest['protected']))))


def verify(phase):
    work = WORK / phase
    manifest = json.loads((work / 'manifest.json').read_text('utf8'))
    for entry in manifest['entries']:
        actual = json.loads((MAP / entry['path']).read_text('utf8'))
        expected = json.loads((work / 'staged' / entry['path']).read_text('utf8'))
        assert actual == expected, 'Editor changed candidate: ' + entry['path']
    print(json.dumps(dict(phase=phase, semantic_roundtrip=len(manifest['entries']))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['stage', 'publish', 'verify'])
    parser.add_argument('phase')
    parser.add_argument('--modules', nargs='*', default=[])
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if args.command == 'stage':
        stage(args.phase, args.modules)
    elif args.command == 'publish':
        publish(args.phase, args.apply)
    else:
        verify(args.phase)
