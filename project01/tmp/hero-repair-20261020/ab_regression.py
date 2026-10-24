"""Temporary, single-variant regression switch. Not a production repair."""
import argparse
import copy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import y3_hero_repair_publish as pub
import y3_hero_repair_editor_audit as audit

ROOT = Path(__file__).resolve().parent / 'ab-20261022'
FILES = {'mach': 'modifier/134265433.json',
         'taishi': 'modifier/134277456.json',
         'ssx': 'ability/134219344.json'}


def load(path):
    return json.loads(path.read_text('utf8'))


def save(path, data):
    pub.write_generated(path, pub.encode(data))


def checked_diffs(expected, actual):
    result = []
    for p, a, b in audit.differences(expected, actual):
        if p.endswith('/fake_op') and (a is audit.MISSING or a == []) and b == [2]:
            continue
        if (p.endswith('/local_var') and a is audit.MISSING
                and b == {'__tuple__': True, 'items': [{}, {}]}):
            continue
        result.append((p, repr(a)[:100], repr(b)[:100]))
    return result


def walk(x):
    if isinstance(x, dict):
        if x.get('enable') is False:
            return
        yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)


def ssx_variant(doc):
    result = copy.deepcopy(doc)
    removed = {'same': 0, 'role': 0}
    for tid in ('1959489540', '893440004'):
        for node in walk(result['trigger_dict'][tid]['action']):
            if node.get('action_type') != 'IF_THEN_ELSE':
                continue
            conditions = node['args_list'][0]['args_list']
            keep = []
            for condition in conditions:
                raw = json.dumps(condition, ensure_ascii=False)
                same = (condition.get('condition_type') == 'BOOL_COMPARE'
                        and 'P2_state_sword_different' in raw)
                role = (condition.get('condition_type') == 'OR'
                        and 'P2_state_sword_target1' in raw
                        and '\u9635\u578b\u961f\u957f' in raw
                        and '\u4ec6\u4ece\u4f19\u4f34' in raw)
                if same:
                    removed['same'] += 1
                elif role:
                    removed['role'] += 1
                else:
                    keep.append(condition)
            conditions[:] = keep
    assert removed == {'same': 2, 'role': 2}, removed
    # Keep native IF nodes, but replace the two empty role gates with their body.
    def flatten(value):
        if isinstance(value, list):
            out = []
            for child in value:
                flatten(child)
                if (isinstance(child, dict)
                        and child.get('action_type') == 'IF_THEN_ELSE'
                        and child.get('enable') is not False
                        and not child['args_list'][0]['args_list']):
                    assert not child['args_list'][2]['args_list']
                    out.extend(child['args_list'][1]['args_list'])
                else:
                    out.append(child)
            value[:] = out
        elif isinstance(value, dict) and value.get('enable') is not False:
            for child in value.values():
                flatten(child)
    flatten(result)
    return result


def stage():
    assert not ROOT.exists(), 'Do not overwrite an existing baseline'
    # Check the two loops still match the last published repair receipts.
    for name, phase in [('mach', 'p2'), ('taishi', 'taishi-context')]:
        rel = FILES[name]
        assert not checked_diffs(load(pub.WORK / phase / 'staged' / rel),
                                 load(pub.MAP / rel)), (name, 'unreviewed live edits')
    baseline = {p.relative_to(pub.MAP).as_posix(): pub.sha(p.read_bytes())
                for p in pub.map_files()}
    for rel in FILES.values():
        pub.write_generated(ROOT / 'baseline' / rel, (pub.MAP / rel).read_bytes())
    variants = {
        'mach': load(pub.WORK / 'p2/original' / FILES['mach']),
        'taishi': load(pub.WORK / 'p1/original' / FILES['taishi']),
        'ssx': ssx_variant(load(pub.MAP / FILES['ssx'])),
    }
    entries = {}
    for name, doc in variants.items():
        rel = FILES[name]
        assert all(t.get('valid') is True for t in doc['trigger_dict'].values())
        target = ROOT / name / rel
        save(target, doc)
        entries[name] = {'path': rel, 'sha256': pub.sha(target.read_bytes()),
                         'triggers': len(doc['trigger_dict'])}
    save(ROOT / 'manifest.json', {'map': str(pub.MAP), 'baseline': baseline,
                                  'variants': entries,
                                  'purpose': 'Diagnostic A/B only; no gameplay acceptance.'})
    print(json.dumps(entries, ensure_ascii=False))


def check(name, applied=False):
    manifest = load(ROOT / 'manifest.json')
    assert Path(manifest['map']).resolve() == pub.MAP.resolve()
    entry = manifest['variants'][name]
    target = entry['path']
    changed = [rel for rel, h in manifest['baseline'].items()
               if rel != target and pub.sha((pub.MAP / rel).read_bytes()) != h]
    assert not changed, ('Other map files changed; stop', changed)
    if applied:
        expected = load(ROOT / name / target)
        actual = load(pub.MAP / target)
        assert not checked_diffs(expected, actual), checked_diffs(expected, actual)
        assert all(t.get('valid') is True for t in actual['trigger_dict'].values())
    else:
        assert pub.sha((pub.MAP / target).read_bytes()) == manifest['baseline'][target]
    print(json.dumps({'variant': name, 'only_changed_file': target,
                      'protected_unchanged': len(manifest['baseline']) - 1,
                      'applied': applied, 'boundary': 'Not gameplay tested.'}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['stage', 'preflight', 'apply', 'verify'])
    parser.add_argument('variant', nargs='?', choices=FILES)
    args = parser.parse_args()
    if args.mode == 'stage':
        stage()
        return
    assert args.variant
    check(args.variant, args.mode == 'verify')
    if args.mode == 'apply':
        rel = FILES[args.variant]
        source = ROOT / args.variant / rel
        assert pub.sha(source.read_bytes()) == load(ROOT / 'manifest.json')['variants'][args.variant]['sha256']
        (pub.MAP / rel).write_bytes(source.read_bytes())
        check(args.variant, True)


if __name__ == '__main__':
    main()
