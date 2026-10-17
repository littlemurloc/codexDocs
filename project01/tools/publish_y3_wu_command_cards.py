"""Hash-checked, backed-up publication of the narrowly scoped Wu card patch."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import zipfile
import y3_wu_command_cards as b

SHARED={'zhlanguage.json','customevent.json','tables/技能作用描述表.json',
        'editor/folderinfo/folderinfo_modifier_all.json'}
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def publish(apply=False):
    root=b.MAP.resolve();stage=b.STAGE.resolve()
    if root!=Path(r'D:\littl\testTempFile\ProjectMonster02\maps\map3').resolve():raise ValueError('Unexpected map root')
    manifest=json.loads((b.WORK/'manifest.json').read_text('utf8'))
    specs=json.loads((b.WORK/'specs.json').read_text('utf8'))
    permitted=SHARED|{f'ability/{aid}.json' for aid in specs}|{f'editor_table/abilityall/{aid}.json' for aid in specs}
    permitted|={f'{folder}/{oid}.json' for folder in ['modifier','editor_table/modifierall'] for oid in [b.CONTROL,b.ARMY]}
    if set(manifest)!=permitted or len(manifest)!=70:raise ValueError('Publication scope differs from reviewed files')
    with zipfile.ZipFile(b.WORK/'before-wu-cards.zip') as z:
        for relative,record in manifest.items():
            dest=(root/relative).resolve()
            if root not in dest.parents:raise ValueError('Destination escapes map root')
            candidate=(stage/relative).resolve()
            if stage not in candidate.parents:raise ValueError('Source escapes stage')
            json.loads(candidate.read_text('utf8'))
            if digest(candidate)!=record['after']:raise ValueError('Staged file changed: '+relative)
            if digest(dest)!=record['before']:raise ValueError('Live file changed after staging: '+relative)
            if record['before'] is not None and hashlib.sha256(z.read(relative)).hexdigest()!=record['before']:
                raise ValueError('Backup mismatch: '+relative)
    print('Preflight passed:',len(manifest),'files;',sum(r['before'] is None for r in manifest.values()),'new files; existing files backed up.')
    if not apply:return
    completed=[]
    try:
        for relative,record in manifest.items():
            dest=(root/relative).resolve();dest.parent.mkdir(parents=True,exist_ok=True)
            pending=dest.with_name(dest.name+'.codex-wu-pending')
            if pending.exists():raise ValueError('Pending file exists: '+str(pending))
            try:
                pending.write_bytes((stage/relative).read_bytes());os.replace(pending,dest)
            finally:
                if pending.exists():pending.unlink()
            completed.append(relative)
            if digest(dest)!=record['after']:raise ValueError('Written hash mismatch: '+relative)
    except BaseException:
        with zipfile.ZipFile(b.WORK/'before-wu-cards.zip') as z:
            for relative in reversed(completed):
                dest=(root/relative).resolve()
                assert root in dest.parents
                if manifest[relative]['before'] is None:dest.unlink()
                else:dest.write_bytes(z.read(relative))
        raise
    record={'map':str(root),'files':list(manifest),'count':len(manifest),'engine_validated':False,
            'backup':str(b.WORK/'before-wu-cards.zip'),'formal_pool_changed':False}
    (b.WORK/'published.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
    print('Published and hash-verified:',len(completed),'files. Editor/gameplay validation remains pending.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');publish(parser.parse_args().apply)
