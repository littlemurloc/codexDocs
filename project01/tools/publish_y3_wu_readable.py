"""Publish only the reviewed native-ECA readability refactor, with rollback."""
from pathlib import Path
import argparse,hashlib,json,os,zipfile
import refactor_y3_wu_cards as r

def sha(raw):return hashlib.sha256(raw).hexdigest()
def publish(apply=False):
    root=r.b.MAP.resolve();stage=r.STAGE.resolve()
    assert root==Path(r'D:\littl\testTempFile\ProjectMonster02\maps\map3').resolve()
    manifest=json.loads((r.WORK/'manifest.json').read_text('utf8'))
    allowed={f'ability/{aid}.json' for aid in r.b.load_specs()}
    allowed|={f'modifier/{oid}.json' for oid in (r.b.CONTROL,r.b.ARMY)}
    allowed|={f'{r.FOLDER}/{name}.json' for name in r.NAMES.values()}
    allowed|={r.FOLDER+'/index.txt','global_trigger/function/new/index.txt',
              'tables/吴国军略_卡牌登记表.json','tables/吴国军略_收益参数映射表.json'}
    if 'editor/tableeditorgroupinfo.json' in manifest:allowed.add('editor/tableeditorgroupinfo.json')
    assert set(manifest)==allowed and len(manifest) in (48,49)
    with zipfile.ZipFile(r.WORK/'before-readable.zip') as backup:
        for rel,record in manifest.items():
            dest=(root/rel).resolve();candidate=(stage/rel).resolve()
            assert root in dest.parents and stage in candidate.parents
            raw=candidate.read_bytes();json.loads(raw)
            assert sha(raw)==record['after'], 'Candidate changed: '+rel
            assert (sha(dest.read_bytes()) if dest.exists() else None)==record['before'], 'Live changed: '+rel
            if record['before'] is not None:assert sha(backup.read(rel))==record['before']
    print('Preflight passed:',len(manifest),'files; existing files backed up; formal pool and object values excluded.')
    if not apply:return
    completed=[]
    try:
        for rel,record in manifest.items():
            dest=(root/rel).resolve();dest.parent.mkdir(parents=True,exist_ok=True)
            pending=dest.with_name(dest.name+'.codex-readable-pending');assert not pending.exists()
            try:
                pending.write_bytes((stage/rel).read_bytes());os.replace(pending,dest)
            finally:
                if pending.exists():pending.unlink()
            completed.append(rel)
            assert sha(dest.read_bytes())==record['after']
    except BaseException:
        with zipfile.ZipFile(r.WORK/'before-readable.zip') as backup:
            for rel in reversed(completed):
                dest=(root/rel).resolve();assert root in dest.parents
                if manifest[rel]['before'] is None:dest.unlink()
                else:dest.write_bytes(backup.read(rel))
        raise
    (r.WORK/'published.json').write_text(json.dumps({'map':str(root),'files':manifest,
            'editor_verified':False,'game_verified':False},ensure_ascii=False,indent=2),encoding='utf8')
    print('Published and hash-verified',len(manifest),'files.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');publish(p.parse_args().apply)
