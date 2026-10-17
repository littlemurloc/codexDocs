"""Stage/test or publish the one-file Wu card category correction."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import unittest
import y3_wu_command_cards as b
import test_y3_wu_command_cards as tests

WORK=Path(__file__).resolve().parents[1]/'tmp/wu-fix-20261017'
REL='modifier/134285001.json'
RESULTS={134275559,134228375,134273390,134269447,134245355}
def sha(data):return hashlib.sha256(data).hexdigest()

def stage():
    WORK.mkdir(parents=True,exist_ok=True)
    original=(b.MAP/REL).read_bytes()
    doc=json.loads(original)
    # Capture the current saved file, including any editor normalization.
    if (WORK/'before.json').exists():
        assert (WORK/'before.json').read_bytes()==original, 'Live controller changed; review it'
    else:(WORK/'before.json').write_bytes(original)
    counts={}
    for node in b.walk(doc):
        if node.get('sub_type')!='GET_ABILITY_BY_AID':continue
        args=node['args_list'];aid=args[2]['args_list'][0]
        assert aid in b.load_specs()
        assert args[1]['args_list'][0]==2, 'Unexpected live lookup category'
        if aid in RESULTS:
            args[1]['args_list'][0]=3
            counts[aid]=counts.get(aid,0)+1
    assert counts=={134228375:4,134245355:40,134269447:4,134273390:8,134275559:4}, counts
    candidate=(json.dumps(doc,ensure_ascii=True,indent=4)+'\n').encode()
    (WORK/'controller-fixed.json').write_bytes(candidate)
    record={'relative':REL,'before':sha(original),'after':sha(candidate),
            'lookups_changed':sum(counts.values()),'by_ability':counts}
    (WORK/'manifest.json').write_text(json.dumps(record,indent=2),encoding='utf8')
    original_read=tests.read
    tests.read=lambda rel:json.loads(candidate) if rel==REL else original_read(rel)
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(tests.WuTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful()
    # Check builder consistency without re-staging/replacing the original batch.
    for node in b.walk(b.controller_eca(b.load_specs())):
        if node.get('sub_type')=='GET_ABILITY_BY_AID':
            args=node['args_list'];aid=args[2]['args_list'][0]
            assert args[1]['args_list'][0]==(3 if aid in RESULTS else 2)
    print(json.dumps(record,ensure_ascii=False,indent=2))

def publish():
    record=json.loads((WORK/'manifest.json').read_text())
    root=b.MAP.resolve();dest=(root/REL).resolve()
    assert root==Path(r'D:\littl\testTempFile\ProjectMonster02\maps\map3').resolve()
    assert root in dest.parents
    assert sha(dest.read_bytes())==record['before'], 'Live file changed after backup'
    payload=(WORK/'controller-fixed.json').read_bytes()
    assert sha(payload)==record['after']
    assert sha((WORK/'before.json').read_bytes())==record['before']
    pending=dest.with_name(dest.name+'.codex-category-pending')
    assert not pending.exists()
    try:
        pending.write_bytes(payload);os.replace(pending,dest)
    finally:
        if pending.exists():pending.unlink()
    assert sha(dest.read_bytes())==record['after']
    (WORK/'published.json').write_text(json.dumps(record,indent=2),encoding='utf8')
    print('Published one controller file; 60 category lookups corrected.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['stage','publish'])
    args=p.parse_args();stage() if args.command=='stage' else publish()
