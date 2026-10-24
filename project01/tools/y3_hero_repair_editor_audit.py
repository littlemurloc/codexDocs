"""Check the settled editor output against an ordered stack of repair receipts."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import y3_hero_repair_publish as publish

MISSING = object()


def differences(a, b, path=''):
    if a == b:
        return []
    if isinstance(a, dict) and isinstance(b, dict):
        return [d for k in a.keys() | b.keys()
                for d in differences(a.get(k, MISSING), b.get(k, MISSING), path + '/' + str(k))]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in differences(x, y, path + '/' + str(i))]
    return [(path, a, b)]


def audit(phases):
    expected, protected = {}, {}
    for phase in phases:
        work = publish.WORK / phase
        manifest = json.loads((work / 'manifest.json').read_text('utf8'))
        assert Path(manifest['map']).resolve() == publish.MAP.resolve()
        for relative, digest in manifest['protected'].items():
            protected.setdefault(relative, digest)
        for entry in manifest['entries']:
            expected[entry['path']] = json.loads((work / 'staged' / entry['path']).read_text('utf8'))
    metadata, hashes, invalid, unexpected = [], {}, [], []
    count = 0
    for relative, before in expected.items():
        raw = (publish.MAP / relative).read_bytes()
        hashes[relative] = publish.sha(raw)
        actual = json.loads(raw)
        for pointer, a, b in differences(before, actual):
            if ((pointer.endswith('/fake_op') and (a is MISSING or a == []) and b == [2])
                    or (pointer.endswith('/local_var') and a is MISSING
                        and b == {'__tuple__': True, 'items': [{}, {}]})):
                metadata.append(dict(file=relative, pointer=pointer, editor_value=b))
            else:
                unexpected.append((relative, pointer, repr(a)[:100], repr(b)[:100]))
        for key, trigger in actual.get('trigger_dict', {}).items():
            count += 1
            if trigger.get('valid') is not True:
                invalid.append((relative, key))
    untouched = {f: h for f, h in protected.items() if f not in expected}
    changed = [f for f, h in untouched.items() if publish.sha((publish.MAP / f).read_bytes()) != h]
    assert not unexpected, unexpected
    assert not invalid, invalid
    assert not changed, changed
    return dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), phases=phases,
                files=len(expected), triggers_valid=count, protected=len(untouched),
                file_sha256=hashes, editor_metadata_additions=metadata,
                boundary='Static editor output only. fake_op additions are recorded, not discarded; no gameplay claim.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phases', nargs='+')
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--stable-against', type=Path)
    args = parser.parse_args()
    receipt = audit(args.phases)
    if args.stable_against:
        old = json.loads(args.stable_against.read_text('utf8'))
        assert old['file_sha256'] == receipt['file_sha256'], 'Editor output has not settled'
    if args.receipt:
        target = args.receipt.resolve()
        assert publish.WORK.resolve() in target.parents
        assert not target.exists(), 'Never overwrite a previous audit receipt'
        target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: v for k, v in receipt.items()
                      if k not in ('file_sha256', 'editor_metadata_additions')}, ensure_ascii=False))
    print('Editor metadata additions:', len(receipt['editor_metadata_additions']))
